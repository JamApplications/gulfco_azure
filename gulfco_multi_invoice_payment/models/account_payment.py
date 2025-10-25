# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessError
from dateutil.relativedelta import relativedelta


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    reconcile_invoice_ids = fields.One2many('account.payment.reconcile', 'payment_id', string="Invoices", copy=False)
    is_advance_pay = fields.Boolean(string="Is Advance Payment", compute="_compute_is_advance_payment", store=True)
    is_normal_payment =fields.Boolean()

    @api.depends('advance_sale_purchase')
    def _compute_is_advance_payment(self):
        for rec in self:
            rec.is_advance_pay = rec.advance_sale_purchase in ('purchase', 'sale')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AccountPayment, self).create(vals_list)
        for rec in records:
            if (
                rec.payment_mode in ("pdc", "cdc")
                and rec.payment_type == "outbound"
                and rec.partner_type == "supplier"
                and not rec.cheque_book_line_id
                and rec.payment_type_selection == "quick_payment"
                and rec.journal_id
            ):
                domain = [
                    ("state", "=", "available"),
                    ("journal_id", "=", rec.journal_id.id),
                    "|",
                    ("payment_id", "=", False),
                    ("payment_id", "=", rec.id),
                    "|",
                    ("partner_id", "=", rec.partner_id.id if rec.partner_id else False),
                    ("partner_id", "=", False),
                ]
                cheque = self.env['cheque.book.line'].search(domain, order='id asc', limit=1)
                if cheque:
                    rec.cheque_book_line_id = cheque
        return records

    @api.onchange('partner_id', 'payment_type', 'partner_type')
    def _onchange_partner_id(self):
        if self.payment_type == 'inbound' and self.partner_type == 'customer':
            return
        elif self.payment_type == "outbound" and self.is_internal_transfer == True:
            return
        else:
            if not self.partner_id:
                return
        if self.is_normal_payment:
            return

        partner_id = self.partner_id
        self.reconcile_invoice_ids = [(5,)]

        used_invoice_ids = self.env['account.payment.reconcile'].search([
            ('payment_id.state', '=', 'draft'),
            ('payment_id', '!=', self.id)
        ]).mapped('invoice_id').ids
        move_type = {'outbound': ['in_invoice', 'in_refund'], 'inbound': ['in_refund']}
        moves = self.env['account.move'].sudo().search(
            ['|', ('partner_id.parent_id', '=', self.partner_id.id), ('partner_id', '=', self.partner_id.id),
             ('state', '=', 'posted'),
             ('payment_state', 'not in', ['paid', 'reversed', 'in_payment']),
             ('move_type', 'in', move_type[self.payment_type]),
             ('company_id', '=', self.company_id.id),
             ('id', 'not in', used_invoice_ids)]
        )
        vals = []
        for move in moves:
            partial_paid = move._get_all_reconciled_invoice_partials()
            vals.append((0, 0, {
                'payment_id': self.id,
                'invoice_id': move.id,
                'already_paid': sum([line['amount'] for line in partial_paid]) if partial_paid else 0.0,
                'amount_residual': move.amount_residual,
                'amount_untaxed': move.amount_untaxed,
                'amount_tax': move.amount_tax,
                'currency_id': move.currency_id.id,
                'amount_total': move.amount_total,
                'select_line': True,
                'amount_paid': 0.0,
            }))
        self.reconcile_invoice_ids = vals
        for line in self.reconcile_invoice_ids:
            line._onchange_select_line()
        self.partner_id = partner_id.id
        return

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        if self.is_normal_payment:
            return
        payment_amount = 0.0
        for line in self.reconcile_invoice_ids.filtered(lambda x: x.amount_paid > 0):
            if self.currency_id != line.currency_id:
                payment_amount += line.currency_id._convert(line.amount_paid, self.currency_id, self.env.company, self.date)
            else:
                payment_amount += line.amount_paid
        self.amount = payment_amount

    @api.constrains('amount', 'reconcile_invoice_ids')
    def _check_payment_amount(self):
        for rec in self:
            if rec.is_normal_payment:
                return

            if rec.payment_type == 'outbound' and rec.is_internal_transfer == True:
                continue
            if rec.payment_type == 'inbound':
                continue
            if rec.payment_type == 'inbound' and rec.is_internal_transfer == True:
                continue

            total = 0.0
            for line in rec.reconcile_invoice_ids.filtered(lambda x: x.amount_paid > 0):
                if rec.currency_id != line.currency_id:
                    total += line.currency_id._convert(
                        line.amount_paid, rec.currency_id, rec.company_id, rec.date)
                else:
                    total += line.amount_paid

            # if float_compare(rec.amount, total, precision_rounding=rec.currency_id.rounding) != 0:
            #     raise UserError(_("The payment amount must be equal to the total of selected invoices."))

            if not rec.is_advance_pay and not rec.is_cash_remittance:
                if float_compare(rec.amount, total, precision_rounding=rec.currency_id.rounding) != 0:
                    raise UserError(_("The payment amount must be equal to the total of selected invoices."))

    #  Commented this code to check the payment difference entry
    def action_post(self):
        res = super(AccountPayment, self).action_post()
        move_lines = self.env['account.move.line']
        rec_lines = self.reconcile_invoice_ids
        if rec_lines:
            for line in rec_lines:
                invoice_move = line.invoice_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.account_type in ('liability_payable', 'asset_receivable'))
                payment_move = line.payment_id.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.account_type in ('liability_payable', 'asset_receivable'))
                move_lines |= (invoice_move + payment_move)
                amount_paid = line.amount_paid

                for pay_line in payment_move:
                    line.invoice_id.js_assign_outstanding_line(pay_line.id)

                if self.currency_id != line.currency_id:
                    amount_paid = line.currency_id._convert(line.amount_paid, self.currency_id, self.env.company, self.date)
                else:
                    amount_paid = line.amount_paid
                # if invoice_move and payment_move and len(rec_lines) > 0:
                #     if self.partner_type == 'customer':
                #         rec = self.env['account.partial.reconcile'].create({
                #             'amount': abs(amount_paid),
                #             'debit_amount_currency': abs(line.amount_paid),
                #             'credit_amount_currency': abs(line.amount_paid),
                #             'debit_move_id': invoice_move.id,
                #             'credit_move_id': payment_move.id,
                #         })
                #     else:
                #         rec = self.env['account.partial.reconcile'].create({
                #             'amount': abs(amount_paid),
                #             'debit_amount_currency': abs(line.amount_paid),
                #             'credit_amount_currency': abs(line.amount_paid),
                #             'debit_move_id': payment_move.id,
                #             'credit_move_id': invoice_move.id,
                #         })
            payment_move.filtered(lambda x: not x.reconciled).reconcile()

        return res

    batch = fields.Char(string="Batch")

    payment_type_selection = fields.Selection(
        selection=[
            ('process_request', 'Payment Process Request'),
            ('quick_payment', 'Quick Payment'),
        ],
        string='Payment Request Type',

    )

    @api.onchange('payment_type_selection')
    def _onchange_payment_type_selection(self):
        if self.is_normal_payment:
            return
        if self.payment_type_selection == 'quick_payment':
            if self.payment_type == "outbound" and not self.env.user.has_group("gulfco_multi_invoice_payment.group_allow_quick_payment"):
                self.payment_type_selection = False
                return {
                    'warning': {
                        'title': 'Access Denied',
                        'message': 'You are not allowed to select Quick Payment.'
                    }
                }

    payment_request_id = fields.Char(
        string="Payment Request ID",
        help="Enter a unique numeric ID for the payment request.",
    )

    @api.constrains('payment_request_id')
    def _check_payment_request_id_is_integer(self):
        for rec in self:
            if rec.is_normal_payment:
                return
            if rec.payment_request_id:
                if not rec.payment_request_id.isdigit():
                    raise ValidationError(
                        _("Payment Request ID must be a whole number (no dots, no commas, only digits)."))

    @api.constrains('payment_request_id', 'payment_type_selection')
    def _check_unique_payment_request_id(self):
        for rec in self:
            if rec.is_normal_payment:
                return
            if rec.payment_type_selection == 'process_request' and rec.payment_request_id:
                exists = self.search([
                    ('id', '!=', rec.id),
                    ('payment_request_id', '=', rec.payment_request_id),
                    ('payment_type_selection', '=', 'process_request')
                ], limit=1)
                if exists:
                    raise ValidationError("Payment Request ID must be unique when Payment Type is 'Payment Process Request'.")

    @api.constrains('payment_request_id', 'payment_type_selection')
    def _check_required_payment_request_id(self):
        for rec in self:
            if rec.is_normal_payment:
                return
            if rec.payment_type_selection == 'process_request' and not rec.payment_request_id:
                raise ValidationError("Payment Request ID is required when Payment Type is 'Payment Process Request'.")

    def toggle_select_all_lines(self):
        for rec in self:
            lines = rec.reconcile_invoice_ids
            if all(line.delete_select_line for line in lines):
                lines.write({'delete_select_line': False})
            else:
                lines.write({'delete_select_line': True})

    def delete_selected_lines(self):
        for rec in self:
            lines_to_delete = rec.reconcile_invoice_ids.filtered(lambda l: l.delete_select_line)
            if lines_to_delete:
                lines_to_delete.unlink()

    # custom_workflow_state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('submitted', 'Submitted'),
    #     ('under_review', 'Under Review'),
    #     ('approved', 'Ready to Confirm'),
    # ],
    #     string="Internal Status",
    #     default='draft', tracking=True)

    custom_workflow_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Ready to Confirm'),
        ('rejected', 'Rejected'),
    ],
        string="Internal Status",
        default='draft',
        tracking=True)

    def action_submit_custom(self):
        for rec in self:
            if rec.custom_workflow_state != 'draft':
                continue

            if rec.payment_type_selection == 'quick_payment':
                rec.custom_workflow_state = 'approved'
                continue

            if not rec.partner_id:
                raise UserError(_("Cannot submit: A vendor (partner) must be selected."))

            if not rec.is_advance_pay and not rec.reconcile_invoice_ids:
                raise UserError(_("Cannot submit: At least one invoice must be selected."))

            if rec.payment_type_selection == 'quick_payment':
                rec.custom_workflow_state = 'approved'
                continue

            if rec.payment_type == 'outbound':
                total = 0.0
                for line in rec.reconcile_invoice_ids.filtered(lambda x: x.amount_paid > 0):
                    if rec.currency_id != line.currency_id:
                        total += line.currency_id._convert(
                            line.amount_paid, rec.currency_id, rec.company_id, rec.date)
                    else:
                        total += line.amount_paid

                if not rec.is_advance_pay:
                    if float_compare(rec.amount, total, precision_rounding=rec.currency_id.rounding) != 0:
                        raise UserError(_("Cannot submit: Payment amount must equal the total of selected invoices."))

                # if float_compare(rec.amount, total, precision_rounding=rec.currency_id.rounding) != 0:
                #     raise UserError(_("Cannot submit: Payment amount must equal the total of selected invoices."))

            rec.custom_workflow_state = 'submitted'
            # rec.activity_schedule(
            #     activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
            #     user_id=self.env.ref('account.group_account_manager').users[:1].id,
            #     summary='Review payment submitted',
            #     note='Please review the submitted payment record.',
            # )

    def action_review_custom(self):
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError("You do not have the permission to perform this action.")
        for rec in self:
            if rec.custom_workflow_state == 'submitted':
                rec.custom_workflow_state = 'under_review'

    def action_reject(self):
        for rec in self:
            rec.custom_workflow_state = 'draft'

    def action_approve_custom(self):
        for rec in self:
            if rec.custom_workflow_state in ['draft','under_review']:

                if not rec.partner_id:
                    raise UserError(_("Cannot approve: You must select a vendor (partner) for this payment."))

                if not rec.is_advance_pay and not rec.reconcile_invoice_ids:
                    raise UserError(_("Cannot submit: At least one invoice must be selected."))

                # if not rec.reconcile_invoice_ids:
                #     raise UserError(_("Cannot submit: At least one invoice must be selected."))

                rec.custom_workflow_state = 'approved'
                users_to_notify = self.env.ref('gulfco_multi_invoice_payment.group_payment_notification').users
                for user in users_to_notify:
                    rec.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=user.id,
                        summary="Payment Requires Your Confirmation",
                        note=f"Payment with Voucher No. {rec.voucher_number} needs to be confirmed or cancelled by you.",
                    )
                # rec.message_post(
                #     body=f"Payment with Voucher No. {rec.voucher_number} needs to be confirmed or cancelled by you.",
                #     partner_ids=users_to_notify.partner_id.ids,
                #     subtype_xmlid='mail.mt_note'
                # )
                # rec.payment_type_selection == 'quick_payment'
                if rec.payment_method_id.is_pdc_method or rec.payment_method_id.is_cdc_method:

                    if rec.payment_type == 'outbound' and not rec.cheque_book_line_id and rec.journal_id:
                        domain = [
                            ('state', '=', 'available'),
                            ('journal_id', '=', rec.journal_id.id),
                            '|', ('payment_id', '=', False), ('payment_id', '=', rec.id),
                            '|', ('partner_id', '=', rec.partner_id.id if rec.partner_id else False),
                            ('partner_id', '=', False),
                        ]
                        cheque = self.env['cheque.book.line'].search(domain, order='id asc', limit=1)
                        if cheque:
                            rec.cheque_book_line_id = cheque

    @api.constrains('due_date','payment_mode')
    def _check_cheque_duee_date(self):
        for rec in self:
            if rec.payment_type == 'outbound' and rec.is_internal_transfer == True:
                continue
            if rec.payment_type == 'inbound':
                continue
            if rec.payment_type == 'inbound' and rec.is_internal_transfer == True:
                continue

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


