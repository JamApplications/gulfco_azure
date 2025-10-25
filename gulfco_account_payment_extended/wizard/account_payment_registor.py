from odoo import fields, models, api, _, Command
from datetime import date
from odoo.exceptions import ValidationError,UserError
from dateutil.relativedelta import relativedelta



class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_pdc_payment = fields.Boolean(
        related=False,compute="_compute_is_payment",store=True,
    )
    payment_mode = fields.Selection([('pdc','PDC'),('cdc','CDC'),('bank','Bank'),('cash','Cash')],compute="compute_payment_mode",store=True)
    is_cdc_payment = fields.Boolean(
        related=False,compute="_compute_is_payment",store=True
    )
    external_email = fields.Char(string="External Email")
    cheque_owner = fields.Char(string="Cheque Owner")
    custodian_id = fields.Many2one('custodian',string='Custodian',compute="compute_custodian_id",store=True)

    @api.constrains('amount', 'payment_type')
    def _check_inbound_amount_non_zero(self):
        for payment in self:
            if payment.payment_type == 'inbound' and payment.amount == 0:
                raise UserError("Payment amount cannot be zero.")

    @api.constrains('cheque_number','payment_mode')
    def _check_cheque_number(self):
        for record in self:
            if record.payment_mode in ['cdc','pdc'] and record.payment_type == 'inbound':
                if record.cheque_number:
                    length = len(str(record.cheque_number))
                    if length < 6 or length > 12:
                        raise UserError("Cheque number must be between 6 and 12 characters long.")

    @api.depends('responsible_id')
    def compute_custodian_id(self):
        for record in self:
            custodian_id = False
            if record.responsible_id:
                custodian_record = self.env['custodian'].sudo().search([('responsible_custodian','=',record.responsible_id.id)],limit=1)
                if custodian_record:
                    custodian_id = custodian_record.id
            record.custodian_id = custodian_id

    @api.depends('payment_type', 'journal_id', 'currency_id','custodian_id')
    def _compute_payment_method_line_fields(self):
        super()._compute_payment_method_line_fields()
        for pay in self:
            if pay.payment_type == 'inbound':
                if pay.custodian_id and pay.custodian_id.journal_ids and pay.custodian_id.inbound_payment_method_line_ids:
                    journal_ids = pay.custodian_id.inbound_payment_method_line_ids.mapped('journal_id')
                    if journal_ids and pay.journal_id in journal_ids:
                        pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda s:s._origin.id in pay.custodian_id.inbound_payment_method_line_ids.ids)

    @api.depends('payment_type', 'company_id', 'can_edit_wizard')
    def _compute_available_journal_ids(self):
        for wizard in self:
            available_journals = self.env['account.journal']
            for batch in wizard.batches:
                available_journals |= wizard._get_batch_available_journals(batch)
            if wizard.custodian_id and wizard.custodian_id.journal_ids and wizard.payment_type == 'inbound':
                available_journals = available_journals.filtered(lambda s:s.id in wizard.custodian_id.journal_ids.ids)
            wizard.available_journal_ids = [Command.set(available_journals.ids)]

    @api.depends('available_journal_ids','custodian_id')
    def _compute_journal_id(self):
        for wizard in self:
            if wizard.journal_id in wizard.available_journal_ids:
                continue
            move_payment_method_lines = wizard.line_ids.move_id.preferred_payment_method_line_id
            if move_payment_method_lines and len(move_payment_method_lines) == 1:
                if wizard.custodian_id and wizard.custodian_id.journal_ids and wizard.payment_type == 'inbound':
                    if move_payment_method_lines.journal_id in wizard.custodian_id.journal_ids:
                        wizard.journal_id = move_payment_method_lines.journal_id
                else:
                    move_payment_method_lines.journal_id
            elif wizard.can_edit_wizard:
                batch = wizard.batches[0]
                journal_id = wizard._get_batch_journal(batch)
                if wizard.custodian_id and wizard.custodian_id.journal_ids and wizard.payment_type == 'inbound':
                    if journal_id in wizard.custodian_id.journal_ids:
                        wizard.journal_id = journal_id
                else:
                    wizard.journal_id = journal_id
            else:
                if wizard.custodian_id and wizard.custodian_id.journal_ids and wizard.payment_type == 'inbound':
                    wizard.journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(wizard.company_id),
                        ('type', 'in', ('bank', 'cash', 'credit')),
                        ('id', 'in', self.available_journal_ids.ids),('id','in',wizard.custodian_id.journal_ids.ids)
                    ], limit=1)
                else:
                    wizard.journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(wizard.company_id),
                        ('type', 'in', ('bank', 'cash', 'credit')),
                        ('id', 'in', self.available_journal_ids.ids)
                    ], limit=1)


    @api.constrains('due_date','payment_mode')
    def _check_cheque_due_date(self):
        for rec in self:
            if rec.due_date and rec.payment_type == 'inbound':
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

    @api.constrains("payment_date")
    def _check_payment_date_future_date(self):
        for record in self:
            if record.payment_type == 'inbound' and record.payment_date and record.payment_date > date.today():
                raise ValidationError('The date cannot be set in the future. Please select a valid date.')

    # @api.onchange("payment_date","payment_type")
    # def _onchange_payment_date_future_date(self):
    #     if self.payment_type == 'inbound' and self.payment_date and self.payment_date > date.today():
    #         raise ValidationError('The date cannot be set in the future. Please select a valid date.')


    @api.depends('payment_method_line_id', 'journal_id')
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

    @api.depends('payment_mode')
    def _compute_is_payment(self):
        for record in self:
            is_pdc_payment = False
            is_cdc_payment = False
            if record.payment_mode == 'pdc':
                is_pdc_payment = True
            elif record.payment_mode == 'cdc':
                is_cdc_payment = True
            record.is_pdc_payment = is_pdc_payment
            record.is_cdc_payment = is_cdc_payment
