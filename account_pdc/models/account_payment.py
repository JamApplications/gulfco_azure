from odoo import _, fields, models, api, Command
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    # _inherits = {'account.move': 'move_id'}

    # common fields for pdc receivable / payable
    bounced_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Bounced Journal Entry',
        tracking=True,
        copy=False,
    )
    customer_code = fields.Char(related="partner_id.customer_code",store=True)

    cheque_payment_type = fields.Selection(
        selection=[('bounced', 'Bounced'),
                   ('deposit', 'Deposit'),
                   ('collected', 'Collected'),
                   ('delivered', 'Delivered'),
                   ('cleared', 'Cleared'),
                   ('writeoff', 'Write-off'),
                   ('recheque', 'Recheque'),
                   ('bounced_in', 'Bounced In Bank'),
                   ('bounced_out', 'Bounced Out Bank'),
                   ('cashed', 'Cashed'),
                   ('recycled', 'Recycled'),
                   ('collection_fees', 'Collection Fees'),
                   ],
    )

    is_access_draft = fields.Boolean(compute='get_draft_access')
    pdc_ref = fields.Char('Cheque Number')
    payment_amount = fields.Float()
    advance_amount = fields.Float()
    bounced_cleared_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Bounced Journal Entry',
        tracking=True,
        copy=False,
    )

    is_pdc_receivable_entry = fields.Boolean(related='move_id.is_pdc_receivable_entry', store=True)

    # pdc receivable fields
    is_pdc_payment = fields.Boolean(
        compute='_compute_is_pdc_payment',
        store=True,
    )
    deposit_pdc_id = fields.Many2one(
        comodel_name='account.deposit.pdc',
        string='Deposit',
        copy=False,
        tracking=True,
    )
    deposit_pdc_state = fields.Selection(
        related='deposit_pdc_id.state',
    )

    # added new field from the account move relation to avoid xml error
    is_move_sent = fields.Boolean(
        related='move_id.is_move_sent',
    )

    deposit_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Deposit Journal Entry',
        tracking=True,
        copy=False,
    )
    pdc_state = fields.Selection(
        string='Cheque Status',
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('registered', 'Registered'),
            ('bounced', 'Bounced'),
            ('returned', 'Returned'),
            ('cashed', 'Cashed'),
            ('recycled', 'Recycled'),
            ('re_cheque', 'Re Cheque'),
            ('deposit', 'Remitted'),
            ('collected', 'Cleared'),
            ('writeoff', 'Write Off'),
        ],
        default='registered',
        copy=False,
        tracking=True,
    )
    collect_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )
    cheque_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )
    write_off_payment_id = fields.Many2one(
        comodel_name='account.move',
        copy=False,
    )
    collection_fees_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )
    cheque_move_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='cheque_payment_id',
    )
    cash_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )
    recheque_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )
    recycled_payment_id = fields.Many2one(
        comodel_name='account.payment',
        copy=False,
    )
    pdc_bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Bank Name',
    )
    due_date = fields.Date(
        copy=False,
    )
    cheque_owner_id = fields.Many2one(
        comodel_name='res.users',
        default=lambda self: self.env.user,
        copy=False,
        tracking=True,
    )

    beneficiary_id = fields.Many2one(comodel_name="res.company", string='Beneficiary Name', required=False,
                                     default=lambda self: self.env.company,
                                     )
    beneficiary_name = fields.Char(string="Beneficiary Name",default="Gulf Trading and Refrigerating Co LLC")

    cheque_scanning = fields.Binary(
        copy=False,
        attachment=True,
    )
    related_move_ids = fields.Many2many(
        comodel_name='account.move',
        copy=False,
    )
    pdc_receivable_deposit_count = fields.Integer(
        compute='_compute_pdc_receivable_deposit',
    )
    pdc_receivable_bounced_move_count = fields.Integer(
        compute='_compute_pdc_receivable_bounced_move',
    )
    pdc_receivable_bounced_in_out_count = fields.Integer(
        compute='_compute_pdc_receivable_bounced_in_out',
    )
    pdc_receivable_collected_count = fields.Integer(
        compute='_compute_pdc_receivable_collected',
    )
    pdc_receivable_writeoff_count = fields.Integer(
        compute='_compute_pdc_receivable_writeoff',
    )
    pdc_receivable_collection_fees_count = fields.Integer(
        compute='_compute_pdc_receivable_collection_fees',
    )
    pdc_receivable_recheque_count = fields.Integer(
        compute='_compute_pdc_receivable_recheque',
    )
    pdc_receivable_recycled_count = fields.Integer(
        compute='_compute_pdc_receivable_recycled',
    )
    pdc_receivable_cashed_count = fields.Integer(
        compute='_compute_pdc_receivable_cashed',
    )

    # pdc payable fields
    can_be_pdc_payable = fields.Boolean(
        compute='_compute_can_be_pdc_payable',
    )
    is_pdc_payable = fields.Boolean(
        string='Is PDC Payable',
    )
    pdc_payable_note = fields.Char(
        string='PDC Payable Note',
    )
    pdc_payable_state = fields.Selection(
        string='PDC Payable Status',
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('registered', 'Registered'),
            ('delivered', 'Delivered'),
            ('bounced', 'Bounced'),
            ('cleared', 'Cleared'),
        ],
        default='draft',
        copy=False,
        tracking=True,
        readonly=False,
        compute='_compute_pdc_payable_state',
        store=True,
    )
    cleared_pdc_payable_move_id = fields.Many2one(
        comodel_name='account.move',
        copy=False,
    )
    pdc_payable_cleared_move_count = fields.Integer(
        compute='_compute_pdc_payable_cleared_move',
    )

    delivered_pdc_payable_move_id = fields.Many2one(
        comodel_name='account.move',
        copy=False,
    )
    pdc_payable_delivered_move_count = fields.Integer(
        compute='_compute_pdc_payable_delivered_move',
    )
    exchange_office_id = fields.Many2one('res.partner', string="Exchange Office")
    journal_type = fields.Selection(related='journal_id.type')
    cancel_id = fields.Many2one('cheque.cancel.reason', string="Bounce Reason")
    is_pdc_collected = fields.Boolean(string="Is PDC Collected",copy=False)

    # common functions pdc receivable and payable
    def _create_pdc_journal_entry(self, journal, partner, label, amount, debit_account, credit_account,
                                  amount_currency=False,
                                  currency=False, ref='',
                                  date=fields.Date.today(),
                                  debit_analytic_tag_ids=False,
                                  credit_analytic_tag_ids=False,
                                  cheque_payment_type=False):
        """ generic function to create journal entry """
        self.ensure_one()
        check_line = self.env['account.move.line'].search([('move_id','in',self.env['account.move'].search([('cheque_payment_id','=', self.id)]).ids),
                                              ('account_id','=', partner.property_account_receivable_id.id)])
        if len(check_line) > 0 and cheque_payment_type == 'collected':
            return True
        move = self.env['account.move'].create({
            'date': self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
            'journal_id': journal.id,
            'cheque_payment_id': self.id,
            'ref': ref,
            'partner_id': partner.id,
            'cheque_payment_type': cheque_payment_type,
            'line_ids': [
                (0, 0, {
                    'name': label,
                    'date':self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
                    'date_maturity':self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
                    'invoice_date':self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
                    'partner_id': partner.id,
                    'account_id': debit_account.id,
                    'debit': amount,
                    'currency_id': currency.id if currency else False,
                    'amount_currency': amount_currency if amount_currency else 0,
                    # 'analytic_tag_ids': [(6, 0, debit_analytic_tag_ids)] if debit_analytic_tag_ids else False,
                }),
                (0, 0, {
                    'name': label,
                    'date':self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
                    'date_maturity':self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
                    'invoice_date':self.due_date if cheque_payment_type=='collected' else fields.Date.today(),
                    'partner_id': partner.id,
                    'account_id': credit_account.id,
                    'credit': amount,
                    'currency_id': currency.id if currency else False,
                    'amount_currency': -amount_currency if amount_currency else 0,
                    # 'analytic_tag_ids': [(6, 0, credit_analytic_tag_ids)] if credit_analytic_tag_ids else False,
                }),
            ],
        })
        move.action_post()
        return move

    # def set_ref_field(self):
    #     for rec in self:
    #         ref = ''
    #         if rec.pdc_ref:
    #             ref = str(rec.pdc_ref)
    #         rec.ref = ref
    #         rec.move_id.ref = ref
    #
    @api.depends('ref')
    def get_ref_field(self):
        for rec in self:
            pdc_ref = ''
            if not rec.journal_id.is_pdc and rec.is_pdc_payment:
                pdc_ref = False
            elif rec.memo:
                if rec.memo.isnumeric():
                    pdc_ref = rec.memo
                else:
                    ref_lst = rec.memo.split(' ')
                    if ref_lst[-1].isnumeric():
                        pdc_ref = ref_lst[-1]
            rec.pdc_ref = pdc_ref


    def get_draft_access(self):
        for this in self:
            if self.env.user.has_group('account.group_account_user') or self.env.user.has_group(
                    'account.group_account_invoice'):
                this.is_access_draft = False

            else:
                this.is_access_draft = True

    def action_cancel_pdc(self):
        """ reset cheque to draft then cancel it """
        self.action_draft()
        self.action_cancel()

    def action_return_pdc(self):
        """ return cheque to customer """
        for record in self:
            company_currency = record.journal_id.company_id.currency_id
            amount_currency = abs(record._get_payment_amount())
            currency = company_currency
            if record.currency_id != company_currency:
                amount_currency = record._get_payment_amount(company_currency=False)
                currency = record.currency_id
            liquidity_analytic_tag_ids = False
            if hasattr(record, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
            move = record._create_pdc_journal_entry(
                journal=record.journal_id,
                partner=record.partner_id,
                label='Cheque Returned %s - %s' % (record.memo, record.name),
                amount=record._get_payment_amount(),
                debit_account=record.journal_id.pdc_bounce_beneficiaries_account_id,
                credit_account=record.journal_id.pdc_bounce_receivable_account_id,
                amount_currency=amount_currency,
                currency=currency,
                ref=f"Return to Customer Entry - {record.name}",
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='returned',
                date=fields.date.today(),
            )
        self.write({'pdc_state': 'returned'})

    def action_open_related_pdc(self):
        """
        open pdc receivable cashed payments
        """
        self.ensure_one()
        cheque_payment = self.cheque_payment_id
        action = {
            'name': _("PDC"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False, 'edit': False},
            'res_id': cheque_payment.id,
            'view_mode': 'form',
        }
        return action

    # pdc receivable functions
    @api.depends('journal_id', 'journal_id.is_pdc', 'payment_type')
    def _compute_is_pdc_payment(self):
        """ mark payment is pdc or not """
        for record in self:
            record.is_pdc_payment = bool(record.payment_type in ['inbound'] and record.journal_id.is_pdc)

    def action_pdc_receivable_bounced(self, bounce_date=fields.Date.today(),
                                      partner=False, original_payment=False,
                                      related_payments=False):
        """ mark bounced and unsent cheque"""
        for record in self:
            record.unmark_as_sent()
            company_currency = record.journal_id.company_id.currency_id
            amount_currency = abs(record._get_payment_amount())
            currency = company_currency
            if record.currency_id != company_currency:
                amount_currency = record._get_payment_amount(company_currency=False)
                currency = record.currency_id
            liquidity_analytic_tag_ids = False
            if hasattr(record, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
            move = record._create_pdc_journal_entry(
                journal=record.journal_id,
                partner=record.partner_id,
                label='Cheque Bounced %s - %s' % (record.memo, record.name),
                amount=record._get_payment_amount(),
                debit_account=record.destination_account_id,
                credit_account=record.journal_id.pdc_check_under_collection_account_id,
                amount_currency=amount_currency,
                currency=currency,
                ref=record.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='bounced',
                date=bounce_date,
            )
            record.bounced_move_id = move.id

            """
            - keep history of reconciled move.
            - hasattr is used as we do not need to add dependency 
            between modules.
            """
            if hasattr(record, '_save_reconciled_invoice_matching'):
                record._save_reconciled_invoice_matching()
            # unreconcile invoice from payment to set invoice status to unpaid
            payment_receivable_move_lines = record.move_id.line_ids.filtered(
                lambda line: line.account_id == record.destination_account_id)
            if record.reconciled_invoice_ids:
                payment_receivable_move_lines.remove_move_reconcile()
            bounce_receivable_move_line = move.line_ids.filtered(
                lambda line: line.account_id == record.destination_account_id)
            (payment_receivable_move_lines +
             bounce_receivable_move_line).reconcile()
            if hasattr(record, 'invoice_matching_ids') \
                    and any(not rec.matched_partial_reconcile_ids
                            and not rec.invoice_matching_ids for rec in
                            self):
                record.invoice_matching_ids._compute_invoice_amount()

        # generate 2 payments inbound and outbound
        if record.pdc_state == 'deposit':
            payment_in = self._create_inbound_payment(
                partner, original_payment, related_payments, bounce_date)
        else:
            # take collection payments and remove reconcile with deposit
            payment_in = original_payment.collect_payment_id
            if related_payments:
                payment_in |= related_payments.mapped('collect_payment_id')
            if payment_in:
                payment_in.mapped('move_id.line_ids').remove_move_reconcile()
        payment_out = self._create_outbound_payment(
            partner, original_payment, related_payments, bounce_date)
        if related_payments:
            related_payments.write({
                'related_move_ids': [(6, 0, (payment_in.mapped('move_id') |
                                             payment_out.move_id).ids)]
            })
        if original_payment.journal_id.pdc_check_under_collection_account_id and \
                original_payment.journal_id.pdc_check_under_collection_account_id.reconcile:
            if payment_in and payment_out:
                # @formatter:off
                payment_in_line = payment_in.move_id.line_ids.filtered(
                    lambda line: line.account_id == original_payment.journal_id.pdc_check_under_collection_account_id
                                 and not line.full_reconcile_id and line.balance
                                 and line.account_id.reconcile)
                payment_out_line = payment_out.move_id.line_ids.filtered(
                    lambda line: line.account_id == original_payment.journal_id.pdc_check_under_collection_account_id
                                 and not line.full_reconcile_id and line.balance
                                 and line.account_id.reconcile)
                # @formatter:on
                if payment_in_line and payment_out_line:
                    (payment_in_line + payment_out_line).reconcile()
        self.write({'pdc_state': 'bounced','state': 'in_process'})

    def _create_inbound_payment(self, partner, original_payment,
                                related_payments, bounce_date):
        payment_method_in = self.env.ref('account.account_payment_method_manual_in')
        payment_method_in = \
            original_payment.deposit_pdc_id.bank_journal_id.inbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == payment_method_in)
        if payment_method_in:

            amount = original_payment._get_payment_amount(company_currency=False)
            name = _('Bounce')
            if original_payment.name:
                name += ' ' + original_payment.name
            if original_payment.memo:
                name += ' ' + original_payment.memo
            if related_payments:
                for pay in related_payments:
                    amount += pay._get_payment_amount(company_currency=False)
                    name += ', ' + pay.name if pay.name else ' ' + ' - ' + pay.memo
            vals = {
                'amount': amount,
                'payment_type': 'inbound',
                'currency_id': original_payment.currency_id.id,
                'partner_id': partner.id,
                'partner_type': 'customer',
                'journal_id': original_payment.deposit_pdc_id.bank_journal_id.id,
                'company_id': original_payment.journal_id.company_id.id,
                'payment_method_line_id': payment_method_in[0].id,
                'memo': name,
                'destination_account_id': original_payment.journal_id.pdc_check_under_collection_account_id.id,
                'cheque_payment_id': original_payment.id,
                'cheque_payment_type': 'bounced_in',
                'date': bounce_date,
            }
            # if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
            #     vals.update({
            #         'liquidity_analytic_tag_ids': [
            #             (6, 0, original_payment.liquidity_analytic_tag_ids.ids)],
            #         'counterpart_analytic_tag_ids': [
            #             (6, 0, original_payment.liquidity_analytic_tag_ids.ids)]
            #     })
            payment = self.env['account.payment'].create(vals)
            payment.move_id.cheque_payment_type = 'bounced_in'
            payment.action_post()
            return payment

    def _create_outbound_payment(self, partner, original_payment,
                                 related_payments, bounce_date):
        payment_method_out = self.env.ref('account.account_payment_method_manual_out')
        payment_method_out = \
            original_payment.deposit_pdc_id.bank_journal_id.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == payment_method_out)
        if payment_method_out:
            amount = original_payment._get_payment_amount(company_currency=False)
            # name = _('Bounce') + ' ' + original_payment.name + ' - ' + original_payment.ref
            name = _('Bounce')
            if original_payment.name:
                name += ' ' + original_payment.name
            if original_payment.memo:
                name += ' ' + original_payment.memo
            if related_payments:
                for pay in related_payments:
                    amount += pay._get_payment_amount(company_currency=False)
                    name += ', ' + pay.name if pay.name else ' '+ ' - ' + pay.memo
            vals = {
                'amount': amount,
                'payment_type': 'outbound',
                'currency_id': original_payment.currency_id.id,
                'partner_id': partner.id,
                'partner_type': 'customer',
                'journal_id': original_payment.deposit_pdc_id.bank_journal_id.id,
                'company_id': original_payment.journal_id.company_id.id,
                'payment_method_line_id': payment_method_out[0].id,
                'memo': name,
                'destination_account_id': original_payment.journal_id.pdc_check_under_collection_account_id.id,
                'cheque_payment_id': original_payment.id,
                'cheque_payment_type': 'bounced_out',
                'date': bounce_date,
            }
            # if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
            #     vals.update({
            #         'liquidity_analytic_tag_ids': [
            #             (6, 0, original_payment.liquidity_analytic_tag_ids.ids)],
            #         'counterpart_analytic_tag_ids': [
            #             (6, 0, original_payment.liquidity_analytic_tag_ids.ids)]
            #     })
            payment = self.env['account.payment'].create(vals)
            payment.move_id.cheque_payment_type = 'bounced_out'
            payment.action_post()
            return payment

    def action_open_pdc_receivable_cashed_wizard(self):
        """ convert cheque to collect with cash """
        self.ensure_one()

        return {
            'name': _('Register Cash Payment'),
            'res_model': 'account.payment.cash',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_open_pdc_receivable_bounce_wizard(self):
        """ convert cheque to bounce """
        self.ensure_one()

        return {
            'name': _('Bounce PDC'),
            'res_model': 'account.payment.pdc.bounce',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_open_pdc_receivable_collect_wizard(self):
        """ convert cheque to collect """
        self.ensure_one()

        return {
            'name': _('Collect PDC'),
            'res_model': 'account.payment.pdc.collect',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_open_pdc_receivable_re_collect_wizard(self):
        """ convert cheque to re-collect """
        self.ensure_one()
        ctx = self._context.copy()
        ctx.update({'re_collect': True})
        return {
            'name': _('Re-Deposit PDC'),
            'res_model': 'account.payment.pdc.collect',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    def action_collect_payment_pdc_receivable(self,
                                              collect_date=fields.Date.today(),
                                              partner=False,
                                              original_payment=False,
                                              related_payments=False):
        """ register payment in bank and mark cheque status is collected"""
        
        from_bounce_state = False
        if original_payment.pdc_state in ['deposit', 'bounced','collected']:
            payment = False
            payment_method = self.env.ref('account.account_payment_method_manual_in')
            payment_method = \
                original_payment.deposit_pdc_id.bank_journal_id.inbound_payment_method_line_ids.filtered(
                    lambda line: line.payment_method_id == payment_method)
            if payment_method:
                amount = original_payment._get_payment_amount(company_currency=False)
                name = 'Collect PDC ' + original_payment.name if original_payment.name else '' + ' - ' + original_payment.memo if original_payment.memo else ''
                if original_payment.pdc_state == 'bounced':
                    from_bounce_state = True
                    name = 'Re-Deposit PDC ' + original_payment.name if original_payment.name else '' + ' - ' + original_payment.memo
                if related_payments:
                    for pay in related_payments:
                        amount += pay._get_payment_amount(company_currency=False)
                        name += ', ' + pay.name if pay.name else '' + ' - ' + pay.memo
                vals = {
                    'amount': amount,
                    'payment_type': 'inbound',
                    'currency_id': original_payment.currency_id.id,
                    'partner_id': partner.id,
                    'partner_type': 'customer',
                    'journal_id': original_payment.deposit_pdc_id.bank_journal_id.id,
                    'company_id': original_payment.journal_id.company_id.id,
                    'payment_method_line_id': payment_method[0].id,
                    'memo': name,
                    'cheque_payment_id': original_payment.id,
                    'date': collect_date,
                    'cheque_payment_type': 'collected',
                }
                if original_payment.pdc_state == 'deposit':
                    vals.update({
                        'destination_account_id': original_payment.journal_id.pdc_check_under_collection_account_id.id,
                    })
                if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
                    vals.update({
                        'liquidity_analytic_tag_ids': [(6, 0, original_payment.liquidity_analytic_tag_ids.ids)],
                        'counterpart_analytic_tag_ids': [(6, 0, original_payment.liquidity_analytic_tag_ids.ids)]
                    })
                payment = self.env['account.payment'].create(vals)
                payment.move_id.cheque_payment_type = 'collected'
                payment.action_post()
            if payment:
                payments = original_payment
                if related_payments:
                    payments |= related_payments
                for record in payments:
                    record.collect_payment_id = payment.id
                    record.pdc_state = 'collected'
                    payment_line = record.move_id.line_ids.filtered(
                        lambda line: line.account_id ==
                                     record.journal_id.pdc_notes_receivable_account_id)
                    deposit_line = record.deposit_move_id.line_ids.filtered(
                        lambda line: line.account_id ==
                                     record.journal_id.pdc_notes_receivable_account_id)
                    if payment_line and not payment_line.reconciled \
                            and deposit_line and not deposit_line.reconciled:
                        (payment_line + deposit_line).reconcile()

    def action_recollect_payment_pdc_receivable(self,
                                              collect_date=fields.Date.today(),
                                              partner=False,
                                              original_payment=False,
                                              related_payments=False):
        """ register payment in bank and mark cheque status is collected"""
        from_bounce_state = False
        if original_payment.pdc_state in ['deposit', 'bounced']:

            liquidity_analytic_tag_ids = False
            if hasattr(original_payment, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = original_payment.liquidity_analytic_tag_ids.ids

            payment_method = self.env['account.payment.method.line'].search(
                [('journal_id', '=', original_payment.deposit_move_id.journal_id.id),
                 ('payment_method_id', '=', self.env['account.payment.method'].search([('code', '=', 'manual'),
                                                                                       ('payment_type', '=',
                                                                                        'inbound')]).id)])
            if not original_payment.payment_method_line_id.payment_account_id:
                raise ValidationError(_("You need to configure the outstanding account in the journal!"))

            move = original_payment._create_pdc_journal_entry(
                journal=original_payment.journal_id,
                partner=partner,
                label='ReCollect PDC ' + original_payment.name if original_payment.name else '' + ' - ' + original_payment.memo if original_payment.memo else '',
                amount_currency=original_payment._get_payment_amount(company_currency=False),
                debit_account=payment_method[0].payment_account_id,
                credit_account=original_payment.partner_id.property_account_receivable_id,
                amount=original_payment._get_payment_amount(),
                currency=original_payment.journal_id.company_id.currency_id,
                ref=original_payment.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='collected',
            )
            original_payment.pdc_state = 'collected'
            """
            if move:
                # Reconcile payment with invoice
                for inv in original_payment.invoice_ids:
                    account = inv.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')).account_id
                    lines_to_reconcile = (inv.line_ids + move.line_ids).filtered(
                        lambda line: line.account_id == account and not line.reconciled
                    )
                    if lines_to_reconcile:
                        lines_to_reconcile.reconcile()
            """

    def action_pdc_receivable_recycled(self):
        """ set status to be receyceled to allow deposit again """
        for record in self:
            record.pdc_state = 'recycled'
            reconciled_invoice_ids = record.reconciled_invoice_ids
            if reconciled_invoice_ids:
                vals = {
                    'amount': record._get_payment_amount(company_currency=False),
                    'communication': record.memo,
                    'currency_id': record.currency_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': record.partner_id.id,
                    'journal_id': record.journal_id.id,
                    'payment_method_line_id': record.payment_method_line_id.id,
                    'pdc_bank_id': self.pdc_bank_id.id if self.pdc_bank_id else False,
                    'due_date': self.due_date,
                    'cheque_scanning': self.cheque_scanning,
                    'cheque_owner_id': self.cheque_owner_id.id,
                }
                # if hasattr(self.env['account.payment.register'],
                #            'liquidity_analytic_tag_ids'):
                #     vals.update({
                #         'liquidity_analytic_tag_ids':
                #             [(6, 0, record.liquidity_analytic_tag_ids.ids)],
                #         'counterpart_analytic_tag_ids':
                #             [(6, 0, record.counterpart_analytic_tag_ids.ids)]
                #     })
                if len(reconciled_invoice_ids) > 1:
                    vals.update({
                        'group_payment': True,
                    })
                payment_wizard = self.env['account.payment.register'].with_context(
                    active_model='account.move',
                    active_ids=reconciled_invoice_ids.ids,
                    default_cheque_payment_type='recycled',
                    default_cheque_payment_id=record.id
                ).create(vals)
                new_payment = payment_wizard._create_payments()
            else:
                vals = {
                    'amount': record._get_payment_amount(company_currency=False),
                    'memo': record.memo,
                    'currency_id': record.currency_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': record.partner_id.id,
                    'journal_id': record.journal_id.id,
                    'payment_method_line_id': record.payment_method_line_id.id,
                    'pdc_bank_id': self.pdc_bank_id.id if self.pdc_bank_id else False,
                    'due_date': self.due_date,
                    'cheque_scanning': self.cheque_scanning,
                    'cheque_owner_id': self.cheque_owner_id.id,
                    'company_id': record.journal_id.company_id.id,
                    'cheque_payment_id': record.id,
                    'date': fields.Date.context_today(record),
                    'cheque_payment_type': 'recycled',
                }
                # if hasattr(record, 'liquidity_analytic_tag_ids'):
                #     vals.update({
                #         'liquidity_analytic_tag_ids': [(6, 0, record.liquidity_analytic_tag_ids.ids)],
                #         'counterpart_analytic_tag_ids': [(6, 0, record.counterpart_analytic_tag_ids.ids)]
                #     })
                new_payment = self.env['account.payment'].create(vals)
                new_payment.move_id.cheque_payment_type = 'recycled'
                if hasattr(record, 'invoice_matching_ids'):
                    for invoice_match in record.invoice_matching_ids:
                        data = invoice_match.copy_data({
                            'payment_id': new_payment.id,
                        })
                        new_invoice_match = \
                            self.env['account.payment.invoice.matching'].create(data)
                        new_invoice_match._compute_invoice_amount()
                new_payment.action_post()
            new_payment.move_id.cheque_payment_id = record
            record.recycled_payment_id = new_payment
            action = {
                'name': _('Recycled PDC'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False},
                'view_mode': 'form',
                'res_id': new_payment.id,
                'views': [(self.env.ref(
                    'account_pdc.account_payment_pdc_receivable_form_inherit_primary').id,
                           'form')],
            }
            return action

    def action_open_pdc_receivable_re_cheque_wizard(self):
        """ open wizard to choose another cheque number and return current cheque """
        self.ensure_one()
        return {
            'name': _('Re Cheque'),
            'res_model': 'account.payment.recheque',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                #'default_pdc_bank_id': self.pdc_bank_id.id if self.pdc_bank_id else False,
                'default_due_date': self.due_date,
                'default_cheque_owner_id': self.cheque_owner_id.id if self.cheque_owner_id else False,
            },
            'type': 'ir.actions.act_window',
        }

    def action_open_pdc_receivable_write_off(self):
        """ open wizard to choose amount fees and generate payment with expenses """
        self.ensure_one()
        return {
            'name': _('Write Off'),
            'res_model': 'account.payment.pdc.writeoff',
            'view_mode': 'form',
            'context': {
                'default_account_id': self.journal_id.write_off_pdc_account_id.id,
                'default_ref': 'Write Off ' + self.name if self.name else '' + ' - ' + self.memo,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_create_pdc_receivable_collection_fees(self):
        """ open wizard to choose amount fees and generate payment with expenses """
        self.ensure_one()
        return {
            'name': _('Add Collection Fees'),
            'res_model': 'account.payment.pdc.collection.fees',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.deposit_pdc_id.bank_journal_id.id,
                'default_ref': 'Collection Fees ' + self.name if self.name else '' + ' - ' + self.memo or '',
                'default_currency_id': self.currency_id.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_draft_pdc_receivable(self):
        """ reset cheque to draft """
        self.action_draft()
        self.write({'pdc_state': 'draft'})

    def _compute_pdc_receivable_deposit(self):
        """
        count number of pdc receivable deposit
        """
        deposits = self.env['account.deposit.pdc'].search(
            [('state', '=', 'deposit'), ('payment_deposit_ids', '!=', False)])
        for record in self:
            deposit_count = 0
            if record.deposit_pdc_id and record.deposit_pdc_id not in deposits:
                deposit_count += 1
            for deposit in deposits:
                if record in deposit.payment_deposit_ids:
                    deposit_count += 1
            record.pdc_receivable_deposit_count = deposit_count

    def action_open_pdc_receivable_deposit(self):
        """
        open pdc receivable deposit
        """
        deposits = self.env['account.deposit.pdc'].search(
            [('state', '=', 'deposit'), ('payment_deposit_ids', '!=', False)])
        for record in self:
            related_deposits = self.env['account.deposit.pdc']
            if record.deposit_pdc_id and record.deposit_pdc_id not in deposits:
                related_deposits |= record.deposit_pdc_id
            for deposit in deposits:
                if record in deposit.payment_deposit_ids:
                    related_deposits |= deposit
            action = {
                'name': _("PDC Deposit"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.deposit.pdc',
                'context': {'create': False, 'edit': False},
            }
            if len(related_deposits) == 1:
                action.update({
                    'res_id': related_deposits.id,
                    'view_mode': 'form',
                })
            if len(related_deposits) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account_pdc.account_deposit_pdc_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', related_deposits.ids)],
                })
            return action

    def _compute_pdc_receivable_bounced_move(self):
        """
        count number of bounced journal entries
        """
        for record in self:
            bounced_moves = record.cheque_move_ids.filtered(lambda move: move.cheque_payment_type == 'bounced')
            record.pdc_receivable_bounced_move_count = len(bounced_moves)

    def action_open_pdc_receivable_bounced_move(self):
        """
        open bounced move
        """
        self.ensure_one()
        moves = self.cheque_move_ids.filtered(lambda move: move.cheque_payment_type == 'bounced')
        action = {
            'name': _("Bounced Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False, 'edit': False},
        }
        if len(moves) == 1:
            action.update({
                'res_id': moves.id,
                'view_mode': 'form',
            })
        if len(moves) > 1:
            action.update({
                'view_mode': 'list,form',
                'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
                'domain': [('id', 'in', moves.ids)],
            })
        return action

    def _compute_pdc_receivable_bounced_in_out(self):
        """
        count number of bounced bank transaction
        """
        for record in self:
            bounced_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type in ['bounced_in', 'bounced_out']).mapped('origin_payment_id')
            record.pdc_receivable_bounced_in_out_count = len(bounced_payments)

    def action_open_pdc_receivable_bounced_in_out(self):
        """
        open pdc receivable bounced in / out payments
        """
        for record in self:
            bounced_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type in ['bounced_in', 'bounced_out']).mapped('origin_payment_id')
            action = {
                'name': _("Bounced Bank Transaction"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False, 'edit': False},
            }
            if len(bounced_payments) == 1:
                action.update({
                    'res_id': bounced_payments.id,
                    'view_mode': 'form',
                })
            if len(bounced_payments) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_account_payment_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', bounced_payments.ids)],
                })
            return action

    def _compute_pdc_receivable_collected(self):
        """
        count number of collected bank transaction
        """
        for record in self:
            collected_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'collected').mapped('origin_payment_id')
            record.pdc_receivable_collected_count = len(collected_payments)

    def action_open_pdc_receivable_collected(self):
        """
        open pdc receivable collected payments
        """
        for record in self:
            collected_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'collected').mapped('origin_payment_id')
            action = {
                'name': _("Collect Bank Transaction"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False, 'edit': False},
            }
            if len(collected_payments) == 1:
                action.update({
                    'res_id': collected_payments.id,
                    'view_mode': 'form',
                })
            if len(collected_payments) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_account_payment_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', collected_payments.ids)],
                })
            return action

    def _compute_pdc_receivable_writeoff(self):
        """
        count number of writeoff bank transaction
        """
        for record in self:
            writeoff_moves = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'writeoff')
            record.pdc_receivable_writeoff_count = len(writeoff_moves)

    def action_open_pdc_receivable_writeoff(self):
        """
        open pdc receivable writeoff
        """
        for record in self:
            writeoff_moves = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'writeoff')
            action = {
                'name': _("Write-Off Transaction"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'context': {'create': False, 'edit': False},
            }
            if len(writeoff_moves) == 1:
                action.update({
                    'res_id': writeoff_moves.id,
                    'view_mode': 'form',
                })
            if len(writeoff_moves) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_move_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', writeoff_moves.ids)],
                })
            return action

    def _compute_pdc_receivable_collection_fees(self):
        """
        count number of collection fees bank transaction
        """
        for record in self:
            collection_fees_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'collection_fees'). \
                mapped('origin_payment_id')
            record.pdc_receivable_collection_fees_count = \
                len(collection_fees_payments)

    def action_open_pdc_receivable_collection_fees(self):
        """
        open pdc receivable collection fees payments
        """
        for record in self:
            collection_fees_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'collection_fees'). \
                mapped('origin_payment_id')
            action = {
                'name': _("Collection Fees Transaction"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False, 'edit': False},
            }
            if len(collection_fees_payments) == 1:
                action.update({
                    'res_id': collection_fees_payments.id,
                    'view_mode': 'form',
                })
            if len(collection_fees_payments) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_account_payment_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', collection_fees_payments.ids)],
                })
            return action

    def _compute_pdc_receivable_recheque(self):
        """
        count number of recheque bank transaction
        """
        for record in self:
            recheque_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'recheque').mapped('origin_payment_id')
            record.pdc_receivable_recheque_count = len(recheque_payments)

    def action_open_pdc_receivable_recheque(self):
        """
        open pdc receivable recheque payments
        """
        for record in self:
            recheque_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'recheque').mapped('origin_payment_id')
            action = {
                'name': _("Re-Cheque"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False, 'edit': False},
            }
            if len(recheque_payments) == 1:
                action.update({
                    'res_id': recheque_payments.id,
                    'view_mode': 'form',
                })
            if len(recheque_payments) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_account_payment_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', recheque_payments.ids)],
                })
            return action

    def _compute_pdc_receivable_recycled(self):
        """
        count number of recycled bank transaction
        """
        for record in self:
            recycled_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'recycled').mapped('origin_payment_id')
            record.pdc_receivable_recycled_count = len(recycled_payments)

    def action_open_pdc_receivable_recycled(self):
        """
        open pdc receivable recycled payments
        """
        for record in self:
            recycled_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'recycled').mapped('origin_payment_id')
            action = {
                'name': _("Recycled"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False, 'edit': False},
            }
            if len(recycled_payments) == 1:
                action.update({
                    'res_id': recycled_payments.id,
                    'view_mode': 'form',
                })
            if len(recycled_payments) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_account_payment_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', recycled_payments.ids)],
                })
            return action

    def _compute_pdc_receivable_cashed(self):
        """
        count number of cashed bank transaction
        """
        for record in self:
            cashed_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'cashed').mapped('origin_payment_id')
            record.pdc_receivable_cashed_count = len(cashed_payments)

    def action_open_pdc_receivable_cashed(self):
        """
        open pdc receivable cashed payments
        """
        for record in self:
            cashed_payments = record.cheque_move_ids.filtered(
                lambda move: move.cheque_payment_type == 'cashed').mapped('origin_payment_id')
            action = {
                'name': _("Cash Receipt"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'context': {'create': False, 'edit': False},
            }
            if len(cashed_payments) == 1:
                action.update({
                    'res_id': cashed_payments.id,
                    'view_mode': 'form',
                })
            if len(cashed_payments) > 1:
                action.update({
                    'view_mode': 'list,form',
                    'views': [
                        (self.env.ref('account.view_account_payment_tree').id, 'list'),
                        (False, 'form')],
                    'domain': [('id', 'in', cashed_payments.ids)],
                })
            return action

    # pdc payable functions
    @api.onchange('journal_id', 'payment_type')
    def _onchange_pdc_payable_info(self):
        """ reset pdc payable info if user change journal or payment type """
        if not self.journal_id.pdc_notes_payable_account_id or not self.payment_type == 'outbound':
            self.pdc_payable_note = False
            self.due_date = False

    @api.constrains('journal_id', 'is_pdc_payable')
    def _constrain_pdc_payable_applied(self):
        """
        restrict mark on is_pdc_payable without journal has pdc account
        """
        for record in self:
            if record.is_pdc_payable and record.journal_id \
                    and not record.journal_id.pdc_notes_payable_account_id:
                raise UserError(_('Please add PDC payable account in %s')
                                % record.journal_id.display_name)

    @api.constrains('memo', 'is_pdc_payable', 'journal_id', 'state')
    def _constrain_pdc_payable_cheque_duplicate(self):
        """
        restrict duplicate cheque number based on each journal
        """
        for record in self:
            if record.memo and record.is_pdc_payable and record.journal_id:
                duplicated_pdc_payables = self.search([
                    ('id', '!=', record.id),
                    ('journal_id', '=', record.journal_id.id),
                    ('is_pdc_payable', '=', True),
                    ('memo', '=', record.memo),
                    ('state', 'in', ['draft', 'posted']),
                ])
                if duplicated_pdc_payables:
                    raise UserError(_('Cheque %s was registered before: \n%s')
                                    % (record.memo, ', '.join(pay.name for pay in duplicated_pdc_payables)))

    @api.depends('journal_id', 'payment_type')
    def _compute_can_be_pdc_payable(self):
        """ set true / false based on payment_type, notes_payable account """
        for record in self:
            can_be_pdc_payable = False
            if record.journal_id and record.journal_id.pdc_notes_payable_account_id and record.payment_type == 'outbound':
                can_be_pdc_payable = True
            record.can_be_pdc_payable = can_be_pdc_payable

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency',
                 'move_id.line_ids.account_id')
    def _compute_pdc_payable_state(self):
        """ update pdc payable state based on differance between paid and residual """
        for record in self:
            pdc_payable_state = record.pdc_payable_state
            if record.is_pdc_payable:

                if not record.currency_id or not record.id or record.state == 'draft':
                    pdc_payable_state = 'draft'
                if record.state == 'in_process':
                    pdc_payable_state = 'registered'
                if record.delivered_pdc_payable_move_id:
                    pdc_payable_state = 'delivered'
                if record.cleared_pdc_payable_move_id:
                    pdc_payable_state = 'cleared'
                if record.bounced_move_id:
                    pdc_payable_state = 'bounced'
                if record.state == 'cancel':
                    pdc_payable_state = 'cancel'
            record.pdc_payable_state = pdc_payable_state
            if pdc_payable_state == 'registered':
                record.mark_as_sent()

    def action_pdc_payable_bounced(self):
        """ mark bounced and unsent cheque"""
        for record in self:
            record.unmark_as_sent()
            company_currency = record.journal_id.company_id.currency_id
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            payment_method = \
                record.journal_id.outbound_payment_method_line_ids.filtered(
                    lambda line: line.payment_method_id == payment_method)
            if payment_method:
                amount_currency = abs(record._get_payment_amount())
                currency = company_currency
                if record.currency_id != company_currency:
                    amount_currency = record._get_payment_amount(company_currency=False)
                    currency = record.currency_id
                liquidity_analytic_tag_ids = False
                if hasattr(record, 'liquidity_analytic_tag_ids'):
                    liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
                move = record._create_pdc_journal_entry(
                    journal=record.journal_id,
                    partner=record.partner_id,
                    label='Cheque Bounced %s - %s' % (record.memo, record.name),
                    amount=abs(record._get_payment_amount()),
                    debit_account=record.journal_id.pdc_payable_under_collection_account_id,
                    credit_account=record.destination_account_id,
                    amount_currency=amount_currency,
                    currency=currency,
                    ref=record.name,
                    debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    cheque_payment_type='bounced'
                )

                cleared_move = record._create_pdc_journal_entry(
                    journal=record.journal_id,
                    partner=record.partner_id,
                    label='Cheque Bounced %s - %s' % (record.memo, record.name),
                    amount=abs(record._get_payment_amount()),
                    debit_account=record.outstanding_account_id,
                    credit_account=payment_method.payment_account_id or record.destination_account_id,
                    # credit_account=payment_method.payment_account_id or record.journal_id.company_id.account_journal_payment_credit_account_id,
                    amount_currency=amount_currency,
                    currency=currency,
                    ref=record.name,
                    debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    cheque_payment_type='bounced'
                )

                bounced_move = record._create_pdc_journal_entry(
                    journal=record.journal_id,
                    partner=record.partner_id,
                    label='Cheque Bounced %s - %s' % (record.memo, record.name),
                    amount=abs(record._get_payment_amount()),
                    debit_account=payment_method.payment_account_id or record.outstanding_account_id,
                    # debit_account=payment_method.payment_account_id or record.journal_id.company_id.account_journal_payment_credit_account_id,
                    credit_account=record.destination_account_id,
                    amount_currency=amount_currency,
                    currency=currency,
                    ref=record.name,
                    debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    cheque_payment_type='bounced'
                )
                reversed_move = record._create_pdc_journal_entry(
                    journal=record.journal_id,
                    partner=record.partner_id,
                    label='Cheque Bounced %s - %s' % (record.memo, record.name),
                    amount=abs(record._get_payment_amount()),
                    debit_account=record.journal_id.pdc_payable_under_collection_account_id,
                    credit_account=record.partner_id.property_account_payable_id,
                    amount_currency=amount_currency,
                    currency=currency,
                    ref=record.name,
                    debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                    cheque_payment_type='bounced'
                )

                record.bounced_move_id = bounced_move.id
                record.bounced_cleared_move_id = cleared_move.id
                record.pdc_payable_state = 'bounced'
                # un-reconcile bill to mark invoice not paid
                payment_payable_moves = record.move_id.line_ids.filtered(
                    lambda line: line.account_id == record.destination_account_id)
                if payment_payable_moves:
                    payment_payable_moves.remove_move_reconcile()
                # reconcile bounced with payment to track changes and not appear when reconcile with other transactions
                bounced_payable_moves = record.bounced_move_id.line_ids.filtered(
                    lambda line: line.account_id == record.destination_account_id)
                if bounced_payable_moves and payment_payable_moves:
                    (bounced_payable_moves + payment_payable_moves).reconcile()

                # revrese entry
                bounced_cleared_payable_moves = record.bounced_cleared_move_id.line_ids.filtered(
                    lambda line: line.account_id == record.destination_account_id)
                if bounced_cleared_payable_moves and payment_payable_moves:
                    (bounced_payable_moves + payment_payable_moves).reconcile()

                # reconcile note_payable also
                payment_note_payable_moves = record.move_id.line_ids.filtered(
                    lambda line: line.account_id == record.outstanding_account_id)
                bounced_note_payable_moves = record.bounced_move_id.line_ids.filtered(
                    lambda line: line.account_id == record.outstanding_account_id)
                if payment_note_payable_moves and bounced_note_payable_moves:
                    (payment_note_payable_moves + bounced_note_payable_moves).reconcile()

                # revrese entry
                bounced_cleared_note_payable_moves = record.bounced_cleared_move_id.line_ids.filtered(
                    lambda line: line.account_id == record.outstanding_account_id)
                if bounced_cleared_note_payable_moves and bounced_note_payable_moves:
                    (payment_note_payable_moves + bounced_cleared_note_payable_moves).reconcile()

    def action_pdc_payable_bounce_cancel(self):
        """
        This is the method triggered from PDC Payable form view on click of button "Bounce/Cancel" 
        mark bounced and unsent cheque
            • If bounce:
                • Dr. Bank outstanding account
                • Cr. Trade Payables (OR Advance Payable for Advance Payment)
            • Cancel before clearing:
                • Dr. Post-Dated Checks Payable
                • Cr. Trade Payables (OR Advance Payable for Advance Payment)
        """
        for record in self:
            record.unmark_as_sent()
            company_currency = record.journal_id.company_id.currency_id
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            payment_method = \
                record.journal_id.outbound_payment_method_line_ids.filtered(
                    lambda line: line.payment_method_id == payment_method)
            if payment_method:
                amount_currency = abs(record._get_payment_amount())
                currency = company_currency
                if record.currency_id != company_currency:
                    amount_currency = record._get_payment_amount(company_currency=False)
                    currency = record.currency_id
                liquidity_analytic_tag_ids = False
                if hasattr(record, 'liquidity_analytic_tag_ids'):
                    liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
                
                cr_payable_account = record.partner_id.property_account_payable_id
                if record.advance_sale_purchase:
                    cr_payable_account = record.partner_id.advance_account_payable_id
                # If bounce/cancel before clear:
                if record.pdc_payable_state == 'registered':
                    bounced_move = record._create_pdc_journal_entry(
                        journal=record.journal_id,
                        partner=record.partner_id,
                        label='Cheque Bounced %s - %s' % (record.memo, record.name),
                        amount=abs(record._get_payment_amount()),
                        debit_account=record.journal_id.pdc_notes_payable_account_id,
                        credit_account=cr_payable_account,
                        amount_currency=amount_currency,
                        currency=currency,
                        ref=record.name,
                        debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        cheque_payment_type='bounced'
                    )
                # If bounce/cancel after clear:
                elif record.pdc_payable_state == 'cleared':
                    bounced_move = record._create_pdc_journal_entry(
                        journal=record.journal_id,
                        partner=record.partner_id,
                        label='Cheque Bounced %s - %s' % (record.memo, record.name),
                        amount=abs(record._get_payment_amount()),
                        debit_account=payment_method.payment_account_id or record.outstanding_account_id,
                        credit_account=cr_payable_account,
                        amount_currency=amount_currency,
                        currency=currency,
                        ref=record.name,
                        debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        cheque_payment_type='bounced'
                    )

                record.bounced_move_id = bounced_move.id
                # record.bounced_cleared_move_id = cleared_move.id
                record.pdc_payable_state = 'bounced'
                record.state = 'canceled'
                
                # Un-reconcile bill to mark invoice unpaid
                payable_move_lines = record.move_id.line_ids.filtered(
                    lambda line: line.account_id == cr_payable_account)
                if payable_move_lines:
                    payable_move_lines.remove_move_reconcile()

                # Reconcile Payables (bounce vs payment)
                bounced_payable_lines = bounced_move.line_ids.filtered(
                    lambda line: line.account_id == cr_payable_account)
                if bounced_payable_lines and payable_move_lines:
                    (bounced_payable_lines + payable_move_lines).reconcile()

                # Determine correct liquidity account based on state
                liquidity_account = (
                    record.journal_id.pdc_notes_payable_account_id
                    if record.pdc_payable_state == 'registered'
                    else (payment_method.payment_account_id or record.outstanding_account_id)
                )

                # Reconcile liquidity side (bounce vs payment)
                payment_liquidity_lines = record.move_id.line_ids.filtered(
                    lambda line: line.account_id == liquidity_account)
                bounced_liquidity_lines = bounced_move.line_ids.filtered(
                    lambda line: line.account_id == liquidity_account)
                if payment_liquidity_lines and bounced_liquidity_lines:
                    (payment_liquidity_lines + bounced_liquidity_lines).reconcile()
    
    def action_clear_pdc_payable(self, clear_date=fields.Date.today()):
        """ create another payment for normal bank and reconcile with pdc payable """
        for record in self:
            if record.pdc_payable_state in ['delivered', 'bounced', 'registered']:
                payment_method = self.env.ref('account.account_payment_method_manual_out')
                payment_method = \
                    record.journal_id.outbound_payment_method_line_ids.filtered(
                        lambda line: line.payment_method_id == payment_method)
                if payment_method:
                    amount_currency = abs(record._get_payment_amount())
                    company_currency = record.journal_id.company_id.currency_id
                    currency = record.journal_id.company_id.currency_id
                    if record.currency_id != company_currency:
                        amount_currency = record._get_payment_amount(company_currency=False)
                        currency = record.currency_id
                    liquidity_analytic_tag_ids = False
                    if hasattr(record, 'liquidity_analytic_tag_ids'):
                        liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
                    move = record._create_pdc_journal_entry(
                        journal=record.journal_id,
                        partner=record.partner_id,
                        label='Cheque Cleared %s - %s' % (record.memo, record.name),
                        amount=abs(record._get_payment_amount()),
                        debit_account=record.outstanding_account_id,
                        # debit_account=record.journal_id.pdc_payable_under_collection_account_id,
                        credit_account=payment_method.payment_account_id or record.destination_account_id,
                        # credit_account=payment_method.payment_account_id or record.journal_id.company_id.account_journal_payment_credit_account_id,
                        amount_currency=amount_currency,
                        currency=currency,
                        ref=record.name,
                        date=clear_date,
                        debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        cheque_payment_type='cleared'
                    )
                    record.cleared_pdc_payable_move_id = move.id
                    record.pdc_payable_state = 'cleared'
                    payment_line = record.move_id.line_ids.filtered(
                        lambda line: line.account_id == record.outstanding_account_id)
                    deposit_line = record.cleared_pdc_payable_move_id.line_ids.filtered(
                        lambda line: line.account_id == record.outstanding_account_id)
                    (payment_line + deposit_line).reconcile()

    def action_delivered_pdc_payable(self, delivered_date=fields.Date.today()):
        for record in self:
            if record.pdc_payable_state == 'registered':
                payment_method = self.env.ref('account.account_payment_method_manual_out')
                payment_method = \
                    record.journal_id.outbound_payment_method_line_ids.filtered(
                        lambda line: line.payment_method_id == payment_method)
                if payment_method:
                    amount_currency = record._get_payment_amount()
                    company_currency = record.journal_id.company_id.currency_id
                    currency = company_currency
                    if record.currency_id != company_currency:
                        amount_currency = record._get_payment_amount(company_currency=False)
                        currency = record.currency_id
                    else:
                        currency= company_currency
                    liquidity_analytic_tag_ids = False
                    if hasattr(record, 'liquidity_analytic_tag_ids'):
                        liquidity_analytic_tag_ids = record.liquidity_analytic_tag_ids.ids
                    move = record._create_pdc_journal_entry(
                        journal=record.journal_id,
                        partner=record.partner_id,
                        label='Cheque Delivered %s - %s' % (record.memo, record.name),
                        amount=abs(record._get_payment_amount()),
                        debit_account=record.outstanding_account_id,
                        credit_account=record.destination_account_id,
                        amount_currency=amount_currency,
                        currency=currency,
                        ref=record.name,
                        date=delivered_date,
                        debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                        cheque_payment_type='delivered'
                    )
                    record.delivered_pdc_payable_move_id = move.id
                    record.pdc_payable_state = 'delivered'
                    # payment_line = record.move_id.line_ids.filtered(
                    #     lambda line: line.account_id == record.outstanding_account_id)
                    # deposit_line = record.delivered_pdc_payable_move_id.line_ids.filtered(
                    #     lambda line: line.account_id == record.outstanding_account_id)
                    # (payment_line + deposit_line).reconcile()

    def action_open_pdc_payable_clear_wizard(self):
        """ convert cheque to cleared """
        self.ensure_one()

        return {
            'name': _('Clear PDC'),
            'res_model': 'account.payment.pdc.payable.clear',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_open_pdc_payable_delivered_wizard(self):
        """ convert cheque to cleared """
        self.ensure_one()

        return {
            'name': _('Delivered PDC'),
            'res_model': 'account.payment.pdc.payable.delivered',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _compute_pdc_payable_cleared_move(self):
        """
        count number of cleared journal entries
        """
        for record in self:
            cleared_moves = record.cheque_move_ids.filtered(lambda move: move.cheque_payment_type == 'cleared')
            record.pdc_payable_cleared_move_count = len(cleared_moves)

    def _compute_pdc_payable_delivered_move(self):
        """
        count number of cleared journal entries
        """
        for record in self:
            delivered_moves = record.cheque_move_ids.filtered(lambda move: move.cheque_payment_type == 'delivered')
            record.pdc_payable_delivered_move_count = len(delivered_moves)

    def action_open_pdc_payable_cleared_move(self):
        """
        open bounced move
        """
        self.ensure_one()
        moves = self.cheque_move_ids.filtered(lambda move: move.cheque_payment_type == 'cleared')
        action = {
            'name': _("Cleared Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False, 'edit': False},
        }
        if len(moves) == 1:
            action.update({
                'res_id': moves.id,
                'view_mode': 'form',
            })
        if len(moves) > 1:
            action.update({
                'view_mode': 'list,form',
                'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
                'domain': [('id', 'in', moves.ids)],
            })
        return action

    def action_open_pdc_payable_delivered_move(self):
        """
        open bounced move
        """
        self.ensure_one()
        moves = self.cheque_move_ids.filtered(lambda move: move.cheque_payment_type == 'delivered')
        action = {
            'name': _("Delivered Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False, 'edit': False},
        }
        if len(moves) == 1:
            action.update({
                'res_id': moves.id,
                'view_mode': 'form',
            })
        if len(moves) > 1:
            action.update({
                'view_mode': 'list,form',
                'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
                'domain': [('id', 'in', moves.ids)],
            })
        return action

    # override / inherit functions
    def button_open_journal_entry(self):
        """ override to Redirect the user to journal entry of payments.
        :return: An action on account.move.
        """
        self.ensure_one()
        moves = self.mapped('move_id') | self.mapped('deposit_move_id') \
                | self.mapped('bounced_move_id') \
                | self.mapped('collect_payment_id.move_id') \
                | self.mapped('cheque_move_ids') \
                | self.mapped('cash_payment_id.move_id') \
                | self.mapped('write_off_payment_id') \
                | self.mapped('collection_fees_payment_id.move_id') \
                | self.mapped('recycled_payment_id.move_id') \
                | self.mapped('cleared_pdc_payable_move_id') \
                | self.mapped('delivered_pdc_payable_move_id') \
                | self.mapped('related_move_ids')
        action = {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False, 'edit': False},
        }
        if len(moves) == 1:
            action.update({
                'res_id': moves.id,
                'view_mode': 'form',
            })
        if len(moves) > 1:
            action.update({
                'view_mode': 'list,form',
                'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
                'domain': [('id', 'in', moves.ids)],
            })
        return action

    def _get_valid_liquidity_accounts(self):
        """ inherit to add account fields from journal"""
        result = super()._get_valid_liquidity_accounts()
        return result | (self.journal_id.pdc_notes_receivable_account_id | self.journal_id.pdc_notes_payable_account_id)

    # @api.depends('journal_id', 'payment_type', 'payment_method_line_id')
    # def _compute_outstanding_account_id(self):
    #     """ inherit to get destination account based on pdc """
    #     super()._compute_outstanding_account_id()
    #     for record in self:
    #         if record.journal_id.is_pdc and record.payment_type == 'inbound':
    #             record.outstanding_account_id = record.journal_id.pdc_notes_receivable_account_id
    #         if record.payment_type == 'outbound' and record.is_pdc_payable:
    #             record.outstanding_account_id = record.journal_id.pdc_notes_payable_account_id

    def _seek_for_lines(self):
        """ inherit to add line from check under collection """
        liquidity_lines, counterpart_lines, writeoff_lines = super()._seek_for_lines()
        for line in self.move_id.line_ids:
            if line.account_id in [self.cheque_payment_id.journal_id.pdc_check_under_collection_account_id,
                                   self.cheque_payment_id.journal_id.write_off_pdc_account_id]:
                counterpart_lines += line
        return liquidity_lines, counterpart_lines, writeoff_lines

    # def _get_valid_liquidity_accounts(self):
    #     return (
    #         self.journal_id.default_account_id,
    #         self.payment_method_line_id.payment_account_id,
    #         self.journal_id.company_id.account_journal_payment_debit_account_id,
    #         self.journal_id.company_id.account_journal_payment_credit_account_id,
    #         self.journal_id.inbound_payment_method_line_ids.payment_account_id,
    #         self.journal_id.outbound_payment_method_line_ids.payment_account_id,
    #     )
        # return (
        #     self.journal_id.default_account_id |
        #     self.payment_method_line_id.payment_account_id |
        #     self.journal_id.company_id.account_journal_payment_debit_account_id |
        #     self.journal_id.company_id.account_journal_payment_credit_account_id |
        #     self.journal_id.inbound_payment_method_line_ids.payment_account_id |
        #     self.journal_id.outbound_payment_method_line_ids.payment_account_id
        # )

    def action_post(self):
        """ inherit to set status for cheque """
        super().action_post()
        for record in self:
            if record.is_pdc_payment:
                record.pdc_state = 'registered'
                if not record.journal_id.pdc_check_under_collection_account_id.id:
                    raise UserError(_('Please configure the PDC accounts in selected journal '))
                for line in self.env['account.move.line'].search([('move_id', '=', record.move_id.id)]):
                    if line.account_id.id == record.partner_id.property_account_receivable_id.id:
                        line.account_id = record.journal_id.pdc_check_under_collection_account_id.id
            if record.is_pdc_payable:
                record.pdc_payable_state = 'registered'

    def action_draft(self):
        """ inherit to set status for cheque """
        super().action_draft()
        for record in self:
            #if record.cheque_move_ids and not self.env.context.get('force_reset_draft', False):
            #    raise UserError(_('You can not reset draft as there '
            #                      'are related journal entries'))
            if record.is_pdc_payable:
                record.pdc_payable_state = 'draft'

    def action_cancel(self):
        """ inherit to set status for cheque """
        super().action_cancel()
        for record in self:
            if record.is_pdc_payment:
                record.pdc_state = 'cancel'
            if record.is_pdc_payable:
                record.pdc_payable_state = 'cancel'

    def _get_default_journal(self):
        """ override to force add pdc based on context default"""
        original_journal = self.env['account.move']._search_default_journal(('bank', 'cash'))
        journal = self.env['account.journal']
        if self.env.context('default_is_pdc_payment'):
            company_id = self._context.get('default_company_id', self.env.company.id)
            domain = [('company_id', '=', company_id), ('type', '=', 'bank'), ('is_pdc', '=', True)]
            journal = self.env['account.journal'].search(domain, limit=1)
        return journal if journal else original_journal

    @api.depends('move_id.name')
    def name_get(self):
        """ inherit to add ref beside name based on context """
        if not self.env.context.get('appear_ref', True):
            return super(AccountPayment, self).name_get()
        res = []
        for record in self:
            name = record.name != '/' and record.name or _('Draft Payment')
            memo = record.memo or ''
            if memo:
                name = "%s (%s)" % (name, memo)
            res += [(record.id, name)]
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ inherit to add ref when search"""
        if args is None:
            args = []
        domain = args + ['|', ('name', operator, name), ('memo', operator, name)]
        return super(AccountPayment, self).search(domain, limit=limit).name_get()

    def _get_payment_amount(self, company_currency=True):
        """ return amount of payment based on journal items """
        self.ensure_one()
        payment_move_lines = self.move_id.line_ids.filtered(
            lambda line: line.account_id == self.outstanding_account_id)
        if company_currency:
            payment_company_amount = sum(payment_move_lines.mapped('debit')) or sum(payment_move_lines.mapped('credit'))
        else:
            payment_company_amount = sum(payment_move_lines.mapped('amount_currency'))
        return abs(payment_company_amount)

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))

                if len(counterpart_lines) != 1 and not self._context.get('custom_bypass'):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one receivable/payable account (with an exception of "
                        "internal transfers).",
                        move.display_name,
                    ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

                if counterpart_lines.account_id.account_type == 'asset_receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    @api.depends('move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). 
            OVERRIDE to handle PDC payments reconciled invoices in PDC Payment screen.
        '''
        stored_payments = self.filtered('id')
        if not stored_payments:
            self.reconciled_invoice_ids = False
            self.reconciled_invoices_count = 0
            self.reconciled_invoices_type = False
            self.reconciled_bill_ids = False
            self.reconciled_bills_count = 0
            self.reconciled_statement_line_ids = False
            self.reconciled_statement_lines_count = 0
            return

        # Get all PDC "check under collection" accounts
        pdc_journals = self.env['account.journal'].search([('type', '=', 'bank'), ('is_pdc', '=', True)])
        pdc_accounts = pdc_journals.pdc_check_under_collection_account_id.ids

        # Standard account types for reconciliation
        account_types = ("asset_receivable", "liability_payable")
        self.env['account.payment'].flush_model(fnames=['move_id', 'outstanding_account_id'])
        self.env['account.move'].flush_model(fnames=['move_type', 'origin_payment_id', 'statement_line_id'])
        self.env['account.move.line'].flush_model(fnames=['move_id', 'account_id', 'statement_line_id'])
        self.env['account.partial.reconcile'].flush_model(fnames=['debit_move_id', 'credit_move_id'])

        # Query for standard receivable/payable reconciliation
        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids,
                invoice.move_type
            FROM account_payment payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                part.debit_move_id = counterpart_line.id
                OR
                part.credit_move_id = counterpart_line.id
            JOIN account_move invoice ON invoice.id = counterpart_line.move_id
            JOIN account_account account ON account.id = line.account_id
            WHERE account.account_type IN %(account_types)s
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
            GROUP BY payment.id, invoice.move_type
        ''', {
            'account_types': account_types,
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = self._cr.dictfetchall()

        # Query for PDC "check under collection" reconciliation
        if pdc_accounts:
            self._cr.execute('''
                SELECT
                    payment.id,
                    ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids,
                    invoice.move_type
                FROM account_payment payment
                JOIN account_move move ON move.id = payment.move_id
                JOIN account_move_line line ON line.move_id = move.id
                JOIN account_partial_reconcile part ON
                    part.debit_move_id = line.id
                    OR
                    part.credit_move_id = line.id
                JOIN account_move_line counterpart_line ON
                    part.debit_move_id = counterpart_line.id
                    OR
                    part.credit_move_id = counterpart_line.id
                JOIN account_move invoice ON invoice.id = counterpart_line.move_id
                WHERE line.account_id IN %(pdc_accounts)s
                    AND payment.id IN %(stored_payments)s
                    AND line.id != counterpart_line.id
                    AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                GROUP BY payment.id, invoice.move_type
            ''', {
               'pdc_accounts': tuple(pdc_accounts),
               'stored_payments': tuple(stored_payments.ids)
            })
            pdc_query_res = self._cr.dictfetchall()
            query_res += pdc_query_res

        # Aggregate results

        for pay in self:
            pay.reconciled_invoice_ids = self.env['account.move']
            pay.reconciled_bill_ids = self.env['account.move']

        for res in query_res:
            pay = self.browse(res['id'])
            invoice_ids = res.get('invoice_ids', [])
            if res['move_type'] in self.env['account.move'].get_sale_types(True):
                pay.reconciled_invoice_ids |= self.env['account.move'].browse(invoice_ids)
            else:
                pay.reconciled_bill_ids |= self.env['account.move'].browse(invoice_ids)

        for pay in self:
            pay.reconciled_invoices_count = len(pay.reconciled_invoice_ids)
            pay.reconciled_bills_count = len(pay.reconciled_bill_ids)

        # Statement lines (unchanged)
        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT counterpart_line.statement_line_id) AS statement_line_ids
            FROM account_payment payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_account account ON account.id = line.account_id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                part.debit_move_id = counterpart_line.id
                OR
                part.credit_move_id = counterpart_line.id
            WHERE account.id = payment.outstanding_account_id
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND counterpart_line.statement_line_id IS NOT NULL
            GROUP BY payment.id
        ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = dict((payment_id, statement_line_ids) for payment_id, statement_line_ids in self._cr.fetchall())

        for pay in self:
            statement_line_ids = query_res.get(pay.id, [])
            pay.reconciled_statement_line_ids = [Command.set(statement_line_ids)]
            pay.reconciled_statement_lines_count = len(statement_line_ids)
            if len(pay.reconciled_invoice_ids.mapped('move_type')) == 1 and pay.reconciled_invoice_ids[0].move_type == 'out_refund':
                pay.reconciled_invoices_type = 'credit_note'
            else:
                pay.reconciled_invoices_type = 'invoice'