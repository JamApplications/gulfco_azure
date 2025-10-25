from odoo import _, fields, models, api
from odoo.exceptions import ValidationError


class AccountPaymentCdcCollectionFees(models.TransientModel):
    _name = 'account.payment.cdc.collection.fees'
    _description = 'Account Payment CDC Collection Fees Wizard'

    amount = fields.Float()
    date = fields.Date(
        string='Transaction Date',
        default=fields.Date.context_today,
    )
    ref = fields.Char(
        string='Reference',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Payment Method',
        required=True,
        domain="[('type', '=', 'bank'), ('is_cdc','=', False)]",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='journal_id.company_id',
    )
    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_payment_method_line_fields')
    hide_payment_method_line = fields.Boolean(
        compute='_compute_payment_method_line_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which "
             "is 'manual'")

    payment_method_line_id = fields.Many2one(
        'account.payment.method.line', string='Payment Method',
        readonly=False, store=True,
        compute='_compute_payment_method_line_id',
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Collection Fees Account',
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable')), ('company_ids', 'in', company_id)]",
        check_company=True
    )

    @api.depends('journal_id')
    def _compute_payment_method_line_id(self):
        for wizard in self:
            available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines('outbound')

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    @api.depends('journal_id')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines('outbound')
            if wizard.payment_method_line_id.id not in wizard.available_payment_method_line_ids.ids:
                # In some cases, we could be linked to a payment method line that has been unlinked from the journal.
                # In such cases, we want to show it on the payment.
                wizard.hide_payment_method_line = False
            else:
                wizard.hide_payment_method_line = len(wizard.available_payment_method_line_ids) == 1 \
                                                  and wizard.available_payment_method_line_ids.code == 'manual'

    def action_register_collection_fees(self):
        """ register fees for bank """
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model')
        if active_model != 'account.payment':
            raise ValidationError(_('Please open Cheque'))

        payment = self.env[active_model].browse(active_id)
        if payment.is_cdc_payment:
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            payment_method = \
                payment.deposit_cdc_id.bank_journal_id.outbound_payment_method_line_ids.filtered(
                    lambda line: line.payment_method_id == payment_method)
            if payment_method and payment.journal_id.write_off_cdc_account_id:
                vals = {
                    'amount': abs(self.amount),
                    'payment_type': 'outbound',
                    'currency_id': payment.currency_id.id,
                    'partner_id': payment.partner_id.id,
                    'partner_type': 'customer',
                    'journal_id': self.journal_id.id,
                    'company_id': self.journal_id.company_id.id,
                    'payment_method_line_id': payment_method[0].id,
                    'memo': self.ref if self.ref else 'Collection Fees ' + payment.name if payment.name else '' + ' - ' + payment.memo,
                    'destination_account_id': self.destination_account_id.id,
                    'cheque_payment_id': payment.id,
                    'date': self.date,
                    'cheque_payment_type': 'collection_fees',
                }
                if hasattr(payment, 'liquidity_analytic_tag_ids'):
                    vals.update({
                        'liquidity_analytic_tag_ids': [(6, 0, payment.liquidity_analytic_tag_ids.ids)],
                    })
                payment = self.env['account.payment'].with_context(custom_bypass=True).create(vals)
                payment.move_id.cheque_payment_type = 'collection_fees'
                payment.action_post()
                payment.collection_fees_payment_id = payment.id