class AccountPaymentReconcile(models.Model):
    _name = 'account.payment.reconcile'

    def _check_full_deduction(self):
        if self.invoice_id:
            payment_ids = [payment['account_payment_id'] for payment in
                           self.invoice_id._get_reconciled_info_JSON_values()]
            if payment_ids:
                payments = self.env['account.payment'].browse(payment_ids)
                return any([True if payment.tds_amt or payment.sales_tds_amt else False for payment in payments])
            else:
                return False

    payment_id = fields.Many2one('account.payment')
    reconcile = fields.Boolean(string="Select")
    invoice_id = fields.Many2one('account.move', required=True)
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', readonly=True)
    amount_total = fields.Monetary(string='Total')
    amount_untaxed = fields.Monetary(string='Untaxed Amount')
    amount_tax = fields.Monetary(string='Taxes Amount')
    already_paid = fields.Monetary("Amount Paid")
    amount_residual = fields.Monetary('Amount Due')
    amount_paid = fields.Monetary(string="Payment Amount")

    @api.onchange('amount_paid')
    def _onchange_amount_paid(self):
        if self.amount_paid > self.amount_residual:
            raise ValidationError(_('You cannot pay more than residual amount.'))


    select_line = fields.Boolean(string='Select', default=False)

    @api.onchange('select_line')
    def _onchange_select_line(self):
        for rec in self:
            if rec.select_line:
                rec.amount_paid = rec.amount_residual
            else:
                rec.amount_paid = 0.0

    delete_select_line = fields.Boolean(string='Select')
