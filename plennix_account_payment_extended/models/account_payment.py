from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_internal_transfer = fields.Boolean(string="Internal Transfer",
                                          readonly=False, store=True,
                                          tracking=True,
                                          compute="_compute_is_internal_transfer")
    destination_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        domain="[('type', 'in', ('bank','cash')), ('id', '!=', journal_id)]",
        check_company=True,
    )

    @api.depends('payment_type', 'journal_id', 'currency_id','is_internal_transfer')
    def _compute_payment_method_line_fields(self):
        super()._compute_payment_method_line_fields()
        for pay in self:
            to_exclude = pay._get_payment_method_codes_to_exclude()
            if pay.is_internal_transfer:
                pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type).filtered(
                    lambda x: x.code in ['manual'])

    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            payment.is_internal_transfer = payment.partner_id \
                                           and payment.partner_id == payment.journal_id.company_id.partner_id \
                                           and payment.destination_journal_id

    def action_open_destination_journal(self):
        ''' Redirect the user to this destination journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Destination journal"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal',
            'context': {'create': False},
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.destination_journal_id.id,
        }
        return action

    def _get_aml_default_display_name_list(self):
        self.ensure_one()
        values = super()._get_aml_default_display_name_list()

        if self.is_internal_transfer:
            # Replace the label entry in the returned list
            for item in values:
                if item[0] == 'label':
                    item = ('label', _("Internal Transfer"))
                    break
            else:
                # If no 'label' was found, add one
                values.insert(0, ('label', _("Internal Transfer")))

            # Alternatively: force first item to be Internal Transfer label
            values[0] = ('label', _("Internal Transfer"))

        return values

    def _get_liquidity_aml_display_name_list(self):
        """ Hook allowing custom values when constructing the label to set on the liquidity line.

        :return: A list of terms to concatenate all together. E.g.
            [('reference', "INV/2018/0001")]
        """
        self.ensure_one()
        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                return [('transfer_to', _('Transfer to %s', self.journal_id.name))]
            else: # payment.payment_type == 'outbound':
                return [('transfer_from', _('Transfer from %s', self.journal_id.name))]
        elif self.payment_reference:
            return [('reference', self.payment_reference)]
        else:
            return self._get_aml_default_display_name_list()

    def _get_counterpart_aml_display_name_list(self):
        """ Hook allowing custom values when constructing the label to set on the counterpart line.

        :return: A list of terms to concatenate all together. E.g.
            [('reference', "INV/2018/0001")]
        """
        self.ensure_one()
        if self.payment_reference:
            return [('reference', self.payment_reference)]
        else:
            return self._get_aml_default_display_name_list()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :param force_balance: Optional balance.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or []

        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %(payment_method)s payment method in the %(journal)s journal.",
                payment_method=self.payment_method_line_id.name, journal=self.journal_id.display_name))

        # Compute amounts.
        write_off_line_vals_list = write_off_line_vals or []
        write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
        write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0

        if not write_off_line_vals and force_balance is not None:
            sign = 1 if liquidity_amount_currency > 0 else -1
            liquidity_balance = sign * abs(force_balance)
        else:
            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        # # Compute a default label to set on the journal items.
        # liquidity_line_name = ''.join(x[1] for x in self._get_aml_default_display_name_list() if x[1])
        # counterpart_line_name = liquidity_line_name

        liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
        counterpart_line_name = ''.join(x[1] for x in self._get_counterpart_aml_display_name_list())

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': counterpart_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        return line_vals_list + write_off_line_vals_list

    @api.depends('partner_id', 'company_id', 'payment_type', 'destination_journal_id', 'is_internal_transfer')
    def _compute_available_partner_bank_ids(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.available_partner_bank_ids = pay.journal_id.bank_account_id
            elif pay.is_internal_transfer:
                pay.available_partner_bank_ids = pay.destination_journal_id.bank_account_id
            else:
                pay.available_partner_bank_ids = pay.partner_id.bank_ids \
                    .filtered(lambda x: x.company_id.id in (False, pay.company_id.id))._origin

    # @api.depends('is_internal_transfer', 'journal_id')
    # def _compute_partner_id(self):
    #     super()._compute_partner_id()
    #
    #     for pay in self:
    #         if pay.is_internal_transfer:
    #             pay.partner_id = pay.journal_id.company_id.partner_id

    @api.depends('is_internal_transfer')
    def _compute_partner_id(self):
        for pay in self:
            if pay.is_internal_transfer:
                pay.partner_id = pay.journal_id.company_id.partner_id
            elif pay.partner_id == pay.journal_id.company_id.partner_id:
                pay.partner_id = False
            else:
                pay.partner_id = pay.partner_id

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer', 'destination_journal_id')
    def _compute_destination_account_id(self):
        super()._compute_destination_account_id()

        for pay in self:
            if pay.is_internal_transfer and pay.destination_journal_id.company_id.transfer_account_id:
                pay.destination_account_id = pay.destination_journal_id.company_id.transfer_account_id

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        # Get default fields from the parent
        fields = super()._get_trigger_fields_to_synchronize()

        # Add custom fields (e.g., 'is_internal_transfer') if not already present
        custom_fields = ('is_internal_transfer',)
        return tuple(set(fields + custom_fields))

    def action_post(self):
        for payment in self:
            if (
                payment.require_partner_bank_account
                and not payment.partner_bank_id.allow_out_payment
            ):
                raise UserError(_(
                    "To record payments with %s, the recipient bank account must be manually validated. "
                    "You should go on the partner bank account of %s in order to validate it."
                ) % (payment.payment_method_line_id.name, payment.partner_id.display_name))

        # Call the super method to maintain standard behavior
        res = super().action_post()

        # Any custom logic after posting (if needed)
        self.filtered(
            lambda pay: pay.is_internal_transfer and not pay.paired_internal_transfer_payment_id
        )._create_paired_internal_transfer_payment()

        return res

    def _create_paired_internal_transfer_payment(self):
        ''' When an internal transfer is posted, a paired payment is created
        with opposite payment_type and swapped journal_id & destination_journal_id.
        Both payments liquidity transfer lines are then reconciled.
        '''
        for payment in self:
            paired_payment = payment.with_context(internal_transfer=True).copy({
                'journal_id': payment.destination_journal_id.id,
                'destination_journal_id': payment.journal_id.id,
                'payment_type': payment.payment_type == 'outbound' and 'inbound' or 'outbound',
                'move_id': None,
                'payment_reference': payment.payment_reference,
                'paired_internal_transfer_payment_id': payment.id,
                'date': payment.date,
            })
            paired_payment._compute_payment_method_line_fields()
            paired_payment.move_id._post(soft=False)
            # paired_payment.action_post()
            payment.paired_internal_transfer_payment_id = paired_payment
            body = _("This payment has been created from:") + payment._get_html_link()
            paired_payment.message_post(body=body)
            body = _("A second payment has been created:") + paired_payment._get_html_link()
            payment.message_post(body=body)

            lines = (payment.move_id.line_ids + paired_payment.move_id.line_ids).filtered(
                lambda l: l.account_id == payment.destination_account_id and not l.reconciled)
            lines.reconcile()

    @api.depends('available_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        ''' Compute the 'payment_method_line_id' field.
        This field is not computed in '_compute_payment_method_line_fields' because it's a stored editable one.
        '''
        for pay in self:
            available_payment_method_lines = pay.available_payment_method_line_ids

            # Select the first available one by default.
            if pay.payment_method_line_id in available_payment_method_lines:
                pay.payment_method_line_id = pay.payment_method_line_id
            elif available_payment_method_lines:
                pay.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                pay.payment_method_line_id = False

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)

        if 'internal_transfer' in self.env.context and self.env.context.get('internal_transfer'):
            for payment, vals in zip(self, vals_list):
                vals.update({
                    'journal_id': payment.destination_journal_id.id,
                })
                # Explicitly remove payment_method_line_id if present
                vals.pop('payment_method_line_id', None)

        return vals_list