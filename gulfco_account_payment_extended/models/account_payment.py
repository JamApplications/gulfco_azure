from datetime import timedelta,date
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
import io
import ast
import xlsxwriter
import base64
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    custodian_id = fields.Many2one('custodian',string='Custodian',compute="compute_custodian_id",store=True,readonly=False, precompute=True)
    payment_mode = fields.Selection([('pdc','PDC'),('cdc','CDC'),('bank','Bank'),('cash','Cash')],compute="compute_payment_mode",store=True)
    is_transfer_created = fields.Boolean(string="Is Transfer Created",copy=False)
    draft_move_line_ids = fields.One2many(
        related='move_id.line_ids',
        string="Draft Journal Items",
        readonly=False
    )
    collector_name = fields.Char(string="Collector Name", store=True)
    external_email = fields.Char(string="External Email")
    cheque_owner = fields.Char(string="Cheque Owner")
    customer_code = fields.Char(string="Customer Code",related="partner_id.customer_code",store=True)
    vendor_code = fields.Char(related="partner_id.vendor_code", store=True)
    journal_type = fields.Selection(related="journal_id.type")
    payment_method_code = fields.Char(related="payment_method_line_id.code")
    transaction_reference = fields.Char(string="Transaction Reference")
    authorization_code = fields.Char(string="Authorization Code")
    payment_method_payment = fields.Selection(
        [
            ('visa', 'Visa Card'),
            ('master', 'MasterCard'),
            ('mercorory', 'Mercorory'),
            ('amex_jcb', 'AMEX JCB'),
            ('other', 'Other'),
        ],
        string="Payment Method Payment"
    )
    holder_card_name = fields.Char(string="Holder Card Name")
    is_pay_by_link = fields.Boolean(related="payment_method_id.is_pay_by_link",store=True)
    payment_amount_residual = fields.Monetary(string='Amount Residual',compute="compute_payment_amount_residual",store=True)
    payment_outstanding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Payment Outstanding Account",
        store=True,
        index='btree_not_null',
        compute='_compute_payment_outstanding_account_id',
        check_company=True)
    is_statement_line_created = fields.Boolean(copy=False)
    is_cash_remittance = fields.Boolean(string="IS Cash Remittance")

    @api.constrains('custodian_id')
    def check_custodian_payment_transfer(self):
        for record in self:
            if record.custodian_id and not self.env.context.get('from_payment_transfer'):
                payment_transfer = self.env['payments.transfer'].search([('state','=','in_progress'),"|",('from_custodian_id','=',record.custodian_id.id),('to_custodian_id','=',record.custodian_id.id)])
                if payment_transfer:
                    raise UserError('This Custodian has payment transfer is in process so please complete first that')


    @api.depends('payment_method_line_id','payment_mode','payment_type','journal_id')
    def _compute_payment_outstanding_account_id(self):
        for pay in self:
            payment_outstanding_account_id = False
            if pay.payment_type == 'inbound' and pay.payment_mode == 'pdc':
                payment_outstanding_account_id = pay.payment_method_line_id.payment_account_id
                # payment_outstanding_account_id = pay.journal_id.pdc_check_under_collection_account_id
            elif  pay.payment_type == 'inbound' and pay.payment_mode == 'cdc':
                payment_outstanding_account_id = pay.payment_method_line_id.payment_account_id
                # payment_outstanding_account_id = pay.journal_id.cdc_check_under_collection_account_id
            pay.payment_outstanding_account_id =  payment_outstanding_account_id

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
        # self._cr.execute('''
        #     SELECT
        #         payment.id,
        #         ARRAY_AGG(DISTINCT counterpart_line.statement_line_id) AS statement_line_ids
        #     FROM account_payment payment
        #     JOIN account_move move ON move.id = payment.move_id
        #     JOIN account_move_line line ON line.move_id = move.id
        #     JOIN account_account account ON account.id = line.account_id
        #     JOIN account_partial_reconcile part ON
        #         part.debit_move_id = line.id
        #         OR
        #         part.credit_move_id = line.id
        #     JOIN account_move_line counterpart_line ON
        #         part.debit_move_id = counterpart_line.id
        #         OR
        #         part.credit_move_id = counterpart_line.id
        #     WHERE account.id = payment.outstanding_account_id or account.id = payment.payment_outstanding_account_id
        #         AND payment.id IN %(payment_ids)s
        #         AND line.id != counterpart_line.id
        #         AND counterpart_line.statement_line_id IS NOT NULL
        #     GROUP BY payment.id
        # ''', {
        #     'payment_ids': tuple(stored_payments.ids)
        # })
        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT counterpart_line.statement_line_id) AS statement_line_ids
            FROM account_payment payment
            LEFT JOIN account_move move ON move.id = payment.move_id
            LEFT JOIN account_move deposit_move ON deposit_move.id = payment.deposit_move_id
            LEFT JOIN account_move_line line ON line.move_id IN (payment.move_id, payment.deposit_move_id)
            LEFT JOIN account_account account ON account.id = line.account_id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                (part.debit_move_id = counterpart_line.id OR part.credit_move_id = counterpart_line.id)
                AND counterpart_line.id != line.id
                AND counterpart_line.statement_line_id IS NOT NULL
            WHERE account.id = payment.outstanding_account_id or account.id = payment.payment_outstanding_account_id
                AND payment.id IN %(payment_ids)s
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

    def _seek_for_lines(self):
        liquidity_lines, counterpart_lines, writeoff_lines = super()._seek_for_lines()
        # if self.payment_type == 'inbound' and self.payment_mode in ['pdc'] and self.payment_outstanding_account_id and self.deposit_move_id:
        if self.reconciled_statement_line_ids and self.payment_type == 'inbound' and self.payment_mode in ['cdc','pdc'] and self.payment_outstanding_account_id and self.deposit_move_id:
            for line in self.deposit_move_id.line_ids:
                if line.account_id != self.payment_outstanding_account_id:
                    liquidity_lines += line
            # if self.payment_mode == 'pdc':
            #     for line in self.deposit_move_id.line_ids:
            #         if line.account_id == self.payment_outstanding_account_id:
            #             counterpart_lines += line
            # elif self.payment_mode == 'cdc':
            #     for line in self.deposit_move_id.line_ids:
            #         if line.account_id != self.payment_outstanding_account_id:
            #             counterpart_lines += line


        return liquidity_lines, counterpart_lines, writeoff_lines

    @api.depends('move_id','move_id.line_ids','move_id.line_ids.amount_residual')
    def compute_payment_amount_residual(self):
        for record in self:
            payment_amount_residual = 0.0
            payment_move_line = record.move_id.line_ids.filtered(lambda s:s.account_type in ('asset_receivable', 'liability_payable'))
            if payment_move_line:
                payment_amount_residual = sum(payment_move_line.mapped('amount_residual'))
            record.payment_amount_residual = payment_amount_residual

    @api.depends('invoice_ids.payment_state', 'move_id.line_ids.amount_residual','deposit_move_id.line_ids.amount_residual','reconciled_statement_line_ids')
    def _compute_state(self):
        super()._compute_state()
        for record in self:
            if record.payment_type == 'inbound' and record.payment_mode == 'pdc' and record.reconciled_statement_line_ids:
                record.state = 'paid'
                record.pdc_state = 'collected'
                record.is_statement_line_created = True
            if record.payment_type == 'inbound' and record.reconciled_statement_line_ids and record.payment_mode == 'cdc':
                record.state = 'paid'
                record.cdc_state = 'collected'
                record.is_statement_line_created = True
            if record.is_statement_line_created and not record.reconciled_statement_line_ids:
                if record.payment_type == 'inbound' and record.payment_mode == 'pdc':
                    record.pdc_state = 'deposit'
                if record.payment_type == 'inbound' and record.payment_mode == 'cdc':
                    record.cdc_state = 'deposit'
            # if record.payment_type == 'inbound' and record.state == 'paid' and record.payment_mode == 'pdc':
            #     record.pdc_state = 'collected'
            # if record.payment_type == 'inbound' and record.state == 'paid' and record.payment_mode == 'cdc':
            #     record.cdc_state = 'collected'

    @api.depends_context('send_cash_remittance')
    @api.depends('company_id', 'partner_id','custodian_id')
    def _compute_journal_id(self):
        for payment in self:
            # default customer payment method logic
            partner = payment.partner_id
            payment_type = payment.payment_type if payment.payment_type in ('inbound', 'outbound') else None
            if not bool(payment._origin) and (partner or payment_type):
                field_name = f'property_{payment_type}_payment_method_line_id'
                default_payment_method_line = payment.partner_id.with_company(payment.company_id)[field_name]
                journal = default_payment_method_line.journal_id
                if journal:
                    if payment.custodian_id and payment.custodian_id.journal_ids and payment_type == 'inbound':
                        if journal in payment.custodian_id.journal_ids:
                            payment.journal_id = journal
                    else:
                        payment.journal_id = journal
                        continue

            company = payment.company_id or self.env.company
            if not payment.journal_id or company != payment.journal_id.company_id:
                if payment.custodian_id and payment.custodian_id.journal_ids and payment_type == 'inbound' and not self.env.context.get('send_cash_remittance'):
                    payment.journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(company),
                        ('type', 'in', ['bank', 'cash', 'credit']),('id','in',payment.custodian_id.journal_ids.ids)
                    ], limit=1)
                elif self.env.context.get('send_cash_remittance'):
                    if payment.custodian_id and payment.custodian_id.journal_ids:
                        payment.journal_id = self.env['account.journal'].search([
                            *self.env['account.journal']._check_company_domain(company),
                            ('type', 'in', ['cash']), ('id', 'in', payment.custodian_id.journal_ids.ids)
                        ], limit=1)
                    else:
                        payment.journal_id = self.env['account.journal'].search([
                            *self.env['account.journal']._check_company_domain(company),
                            ('type', 'in', ['cash'])], limit=1)
                else:
                    payment.journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(company),
                        ('type', 'in', ['bank', 'cash', 'credit']),
                    ], limit=1)

    @api.depends_context('send_cash_remittance')
    @api.depends('payment_type','custodian_id')
    def _compute_available_journal_ids(self):
        journals = self.env['account.journal'].search([
            '|',
            ('company_id', 'parent_of', self.env.company.id),
            ('company_id', 'child_of', self.env.company.id),
            ('type', 'in', ('bank', 'cash', 'credit')),
        ])
        for pay in self:
            if pay.payment_type == 'inbound' and not self.env.context.get('send_cash_remittance'):
                if pay.custodian_id and pay.custodian_id.journal_ids and pay.payment_type == 'inbound':
                    journals = journals.filtered(lambda s:s.id in pay.custodian_id.journal_ids.ids)
                pay.available_journal_ids = journals.filtered('inbound_payment_method_line_ids')
            elif self.env.context.get('send_cash_remittance'):
                journals = journals.filtered(lambda s:s.type == 'cash')
                if pay.custodian_id and pay.custodian_id.journal_ids:
                    journals = journals.filtered(lambda s:s.id in pay.custodian_id.journal_ids.ids)
                if pay.payment_type == 'inbound':
                    pay.available_journal_ids = journals.filtered('inbound_payment_method_line_ids')
                else:
                    pay.available_journal_ids = journals.filtered('outbound_payment_method_line_ids')
            else:
                pay.available_journal_ids = journals.filtered('outbound_payment_method_line_ids')

    @api.depends('payment_type', 'journal_id', 'currency_id','is_internal_transfer','journal_id')
    def _compute_payment_method_line_fields(self):
        super()._compute_payment_method_line_fields()
        for pay in self:
            if pay.payment_type == 'inbound' and not self.env.context.get('send_cash_remittance'):
                if pay.custodian_id and pay.custodian_id.journal_ids and pay.payment_type == 'inbound' and pay.custodian_id.inbound_payment_method_line_ids:
                    journal_ids = pay.custodian_id.inbound_payment_method_line_ids.mapped('journal_id')
                    if journal_ids and pay.journal_id in journal_ids:
                        pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda s:s._origin.id in pay.custodian_id.inbound_payment_method_line_ids.ids)
            elif self.env.context.get('send_cash_remittance'):
                if pay.custodian_id and pay.custodian_id.journal_ids and pay.payment_type == 'inbound' and pay.custodian_id.inbound_payment_method_line_ids:
                    journal_ids = pay.custodian_id.inbound_payment_method_line_ids.mapped('journal_id')
                    if journal_ids and pay.journal_id in journal_ids:
                        pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda s:s._origin.id in pay.custodian_id.inbound_payment_method_line_ids.ids)

    @api.constrains('amount', 'payment_type')
    def _check_inbound_amount_non_zero(self):
        for payment in self:
            if payment.payment_type == 'inbound' and payment.amount == 0:
                raise UserError("Payment amount cannot be zero.")
    
    @api.constrains('due_date','payment_mode')
    def _check_cheque_due_date(self):
        for rec in self:
            if rec.due_date and rec.payment_type == 'outbound':
                if rec.payment_mode == 'pdc' and rec.due_date <= fields.Date.context_today(rec) and rec.state == 'draft':
                    raise UserError(_('PDC maturity date must be a future date.'))  
                elif rec.payment_mode == 'cdc' and rec.due_date > fields.Date.context_today(rec):
                    raise UserError(_('CDC maturity date must be today or a past date.'))
            
            elif rec.due_date and rec.payment_type == 'inbound':
                today = fields.Date.context_today(rec)
                max_date = today + relativedelta(months=6)
                min_date = today - relativedelta(months=6)
                if rec.payment_mode == 'pdc':
                    if rec.due_date <= today and rec.state == 'draft':
                        raise UserError(_('PDC maturity date must be a future date.'))
                    # if rec.due_date > max_date:
                    #     raise UserError("Due Date cannot be more than 6 months from today.")
                if rec.payment_mode == 'cdc':
                    if rec.due_date > today:
                        raise UserError(_('CDC maturity date must be today or a past date.'))
                    if rec.due_date < min_date:
                        raise UserError("Due Date cannot be older than 6 months for CDC.")

    @api.constrains("date")
    def _check_payment_date_future_date(self):
        for record in self:
            if record.payment_type == 'inbound' and record.date and record.date > date.today():
                raise UserError('The date cannot be set in the future. Please select a valid date.')

    @api.constrains('pdc_ref','cdc_ref','payment_mode')
    def _check_pdc_ref_cdc_ref_number(self):
        for record in self:
            if record.pdc_ref and record.payment_mode == 'pdc' and record.payment_type == 'inbound':
                length = len(record.pdc_ref)
                if length < 6 or length > 12:
                    raise UserError("Cheque number must be between 6 and 12 characters long.")
            if record.cdc_ref and  record.payment_mode == 'cdc'  and record.payment_type == 'inbound':
                length = len(record.cdc_ref)
                if length < 6 or length > 12:
                    raise UserError("Cheque number must be between 6 and 12 characters long.")

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        # Generate journal entry immediately on Payment Creation (Draft State) just like in Odoo 17
        # Instead of generating entry on post, we generate it on create
        write_off_line_vals_list = []
        force_balance_vals_list = []
        linecomplete_line_vals_list = []

        for vals in vals_list:

            # Hack to add a custom write-off line.
            write_off_line_vals_list.append(vals.get('write_off_line_vals', None))

            # Hack to force a custom balance.
            force_balance_vals_list.append(vals.get('force_balance', None))

            # Hack to add a custom line.
            linecomplete_line_vals_list.append(vals.get('line_ids', None))

        payments = super().create(vals_list)

        for i, (pay, vals) in enumerate(zip(payments, vals_list)):

            if not (
                write_off_line_vals_list[i] is not None
                or force_balance_vals_list[i] is not None
                or linecomplete_line_vals_list[i] is not None
            ) and pay.journal_id.generate_entry_on_draft_payment:
                
                pay.with_context(is_draft_payment=True)._generate_journal_entry()
                # propagate the related fields to the move as it is being created after the payment
                if move_vals := {
                    fname: value
                    for fname, value in vals.items()
                    if self._fields[fname].related and (self._fields[fname].related or '').split('.')[0] == 'move_id'
                    and fname != 'draft_move_line_ids'
                }:
                    pay.move_id.write(move_vals)
        return payments
    
    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        # OVERRIDE
        need_move = self.filtered(lambda p: not p.move_id and p.outstanding_account_id)
        assert len(self) == 1 or (not write_off_line_vals and not force_balance and not line_ids)

        move_vals = [
            pay._generate_move_vals(write_off_line_vals, force_balance, line_ids)
            for pay in need_move
        ]
        moves = self.env['account.move'].create(move_vals)
        for pay, move in zip(need_move, moves):
            if self._context.get('is_draft_payment', False): # Custom context to handle draft payments entry creation
                pay.write({'move_id': move.id})
                
                # For Advance Payment
                if pay.advance_sale_purchase == 'purchase':
                    move.line_ids.filtered(lambda x: x.debit > 0).update(
                        {'account_id': pay.partner_id.advance_account_payable_id.id})
                if pay.advance_sale_purchase == 'sale':
                    move.line_ids.filtered(lambda x: x.credit > 0).update(
                        {'account_id': pay.partner_id.advance_account_receivable_id.id})
                    
                # PDC/CDC
                rec = pay
                if rec.payment_mode == 'pdc' and rec.payment_type == 'inbound' and not rec.is_pdc_payable:
                    if not rec.journal_id.pdc_check_under_collection_account_id.id:
                        raise UserError(_('Please configure the PDC accounts in selected journal '))
                    for line in self.env['account.move.line'].search([('move_id', '=', rec.move_id.id)]):
                        if line.account_id.id == rec.partner_id.property_account_receivable_id.id:
                            line.account_id = rec.journal_id.pdc_check_under_collection_account_id.id
                        
                elif rec.payment_mode == 'cdc' and rec.payment_type == 'inbound' and not rec.is_cdc_payable:
                    if not rec.journal_id.cdc_notes_receivable_account_id.id:
                        raise UserError(_('Please configure the CDC accounts in selected journal '))
                    move.line_ids.filtered(lambda x: x.debit > 0).update(
                        {'account_id': rec.journal_id.cdc_notes_receivable_account_id.id})
                    move.line_ids.filtered(lambda x: x.credit > 0).update(
                        {'account_id': rec.partner_id.property_account_receivable_id.id})
                    # for line in self.env['account.move.line'].search([('move_id', '=', rec.move_id.id)]):
                    #     if line.account_id.id == rec.partner_id.property_account_receivable_id.id:
                    #         line.account_id = rec.journal_id.cdc_check_under_collection_account_id.id
            else:
                pay.write({'move_id': move.id, 'state': 'in_process'})
                
    def action_post(self):
        cash_remittance_payments = self.filtered(lambda s:s.is_cash_remittance)
        if cash_remittance_payments:
            for cash_remittance_payment in cash_remittance_payments:
                if cash_remittance_payment.custodian_id:
                    cash_custodian_report = self.env['custodian.payment.report'].search_read([('custodian_id','=',cash_remittance_payment.custodian_id.id),('payment_method_line_id.journal_id.type','=','cash')])
                    custodian_balance = sum(record['amount'] for record in cash_custodian_report)
                    if not custodian_balance:
                        raise UserError("The custodian does not have an available cash balance.")
                    if cash_remittance_payment.amount < round(custodian_balance,2):
                        raise UserError(
                            f"The transferred amount ({cash_remittance_payment.amount}) cannot be less than the custodian's available cash balance ({custodian_balance})."
                        )
                    elif cash_remittance_payment.amount > round(custodian_balance,2):
                        raise UserError(
                            f"The transferred amount ({cash_remittance_payment.amount}) cannot exceed the custodian's available cash balance ({custodian_balance})."
                        )
        payment =  super(AccountPayment, self).action_post()
        for rec in self:
            if not rec.journal_id.generate_entry_on_draft_payment:
                if rec.advance_sale_purchase == 'purchase':
                    rec.move_id.line_ids.filtered(lambda x: x.debit > 0).update(
                        {'account_id': rec.partner_id.advance_account_payable_id.id})
                elif rec.advance_sale_purchase == 'sale':
                    rec.move_id.line_ids.filtered(lambda x: x.credit > 0).update(
                        {'account_id': rec.partner_id.advance_account_receivable_id.id})
            
                # PDC/CDC
                if rec.payment_mode == 'pdc' and rec.payment_type == 'inbound' and not rec.is_pdc_payable:
                    rec.pdc_state = 'registered'
                    if not rec.journal_id.pdc_check_under_collection_account_id.id:
                        raise UserError(_('Please configure the PDC accounts in selected journal '))
                    for line in self.env['account.move.line'].search([('move_id', '=', rec.move_id.id)]):
                        if line.account_id.id == rec.partner_id.property_account_receivable_id.id:
                            line.account_id = rec.journal_id.pdc_check_under_collection_account_id.id
                    # if rec.is_pdc_payable:
                    #     rec.pdc_payable_state = 'registered'
                        
                elif rec.payment_mode == 'cdc' and rec.payment_type == 'inbound' and not rec.is_cdc_payable:
                    rec.cdc_state = 'registered'
                    if not rec.journal_id.cdc_check_under_collection_account_id.id:
                        raise UserError(_('Please configure the CDC accounts in selected journal '))
                    for line in self.env['account.move.line'].search([('move_id', '=', rec.move_id.id)]):
                        if line.debit > 0:
                            line.account_id = rec.journal_id.cdc_notes_receivable_account_id.id                        
                        elif line.credit > 0:
                            line.account_id = rec.partner_id.property_account_receivable_id.id
                        # if line.account_id.id == rec.partner_id.property_account_receivable_id.id:
                        #     line.account_id = rec.journal_id.cdc_check_under_collection_account_id.id
                    # if rec.is_cdc_payable:
                    #     rec.cdc_payable_state = 'registered'
        return payment

    @api.depends('responsible_id')
    def compute_custodian_id(self):
        for record in self:
            custodian_id = False
            if record.responsible_id:
                custodian_record = self.env['custodian'].sudo().search([('responsible_custodian','=',record.responsible_id.id)],limit=1)
                if custodian_record:
                    custodian_id = custodian_record.id
            record.custodian_id = custodian_id

    @api.depends('payment_mode')
    def _compute_is_cdc_payment(self):
        """ mark payment is cdc or not """
        for record in self:
            record.is_cdc_payment = True if record.payment_mode == 'cdc' else False
    
    @api.depends('journal_id', 'journal_id.is_pdc', 'payment_type', 'payment_mode')
    def _compute_is_pdc_payment(self):
        """ mark payment is pdc or not """
        for record in self:
            record.is_pdc_payment = bool(record.payment_type in ['inbound'] and record.journal_id.is_pdc and record.payment_mode == 'pdc')

    @api.depends('payment_method_line_id','journal_id')
    def compute_payment_mode(self):
        for record in self:
            payment_mode = False
            if record.payment_method_line_id.payment_method_id.is_cdc_method:
                payment_mode = 'cdc'
            elif record.payment_method_line_id.payment_method_id.is_pdc_method:
                payment_mode = 'pdc'
            elif record.journal_id.type == 'bank':
                payment_mode = 'bank'
            elif record.journal_id.type == 'cash':
                payment_mode = 'cash'
            record.payment_mode = payment_mode
    
    @api.depends('journal_id', 'payment_type', 'payment_method_line_id', 'payment_mode')
    def _compute_outstanding_account_id(self):
        """ inherit to get destination account based on pdc/cdc payment type """
        super()._compute_outstanding_account_id()
        for record in self:
            if record.payment_type == 'inbound':
                if record.payment_mode == 'pdc' and record.journal_id.is_pdc:
                    record.outstanding_account_id = record.journal_id.pdc_notes_receivable_account_id
                elif record.payment_mode == 'cdc' and record.journal_id.is_cdc:
                    record.outstanding_account_id = record.journal_id.cdc_notes_receivable_account_id

            elif record.payment_type == 'outbound':
                if record.payment_mode == 'pdc' and record.is_pdc_payable:
                    record.outstanding_account_id = record.journal_id.pdc_notes_payable_account_id
                elif record.payment_mode == 'cdc' and record.is_cdc_payable:
                    record.outstanding_account_id = record.journal_id.cdc_notes_payable_account_id

    @api.onchange("payment_mode")
    def _onchange_payment_mode(self):
        if (
            self._context.get("default_payment_type") == "outbound"
            and self._context.get("default_partner_type") == "supplier"
            and not self._context.get("default_is_pdc_payable", False)
            and not self._context.get("default_is_cdc_payable", False)
        ):
            if self.payment_mode == "cdc":
                self.is_cdc_payable = True
                self.is_pdc_payable = False
            elif self.payment_mode == "pdc":
                self.is_pdc_payable = True
                self.is_cdc_payable = False
            else:
                self.is_cdc_payable = False
                self.is_pdc_payable = False

    def action_print_receipt_payment_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("Payment Receipts Report")
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        worksheet.merge_range('A1:H1', "Payment Receipts Report", header_format)
        headers = [
            "Deposit Date", "Customer Name", "Customer Number", "Receipt number",
            "Receipt date", "Gl date", "Status", "Amount SUM", "Payment method dsp","Org id",
            "Maturity date","Applied amount SUM","Unapplied amount","Media","Bank Account No"
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(1, col_num, header, header_format)
        row = 2
        for record in self:
            deposit_date = ''
            if record.deposit_pdc_id:
                deposit_date = record.deposit_pdc_id.deposit_date.strftime('%Y-%m-%d')
            elif record.deposit_cdc_id:
                deposit_date = record.deposit_cdc_id.deposit_date.strftime('%Y-%m-%d')
            total_amount = record.amount
            reconciled_amount = 0.0
            pay_rec_lines = record.cheque_move_ids.mapped('line_ids').filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
            for line in pay_rec_lines:
                for matched in line.matched_debit_ids + line.matched_credit_ids:
                    reconciled_amount += matched.amount
            remaining_amount = total_amount - reconciled_amount
            worksheet.write(row, 0, deposit_date)
            worksheet.write(row, 1, record.partner_id.name or '')
            worksheet.write(row, 2, record.partner_id.customer_code or '')
            worksheet.write(row, 3, record.name)
            worksheet.write(row, 4, record.create_date.strftime('%Y-%m-%d'))
            worksheet.write(row, 5, record.date.strftime('%Y-%m-%d'))
            worksheet.write(row, 6, record.pdc_state)
            worksheet.write(row, 7, record.amount,number_format)
            worksheet.write(row, 8, record.payment_method_line_id.name)
            worksheet.write(row, 9, record.company_id.division_code)
            if record.due_date:
                worksheet.write(row, 10, record.due_date.strftime('%Y-%m-%d'))
            else:
                worksheet.write(row, 10, '')
            worksheet.write(row, 11, reconciled_amount,number_format)
            worksheet.write(row, 12, remaining_amount,number_format)
            worksheet.write(row, 13, record.currency_id.name)
            worksheet.write(row, 14, record.journal_id.name)
            row += 1
        worksheet.set_column(0, 20, 20)
        workbook.close()
        output.seek(0)
        xlsx_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Payment_receips_report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'account.payment',
            'res_id': self[0].id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    
    @api.model
    def cron_send_pdc_due_date_notifications(self):
        """
        Send due date notification emails for Customer PDC Receivable payments
        whose due date is X days from today, where X (1 day or 2 days) is set in config.
        """
        days_before = int(self.env['ir.config_parameter'].sudo().get_param('account_pdc.pdc_mail_notify_days', default='1'))
        notify_date = fields.Date.today() + timedelta(days=days_before)
        notify_states = [
            'registered',
            'deposit',
        ]
        pdc_payments = self.search([
            ('payment_mode', '=', 'pdc'),
            ('due_date', '=', notify_date),
            ('pdc_state', 'in', notify_states),
            ('payment_type', '=', 'inbound'), 
            ('partner_type', '=', 'customer'),  # Only PDC Receivable
        ])
        template = self.env.ref('account_pdc.mail_template_pdc_due_date_notification')
        for payment in pdc_payments:
            if payment.partner_id.email:
                template.send_mail(payment.id, force_send=True)
    
    def action_open_manual_reconciliation_widget(self):
        ''' Open the manual reconciliation widget for the current payment.
        :return: A dictionary representing an action.
        
        Overridden this method to include default PDC Filter in the context to show PDC Under Collection accounts Journal Items
        '''
        self.ensure_one()
        action_values = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_move_line_posted_unreconciled')
        if self.partner_id:
            context = ast.literal_eval(action_values['context'])
            context.update({'search_default_partner_id': self.partner_id.id})
            if self.partner_type == 'customer':
                context.update({'search_default_trade_receivable': 1})
                if self.payment_type == 'inbound' and self.payment_mode == 'pdc':
                    # Set PDC Receivable as default
                    context.update({'search_default_pdc_accounts': 1})
                    context.update({'is_pdc_payment_matching': True})
            elif self.partner_type == 'supplier':
                context.update({'search_default_trade_payable': 1})
            
            action_values['context'] = context
        return action_values  
    
    def get_application_details(self):
        """ Return a list of dicts containing reconciled invoice details for this payment. """
        self.ensure_one()
        result = []

        invoices = self.invoice_ids | self.reconciled_invoice_ids | self.reconciled_bill_ids
        reconciled_total = 0
        company_currency = self.company_id.currency_id
        for inv in invoices:            
            reconciled_lines = inv._get_all_reconciled_invoice_partials()
            for line in reconciled_lines:
                aml = line['aml']
                invoice = aml.move_id                                
                currency = line['currency']
                company_currency = invoice.company_currency_id
                
                if aml.payment_id and aml.payment_id.id == self.id:
                    continue
                
                reconciled_amt = line['amount']
                # if aml.payment_id and aml.payment_id.id == self.id:
                #     reconciled_amt = abs(aml.amount_residual)    
                if currency != company_currency:
                    if invoice.is_exchange and invoice.rate:
                        reconciled_amt = reconciled_amt * invoice.rate
                    else:
                        reconciled_amt = currency._convert(reconciled_amt, company_currency)
                if not float_is_zero(reconciled_amt, precision_rounding=company_currency.rounding):
                    reconciled_total += reconciled_amt
                    result.append({
                        'invoice_name': invoice.name,
                        'branch': invoice.branch,
                        'division': invoice.company_id.name,
                        'reconciled_amount': reconciled_amt,
                        'company_currency': company_currency,
                        'invoice_currency': currency,
                        'is_residual_line': False,
                    })
                    
            reconciled_amt = inv.amount_total - inv.amount_residual
            currency = inv.currency_id
            if currency != company_currency:
                if inv.is_exchange and inv.rate:
                    reconciled_amt = reconciled_amt * inv.rate
                else:
                    reconciled_amt = currency._convert(reconciled_amt, company_currency)
            reconciled_total += reconciled_amt
            result.append({
                'invoice_name': inv.name,
                'branch': inv.branch,
                'division': inv.company_id.name,
                'reconciled_amount': reconciled_amt,
                'company_currency': company_currency,
                'invoice_currency': currency,
                'is_residual_line': False,
            })
        # If partial payment or overpayment exists (i.e., amount not fully matched to invoices)
        # if result and not float_is_zero(self.amount_company_currency_signed - reconciled_total, precision_rounding=company_currency.rounding):
        if result and self.move_id and self.move_id.line_ids:
            reconciled_payment_entry_line = self.move_id.line_ids.filtered(lambda l: l.is_account_reconcile)
            if reconciled_payment_entry_line and not float_is_zero(self.payment_amount_residual, precision_rounding=company_currency.rounding):
                result.insert(0, {
                    'invoice_name': 'UNAPPLIED AMOUNT',
                    'branch': '',
                    'division': self.company_id.name,
                    'reconciled_amount': self.payment_amount_residual,
                    'company_currency': company_currency,
                    'invoice_currency': self.currency_id,
                    'is_residual_line': True,
                })


        return result

    def _get_application_details_total_applied(self):
        self.ensure_one()
        # reconciled_invoices = self.reconciled_invoice_ids | self.reconciled_bill_ids
        # reconciled_total = 0
        # company_currency = self.company_id.currency_id
        
        # Return total matched amount for the payment
        matched_invoices = self.invoice_ids | self.reconciled_invoice_ids | self.reconciled_bill_ids
        if not matched_invoices:
            return 0
        reconciled_total = self.amount_company_currency_signed - abs(self.payment_amount_residual)
        # for inv in reconciled_invoices:
        #     reconciled_amt = inv.amount_total - inv.amount_residual
        #     currency = inv.currency_id
        #     if currency != company_currency:
        #         if inv.is_exchange and inv.rate:
        #             reconciled_amt = reconciled_amt * inv.rate
        #         else:
        #             reconciled_amt = currency._convert(reconciled_amt, company_currency)
        #     reconciled_total += reconciled_amt
        
        return reconciled_total
        
    
    def _get_responsible_employee(self):
        if self.responsible_id and self.responsible_id.employee_ids:
            employee = self.env["hr.employee"].search([('id', 'in', self.responsible_id.employee_ids.ids),
                           ('company_id', 'in', self.env.companies.ids)], limit=1)
            return employee
        
    def _server_action_cancel_payment(self):
        for payment in self:
            if payment.state in ['draft', 'in_process'] \
                and not (payment.is_pdc_payment or payment.is_pdc_payable or payment.is_cdc_payment or payment.is_cdc_payable):
                payment.sudo().action_cancel()

    def _server_action_open_pdc_receivable_bounce_wizard(self):
        """Server action for bulk action: action_open_pdc_receivable_bounce_wizard"""
        for payment in self:
            if payment.payment_mode != 'pdc':
                raise UserError(f"Payment {payment.name} is not a PDC.")
            if payment.is_pdc_payable:
                raise UserError(f"Payment {payment.name} is marked as payable, not receivable.")
            if payment.pdc_state != 'collected':
                raise UserError(f"Payment {payment.name} must be in 'collected' state.")   
        
        return {
            'name': _('Bounce PDC'),
            'res_model': 'account.payment.pdc.bounce',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': self.ids, 'from_server_action': True},
        }       
    def _server_action_open_pdc_receivable_re_collect_wizard(self):
        """Server action for bulk action: action_open_pdc_receivable_re_collect_wizard"""
        for payment in self:
            if payment.payment_mode != 'pdc' or payment.pdc_state not in ['bounced', 'returned']:
                raise UserError("Only PDC Receivable payments in 'Bounced' or 'Returned' state can be re-deposited.") 
        
        ctx = self._context.copy()
        ctx.update({'re_collect': True, 'active_ids': self.ids})
        return {
            'name': _('Re-Deposit PDC'),
            'res_model': 'account.payment.pdc.collect',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }       
    def _server_action_return_pdc(self):
        """Server action for bulk action: action_return_pdc"""
        for payment in self:
            if payment.payment_mode != 'pdc' or payment.pdc_state != 'bounced':
                raise UserError("Only PDC Receivable payments in 'Bounced' state can be returned.") 
        
        self.action_return_pdc()
        
    def _server_action_open_cdc_receivable_collect_wizard(self):
        """Server action for bulk action: action_open_cdc_receivable_collect_wizard"""
        for payment in self:
            if payment.payment_mode != 'cdc':
                raise UserError(f"Payment {payment.name} is not a CDC.")
            if payment.is_cdc_payable:
                raise UserError(f"Payment {payment.name} is marked as CDC Payable, not receivable.")
            if payment.cdc_state != 'deposit':
                raise UserError(f"Payment {payment.name} must be in 'Deposit' state to collect.")
        
        return {
            'name': _('Collect CDC'),
            'res_model': 'account.payment.cdc.collect',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': self.ids, 'from_server_action': True},
        }  
        
    def _server_action_cdc_receivable_deposit_wizard(self):
        """Server action for bulk action: action_cdc_receivable_deposit_wizard"""
        for payment in self:
            if payment.payment_mode != 'cdc':
                raise UserError(f"Payment {payment.name} is not a CDC.")
            
            if payment.is_cdc_payable:
                raise UserError("You cannot deposit this cheque because it is a CDC Payable, not a Receivable.")

            if payment.state != 'in_process':
                raise UserError("The cheque must be in 'In Process' state to deposit.")

            if payment.cdc_state not in ['registered', 'bounced']:
                raise UserError("The cheque must be in 'Registered' or 'Bounced' state to deposit.")
        
        ctx = self._context.copy()
        ctx.update({'default_payment_ids': [(6, 0, self.ids)]})

        return {
            'name': _('Deposit CDC Cheque'),
            'res_model': 'account.deposit.cdc',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        } 
        
    def _server_action_open_cdc_receivable_cashed_wizard(self):
        """Server action for bulk action: action_open_cdc_receivable_cashed_wizard"""
        for payment in self:
            if payment.payment_mode != 'cdc':
                raise UserError(f"Payment {payment.name} is not a CDC.")
            
            if payment.is_cdc_payable:
                raise UserError(f"You cannot mark this cheque: {payment.name} as cashed because it is a CDC Payable.")

            if payment.state != 'in_process':
                raise UserError("The cheque must be in 'In Process' state to deposit.")

            if payment.cdc_state not in ['registered', 'bounced']:
                raise UserError("Only cheques with CDC State 'Registered' or 'Bounced' can be marked as cashed.")
        
        return {
            'name': _('Register Cash Payment'),
            'res_model': 'account.payment.cash',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_payment_ids': self.ids},
        }
            
    def _server_action_open_cdc_receivable_bounce_wizard(self):
        """Server action for bulk action: action_open_cdc_receivable_bounce_wizard"""
        for payment in self:
            if payment.payment_mode != 'cdc':
                raise UserError(f"Payment {payment.name} is not a CDC.")
            if payment.is_cdc_payable:
                raise UserError(f"Payment {payment.name} is marked as CDC Payable, not receivable.")
            if payment.cdc_state != 'deposit':
                raise UserError(f"Payment {payment.name} must be in 'Deposit' state to collect.")
        
        return {
            'name': _('Bounce CDC'),
            'res_model': 'account.payment.cdc.bounce',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': self.ids, 'from_server_action': True},
        } 
            
    def _server_action_open_pdc_receivable_collect_wizard(self):
        """Server action for bulk action: action_open_pdc_receivable_collect_wizard"""
        for rec in self:
            if rec.payment_mode != 'pdc':
                raise UserError("Payment %s is not marked as PDC." % rec.name)
            if rec.is_pdc_payable:
                raise UserError("Payment %s is a PDC Payable. This action applies only to Receivable PDCs." % rec.name)
            #if rec.state != 'in_process':
            #    raise UserError("Payment %s must be in 'In Process' state." % rec.name)
            #if rec.pdc_state != 'deposit':
            #    raise UserError("Payment %s must be in 'Deposit' PDC state." % rec.name)
        
        return {
            'name': _('Collect PDC'),
            'res_model': 'account.payment.pdc.collect',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': self.ids, 'from_server_action': True},
        }  
            
    def _server_action_open_pdc_payable_clear_wizard(self):
        """Server action for bulk action: action_open_pdc_payable_clear_wizard"""
        for rec in self:
            if not rec.is_pdc_payable:
                raise UserError(f"Payment: {rec.name} is not a PDC Payable.")
            if rec.state != 'in_process':
                raise UserError(f"Payment: {rec.name} must be in 'In Process' state.")
            if rec.pdc_payable_state not in ['registered', 'bounced']:
                raise UserError(f"Payment: {rec.name} must be in 'Registered' or 'Bounced' state.")
            if rec.cleared_pdc_payable_move_id:
                raise UserError(f"Payment: {rec.name} is already cleared.")
        
        return {
            'name': _('Clear PDC'),
            'res_model': 'account.payment.pdc.payable.clear',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': self.ids, 'from_server_action': True},
        }
            
    def _server_action_pdc_payable_bounce_cancel(self):
        """Server action for bulk action: action_pdc_payable_bounce_cancel"""
        for rec in self:
            if not rec.is_pdc_payable:
                raise UserError(f"Payment: {rec.name} is not a PDC Payable.")
            if rec.state not in ['in_process','paid']:
                raise UserError(f"Payment: {rec.name} must be in 'In Process' or Paid state.")
            if rec.pdc_payable_state not in ['registered', 'cleared']:
                raise UserError(f"PDC Payable Payment: {rec.name} must be in 'Registered' or 'Cleared' state.")
            if rec.bounced_move_id:
                raise UserError(f"Payment {rec.name} is already bounced.")
        
        return self.action_pdc_payable_bounce_cancel()
            
    def _server_action_open_cdc_payable_clear_wizard(self):
        """Server action for bulk action: action_open_cdc_payable_clear_wizard"""
        for rec in self:
            if not rec.is_cdc_payable:
                raise UserError(f"Payment {rec.name} is not a CDC Payable.")
            if rec.state != 'in_process':
                raise UserError(f"Payment {rec.name} must be in 'In Process' state.")
            if rec.cdc_payable_state not in ['registered', 'bounced']:
                raise UserError(f"Payment {rec.name} must be in 'Registered' or 'Bounced' state.")
            if rec.cleared_cdc_payable_move_id:
                raise UserError(f"Payment {rec.name} is already cleared.")
        
        return {
            'name': _('Clear CDC'),
            'res_model': 'account.payment.cdc.payable.clear',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'active_ids': self.ids, 'from_server_action': True},
        }     
               
    def _server_action_cdc_payable_bounce_cancel(self):
        """Server action for bulk action: action_cdc_payable_bounce_cancel"""
        for rec in self:
            if not rec.is_cdc_payable:
                raise UserError(f"Payment {rec.name} is not a CDC Payable.")
            if rec.state not in ['in_process', 'paid']:
                raise UserError(f"Payment {rec.name} must be in 'In Process' or 'Paid' state.")
            if rec.cdc_payable_state not in ['registered', 'cleared']:
                raise UserError(f"Payment {rec.name} must be in 'Registered' or 'Cleared' state.")
            if rec.bounced_move_id:
                raise UserError(f"Payment {rec.name} is already bounced/cancelled.")
        
        return self.action_cdc_payable_bounce_cancel()
    
    
    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        form_toolbar = res['views'].get('form', {}).get('toolbar') or False
        list_toolbar = res['views'].get('list', {}).get('toolbar') or False
        if options and options.get('action_id'):
            window_action_id = self.env['ir.actions.act_window'].sudo().browse(options.get('action_id'))
            try:
                context_str = window_action_id.context
                context_dict = ast.literal_eval(context_str.strip())
                default_is_cash_remittance = context_dict.get('default_is_cash_remittance', False)
            except Exception as e:
                _logger.error(f"Error parsing context string: {context_str}. Error: {e}")
                default_is_cash_remittance = False
            if default_is_cash_remittance:
                if form_toolbar:
                    if res['views']['form']['toolbar'].get('print', False):
                        res['views']['form']['toolbar']['print'] = []
                if list_toolbar:
                    if res['views']['list']['toolbar'].get('print', False):
                        res['views']['list']['toolbar']['print'] = []

        return res
        
