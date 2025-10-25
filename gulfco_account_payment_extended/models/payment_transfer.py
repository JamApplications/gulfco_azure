import datetime

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
from odoo.tools import groupby
from odoo.exceptions import UserError


class PaymentsTransfer(models.Model):
    _name = 'payments.transfer'
    _description = 'Payments Transfer'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'

    name = fields.Char(string="Transfer Reference", required=True, copy=False, readonly=True,default="New")
    internal_transfer = fields.Boolean(string="Internal Transfer", default=True)

    journal_id = fields.Many2one('account.journal', string="Journal", domain="[('type', 'in', ['bank', 'cash'])]",
                                 required=False)
    destination_journal_id = fields.Many2one('account.journal', string="Destination Journal",
                                             domain="[('type', 'in', ['bank', 'cash'])]", required=False)

    payment_type = fields.Selection([
        ('send', 'Send'),
        ('receive', 'Receive')
    ], string="Payment Type", default='send', required=False)

    total_custody_balance = fields.Float(string="Total Custody Balance", compute="_compute_total_balance",
                                            store=True)
    date_from = fields.Date(string="Duration From")
    date_to = fields.Date(string="Duration To")

    from_custodian_id = fields.Many2one('custodian', string="From Custodian")
    to_custodian_id = fields.Many2one('custodian', string="To Custodian")
    from_custodian_code = fields.Char(related='from_custodian_id.custodian_code', string="From Custodian Code")
    from_responsible_custodian = fields.Many2one('res.partner',related="from_custodian_id.responsible_custodian",store=True)

    to_custodian_code = fields.Char(related='to_custodian_id.custodian_code', string="To Custodian Code")
    to_responsible_custodian = fields.Many2one('res.partner',related="to_custodian_id.responsible_custodian",store=True)
    transfer_date = fields.Datetime(string="Transfer Date", readonly=False)
    is_transferred = fields.Boolean(string="Is Transferred",copy=False)

    memo = fields.Text(string="Memo")

    payment_line_ids = fields.One2many('payments.transfer.line', 'transfer_id', string="Payments to be Transferred")
    from_employee_id = fields.Many2one('hr.employee',compute="compute_employee",string="From Employee")
    from_employee_code = fields.Char(string="From Employee Code",related="from_employee_id.employee_code")

    to_employee_id = fields.Many2one('hr.employee',compute="compute_employee",string="To Employee")
    to_employee_code = fields.Char(string="To Employee Code",related="to_employee_id.employee_code")
    related_payment_transfer_id = fields.Many2one('payments.transfer',string="Related Payment Transfer",copy=False)
    is_related_payment_transfer = fields.Boolean(string="Is Related Payment Transfer",copy=False)
    state = fields.Selection([('draft','Draft'),('in_progress','In Progress'),('completed','Completed'),('discarded','Discarded')],string="Status",default="draft",tracking=True)
    from_restriction_custodian_ids = fields.Many2many('custodian','from_custodian_restriction_rel','from_restriction_custodian_id','from_custodian_id',string="From Restriction Custodian",compute='_compute_from_restriction_custodian_ids')

    @api.depends('from_custodian_id')
    def _compute_from_restriction_custodian_ids(self):
        all_custodians = self.env['custodian'].search([])
        for rec in self:
            if rec.from_custodian_id and rec.from_custodian_id.restriction_custodian_ids:
                rec.from_restriction_custodian_ids = rec.from_custodian_id.restriction_custodian_ids.ids
            else:
                rec.from_restriction_custodian_ids = all_custodians.ids

    @api.constrains('payment_type', 'from_custodian_id')
    def _check_same_payment_transfer(self):
        for record in self:
            if record.from_custodian_id and record.payment_type:
                if self.search_count([('from_custodian_id', '=', record.from_custodian_id.id), ('payment_type', '=', record.payment_type),('state','=','draft')]) > 1:
                    raise ValidationError(_("This sender custodian already has a draft transfer document."))

    @api.constrains('name')
    def _check_sequence_number(self):
        for record in self:
            if record.name and record.name != 'New':
                if self.search_count([('name','=',record.name),('id','!=',record.id)]) > 0:
                    raise ValidationError('Sequence Number Must be Unique ')



    # @api.onchange('to_custodian_id')
    # def onchange_to_custodian_id(self):
    #     if self.to_custodian_id and self.from_custodian_id and self.from_custodian_id.restriction_custodian_ids:
    #         if self.to_custodian_id in self.from_custodian_id.restriction_custodian_ids:
    #             raise UserError('this custodian is restricated in from custodian')

    @api.depends('from_responsible_custodian','to_responsible_custodian')
    def compute_employee(self):
        for record in self:
            record.from_employee_id = False
            record.to_employee_id = False
            if record.from_responsible_custodian and record.from_responsible_custodian.employee_ids:
                record.from_employee_id = record.from_responsible_custodian.employee_ids[0].id
            if record.to_responsible_custodian and record.to_responsible_custodian.employee_ids:
                record.to_employee_id = record.to_responsible_custodian.employee_ids[0].id

    # employee_name = fields.Char(string="Employee Name", readonly=False)
    # employee_code = fields.Char(string="Employee Code", readonly=False)

    @api.depends('payment_line_ids.amount')
    def _compute_total_balance(self):
        for rec in self:
            rec.total_custody_balance = sum(line.amount for line in rec.payment_line_ids)

    def action_discard_payment_transfer(self):
        self.state = 'discarded'
        if self.related_payment_transfer_id:
            self.related_payment_transfer_id.state = 'discarded'
        original_payment_transfer_id = self.env['payments.transfer'].search(
            [('related_payment_transfer_id', '=', self.id)])
        if original_payment_transfer_id:
            original_payment_transfer_id.state = 'discarded'


    def action_load_payment(self):
        # line_ids = self.from_custodian_id.line_ids.filtered(lambda s:s.journal_id == self.journal_id)
        # responsible_ids = line_ids.mapped('responsible_custodian')
        # users = responsible_ids.mapped('user_ids')
        users = self.from_custodian_id.responsible_custodian.mapped('user_ids')
        # payment_records = self.env['account.payment'].sudo().search(
        #     [('payment_type', '=', 'inbound'), ('date', '<=', self.date_to),('journal_id','in',self.from_custodian_id.journal_ids.ids),('date', '>=', self.date_from),('responsible_id','=',self.from_custodian_id.responsible_custodian.id),('state','=','in_process')])
        state_list = ['registered','bounced']
        # state_list = ['draft','registered','deposit','collected']
        bank_cash_payment_records = self.env['account.payment']
        pdc_cdc_payment_records = self.env['account.payment']
        if self.from_custodian_id.journal_ids:
            # bank_cash_payment_records = self.env['account.payment'].sudo().search(
            #     [('payment_mode','in',['bank','cash']),
            #      ('custodian_id', '=', self.from_custodian_id.id),
            #      ('state', 'in', ['in_process','paid']),
            #      ('is_transfer_created','=',False),
            #      ('journal_id','in',self.from_custodian_id.journal_ids.ids)])
            cash_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['cash']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 ('state', 'in', ['in_process', 'paid']),
                 ('journal_id', 'in', self.from_custodian_id.journal_ids.ids)])
            bank_cash_payment_records += cash_payment_records
            bank_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['bank']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 ('state', 'in', ['in_process']),
                 ('journal_id', 'in', self.from_custodian_id.journal_ids.ids)])
            bank_cash_payment_records += bank_payment_records
            pdc_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['pdc']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 ('journal_id','in',self.from_custodian_id.journal_ids.ids),
                 '|',('state', '=', 'draft'),('pdc_state','in',state_list)])
            pdc_cdc_payment_records += pdc_payment_records
            cdc_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['cdc']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 ('journal_id', 'in', self.from_custodian_id.journal_ids.ids),
                 '|', ('state', '=', 'draft'),('cdc_state', 'in', state_list)])
            pdc_cdc_payment_records += cdc_payment_records
        else:
            cash_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['cash']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 ('state', 'in', ['in_process','paid']),
                 ('is_transfer_created', '=', False)])
            bank_cash_payment_records += cash_payment_records
            bank_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['bank']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 ('state', 'in', ['in_process']),
                 ('is_transfer_created', '=', False)])
            bank_cash_payment_records += bank_payment_records
            pdc_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode','in',['pdc']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                '|',('state', '=', 'draft'),('pdc_state','in',state_list)])
            pdc_cdc_payment_records += pdc_payment_records
            cdc_payment_records = self.env['account.payment'].sudo().search(
                [('payment_mode', 'in', ['cdc']),
                 ('custodian_id', '=', self.from_custodian_id.id),
                 '|', ('state', '=', 'draft'),('cdc_state', 'in', state_list)])
            pdc_cdc_payment_records += cdc_payment_records
        line_val_list = [(5,0,0)]
        for (journal_id,currency_id),payment_records in groupby(bank_cash_payment_records,lambda s:(s.journal_id,s.currency_id)):
            amount = 0.0
            payment_ids = []
            for payment_record in payment_records:
                amount += payment_record.amount_signed
                # amount += payment_record.amount
                payment_ids.append(payment_record.id)
            if journal_id.type == 'bank':
                payment_method = 'bank'
            else:
                payment_method = 'cash'
            line_vals = {
                'journal_id': journal_id.id,
                'amount' : amount ,
                'currency_id':currency_id.id,
                'payment_ids': payment_ids,
                'payment_method':payment_method,
                'amount_transferred': amount

            }
            line_val_list.append((0,0,line_vals))
        for (payment_mode,currency_id),payment_records in groupby(pdc_cdc_payment_records,lambda s:(s.payment_mode,s.currency_id)):
            amount = 0.0
            payment_ids = []
            journal_id = False
            for payment_record in payment_records:
                # amount += payment_record.amount
                amount += payment_record.amount_signed
                payment_ids.append(payment_record.id)
                journal_id = payment_record.journal_id
            if journal_id:
                line_vals = {
                    'journal_id': journal_id.id,
                    'amount' : amount ,
                    'currency_id':currency_id.id,
                    'payment_ids': payment_ids,
                    'payment_method':payment_mode,
                    'amount_transferred':amount
                }
                line_val_list.append((0,0,line_vals))

        # for responsible_id,payment_records in groupby(payment_records,lambda s:s.responsible_id):
        #     amount = 0.0
        #     payment_ids = []
        #     for payment_record in payment_records:
        #         amount += payment_record.payment_amount
        #         payment_ids.append(payment_record.id)
        #     line_vals = {
        #         'responsible_user_id': responsible_id.id,
        #         'journal_id': self.journal_id.id,
        #         'amount' : amount ,
        #         'currency_id':self.currency_id.id,
        #
        #     }
        #     line_val_list.append((0,0,line_vals))
        self.write({'payment_line_ids':line_val_list})

    def action_create_related_payment_transfer(self):
        if self.from_custodian_id.journal_ids:
            from_custodian_report = self.env['custodian.payment.report'].search_read(
                [('custodian_id', '=', self.from_custodian_id.id),
                 ('payment_method_line_id.journal_id', 'in',self.from_custodian_id.journal_ids.ids)])
        else:
            from_custodian_report = self.env['custodian.payment.report'].search_read(
                [('custodian_id', '=', self.from_custodian_id.id)])
        custodian_balance = sum(record['amount'] for record in from_custodian_report)
        if round(custodian_balance,2) != round(self.total_custody_balance,2):
            raise ValidationError(_(
                'You need to reload your balance to fetch the latest transactions in your custodian.'
            ))
        if self.payment_type == 'send':
            payment_type = 'receive'
        else:
            payment_type = 'send'
        related_payment_transfer_id = self.copy({'payment_type':payment_type,
                                                 'is_related_payment_transfer':True,
                                                 'state':'in_progress',
                                                 'payment_line_ids': [(0, 0, line.copy_data()[0]) for line in self.payment_line_ids]})
        if related_payment_transfer_id:
            original_payment_name = self.env['ir.sequence'].next_by_code('payments.transfer')
            self.write({'related_payment_transfer_id':related_payment_transfer_id.id,'state':'in_progress','name':original_payment_name})
            related_payment_name = self.env['ir.sequence'].next_by_code('payments.transfer')
            related_payment_transfer_id.write({'name': related_payment_name})
        cash_payment_lines = self.payment_line_ids.filtered(lambda s: s.payment_method in ['cash'])
        cash_journal = self.from_custodian_id.journal_ids.filtered(lambda s: s.type == 'cash')
        if not cash_journal and cash_payment_lines:
            self.message_post(body="Cash Journal is not configured in From Custodian",
                                                      subtype_xmlid="mail.mt_comment", message_type="comment")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Please Configure Cash Journal in From Custodian"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        to_cash_journal = self.to_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
        if not to_cash_journal and cash_payment_lines:
            self.message_post(body="Cash Journal is not configured in To Custodian", subtype_xmlid="mail.mt_comment", message_type="comment")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Please Configure Cash Journal in To Custodian"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        if not self.to_custodian_id.journal_ids:
            self.message_post(body="Please Configure the Journal in TO Custodians", subtype_xmlid="mail.mt_comment", message_type="comment")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Please Configure the Journal in TO Custodians"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        if len(set(self.to_custodian_id.journal_ids.mapped('type'))) != len(set(self.from_custodian_id.journal_ids.mapped('type'))):
            self.message_post(body="Please Configure the Same Journal type in From and To custodian",
                              subtype_xmlid="mail.mt_comment",
                              message_type="comment")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Please Configure the Same Journal type in from and to custodian"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        line_ids = []
        transfer_payments = self.env['account.payment']
        for line in cash_payment_lines:
            from_journal = self.from_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
            from_default_account_id = from_journal[0].default_account_id.id
            to_journal = self.to_custodian_id.journal_ids.filtered(lambda s: s.type == 'cash')
            to_default_account_id = to_journal[0].default_account_id.id
            if self.payment_type == 'send':
                line_list = [
                    (0, 0,
                     {
                    "name": "Custodian {} of cash transfer".format(self.to_custodian_id.name),
                    "account_id": to_default_account_id,
                    "currency_id": line.currency_id.id,
                    "debit": line.amount_transferred,
                }, ),
                    (0, 0,
                     {
                         "name": "Custodian {} of cash transfer".format(self.from_custodian_id.name),
                         "account_id": from_default_account_id,
                         "currency_id": line.currency_id.id,
                         "credit": line.amount_transferred,
                     },)
                ]
            else:
                line_list = [
                    (0, 0,
                     {
                         "name": "Custodian {} of cash transfer".format(self.from_custodian_id.name),
                         "account_id": from_default_account_id,
                         "currency_id": line.currency_id.id,
                         "debit": line.amount_transferred,
                     },),
                    (0,0,
                     {
                            "name": "Custodian {} of cash transfer".format(self.to_custodian_id.name),
                            "account_id": to_default_account_id,
                            "currency_id": line.currency_id.id,
                            "credit": line.amount_transferred,
                        },)
                ]
            line_ids += line_list
            transfer_payments += line.payment_ids
        if line_ids:
            move_vals = {
                "date": fields.Date.today(),
                "invoice_date": fields.Date.today(),
                "move_type": "entry",
                'ref': 'Entry of Payment Transfer',
                "journal_id": cash_journal[0].id,
                "line_ids": line_ids,
                "payment_transfer_id": self.id
            }
            self.transfer_date = datetime.datetime.now()
            self.is_transferred = True
            self.env["account.move"].create(move_vals)
        if transfer_payments:
            transfer_payments.sudo().write({'is_transfer_created':True})

    def action_transfer_payment(self):
        original_payment_transfer_id = self.env['payments.transfer'].search(
            [('related_payment_transfer_id', '=', self.id)], limit=1)
        # bank_pdc_cdc_payment_lines = self.payment_line_ids.filtered(lambda s:s.payment_method in ['pdc','cdc','bank'])
        # pdc_cdc_payments = bank_pdc_cdc_payment_lines.mapped('payment_ids')
        # pdc_cdc_payments.sudo().write({'responsible_id': original_payment_transfer_id.to_custodian_id.responsible_custodian.id})
        pdc_cdc_payments = self.payment_line_ids.mapped('payment_ids')

        ids_tuple = tuple(pdc_cdc_payments.ids)
        if len(ids_tuple) == 1:
            ids_tuple = f"({ids_tuple[0]})"  # single ID without trailing comma
        else:
            ids_tuple = str(ids_tuple)

        # pdc_cdc_payments.sudo().write({'responsible_id': original_payment_transfer_id.to_custodian_id.responsible_custodian.id,'custodian_id':original_payment_transfer_id.to_custodian_id.id})
        query = "update account_payment set responsible_id = {},custodian_id = {} where id in {}".format(original_payment_transfer_id.to_custodian_id.responsible_custodian.id,original_payment_transfer_id.to_custodian_id.id,ids_tuple)
        self.env.cr.execute(query)
        move = self.env['account.move'].sudo().search([('payment_transfer_id','=',original_payment_transfer_id.id)])
        if move:
            move.action_post()
        original_payment_transfer_id.state = 'completed'
        self.state = 'completed'
        self.is_transferred = True

    # def action_transfer_payment(self):
    #     # bank_cash_payment_lines = self.payment_line_ids.filtered(lambda s:s.payment_method in ['cash','bank'])
    #     original_payment_transfer_id = self.env['payments.transfer'].search(
    #         [('related_payment_transfer_id', '=', self.id)], limit=1)
    #     cash_payment_lines = self.payment_line_ids.filtered(lambda s:s.payment_method in ['cash'])
    #     # if cash_payment_lines and not any(cash_payment_lines.mapped('amount_transferred')):
    #     #     raise UserError('Please Configure Transfer Amount in Cash lines')
    #     bank_pdc_cdc_payment_lines = self.payment_line_ids.filtered(lambda s:s.payment_method in ['pdc','cdc','bank'])
    #     # pdf_cdc_payment_lines = self.payment_line_ids.filtered(lambda s:s.payment_method in ['pdc','cdc'])
    #     # cash_journal = self.from_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
    #     cash_journal = original_payment_transfer_id.from_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
    #     if not cash_journal:
    #         original_payment_transfer_id.message_post(body="Cash Journal is not configured in From Custodian", subtype_xmlid="mail.mt_comment", message_type="comment")
    #         self.message_post(body="Cash Journal is not configured in From Custodian of Original Payment transfer", subtype_xmlid="mail.mt_comment", message_type="comment")
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'type': 'warning',
    #                 'message': _("Please Configure Cash Journal in From Custodian"),
    #                 'next': {'type': 'ir.actions.act_window_close'},
    #             }
    #         }
    #     to_cash_journal = original_payment_transfer_id.to_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
    #     # to_cash_journal = self.to_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
    #     if not to_cash_journal:
    #         original_payment_transfer_id.message_post(body="Cash Journal is not configured in To Custodian", subtype_xmlid="mail.mt_comment", message_type="comment")
    #         self.message_post(body="Cash Journal is not configured in To Custodian of Original Payment transfer", subtype_xmlid="mail.mt_comment", message_type="comment")
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'type': 'warning',
    #                 'message': _("Please Configure Cash Journal in To Custodian"),
    #                 'next': {'type': 'ir.actions.act_window_close'},
    #             }
    #         }
    #     if not original_payment_transfer_id.to_custodian_id.journal_ids:
    #     # if not self.to_custodian_id.journal_ids:
    #         original_payment_transfer_id.message_post(body="Please Configure the Journal in TO Custodians", subtype_xmlid="mail.mt_comment", message_type="comment")
    #         self.message_post(body="Please Configure the Journal in TO Custodians of Original Payment transfer", subtype_xmlid="mail.mt_comment", message_type="comment")
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'type': 'warning',
    #                 'message': _("Please Configure the Journal in TO Custodians"),
    #                 'next': {'type': 'ir.actions.act_window_close'},
    #             }
    #         }
    #     # line_journal_types = self.payment_line_ids.mapped('journal_id').mapped('type')
    #     if len(set(original_payment_transfer_id.to_custodian_id.journal_ids.mapped('type'))) != len(set(original_payment_transfer_id.from_custodian_id.journal_ids.mapped('type'))):
    #         original_payment_transfer_id.message_post(body="Please Configure the Same Journal type in from and to custodian ", subtype_xmlid="mail.mt_comment",
    #                           message_type="comment")
    #         self.message_post(body="Please Configure the Same Journal type in from and to custodian of Original Payment transfer",
    #                           subtype_xmlid="mail.mt_comment",
    #                           message_type="comment")
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'type': 'warning',
    #                 'message': _("Please Configure the Same Journal type in from and to custodian"),
    #                 'next': {'type': 'ir.actions.act_window_close'},
    #             }
    #         }
    #     line_ids = []
    #     transfer_payments = self.env['account.payment']
    #     for line in cash_payment_lines:
    #     # for line in bank_cash_payment_lines:
    #     #     from_journal = self.from_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
    #         from_journal = original_payment_transfer_id.from_custodian_id.journal_ids.filtered(lambda s:s.type == 'cash')
    #         from_default_account_id = from_journal[0].default_account_id.id
    #         # to_journal = self.to_custodian_id.journal_ids.filtered(lambda s: s.type == 'cash')
    #         to_journal = original_payment_transfer_id.to_custodian_id.journal_ids.filtered(lambda s: s.type == 'cash')
    #         to_default_account_id = to_journal[0].default_account_id.id
    #         if original_payment_transfer_id.payment_type == 'send':
    #         # if self.payment_type == 'send':
    #             line_list = [
    #                 (0, 0,
    #                  {
    #                 "name": "Custodian {} of cash transfer".format(original_payment_transfer_id.to_custodian_id.name),
    #                 "account_id": to_default_account_id,
    #                 "currency_id": line.currency_id.id,
    #                 "debit": line.amount_transferred,
    #             }, ),
    #                 (0, 0,
    #                  {
    #                      "name": "Custodian {} of cash transfer".format(original_payment_transfer_id.from_custodian_id.name),
    #                      "account_id": from_default_account_id,
    #                      "currency_id": line.currency_id.id,
    #                      "credit": line.amount_transferred,
    #                  },)
    #             ]
    #         else:
    #             line_list = [
    #                 (0, 0,
    #                  {
    #                      "name": "Custodian {} of cash transfer".format(original_payment_transfer_id.from_custodian_id.name),
    #                      "account_id": from_default_account_id,
    #                      "currency_id": line.currency_id.id,
    #                      "debit": line.amount_transferred,
    #                  },),
    #                 (0,0,
    #                  {
    #                         "name": "Custodian {} of cash transfer".format(original_payment_transfer_id.to_custodian_id.name),
    #                         "account_id": to_default_account_id,
    #                         "currency_id": line.currency_id.id,
    #                         "credit": line.amount_transferred,
    #                     },)
    #             ]
    #         line_ids += line_list
    #         transfer_payments += line.payment_ids
    #     if line_ids:
    #         move_vals = {
    #             "date": fields.Date.today(),
    #             "invoice_date": fields.Date.today(),
    #             "move_type": "entry",
    #             'ref': 'Entry of Payment Transfer',
    #             "journal_id": cash_journal[0].id,
    #             "line_ids": line_ids,
    #             "payment_transfer_id": self.id
    #         }
    #         self.transfer_date = datetime.datetime.now()
    #         self.is_transferred = True
    #         move_id = self.env["account.move"].create(move_vals)
    #         move_id.action_post()
    #     if transfer_payments:
    #         transfer_payments.sudo().write({'is_transfer_created':True})
    #     pdc_cdc_payments = bank_pdc_cdc_payment_lines.mapped('payment_ids')
    #     # pdc_cdc_payments = pdf_cdc_payment_lines.mapped('payment_ids')
    #     pdc_cdc_payments.sudo().write({'responsible_id': original_payment_transfer_id.to_custodian_id.responsible_custodian.id})
    #     self.is_transferred = True

    def open_related_payment_transfer(self):
        action = {
            'name': _("Related Payment Transfer"),
            'type': 'ir.actions.act_window',
            'res_model': 'payments.transfer',
            'context': {'create': False, 'edit': True, 'delete': False},
            'view_mode': 'list,form',
            'domain': [('id', '=', self.related_payment_transfer_id.id)],
        }
        return action

    def open_transfer_jornal_entries(self):
        move = self.env['account.move'].sudo().search([('payment_transfer_id','=',self.id)])
        action = {
            'name': _("Payment Transfer Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': True, 'edit': True,'delete':True},
            'view_mode': 'list,form',
            'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
            'domain': [('id', 'in', move.ids)],
        }
        return action


class PaymentsTransferLine(models.Model):
    _name = 'payments.transfer.line'
    _description = 'Payment Transfer Line'

    transfer_id = fields.Many2one('payments.transfer', string="Transfer")
    payment_method = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('pdc', 'PDC'),
        ('cdc', 'CDC'),
    ], string="Payment Method", required=False)

    amount = fields.Monetary(string="Original Amount", readonly=False)
    currency_id = fields.Many2one('res.currency', string="Currency")
    journal_id = fields.Many2one('account.journal',string="Journal")

    amount_transferred = fields.Monetary(string="Amount Transferred")
    # responsible_user_id = fields.Many2one('res.users',string="Responsible")

    # transfer_date = fields.Datetime(string="Transfer Date", readonly=False)
    payment_ids = fields.Many2many('account.payment', string="Payments")
    # employee_id = fields.Many2one('hr.employee',related="responsible_user_id.employee_id",string="Employee Name")
    # employee_code = fields.Char(string="Employee Code")

    # @api.onchange('amount_transferred', 'amount')
    # def _check_amount_transferred(self):
    #     for rec in self:
    #         if rec.amount_transferred != rec.amount:
    #             raise ValidationError("Transferred amount must me same as amount.")

    def action_show_payment_info(self):
        return {
            'name': _('Show Payment Info'),
            'res_model': 'pdc.cdc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context' : {'default_payment_ids':self.payment_ids.ids}
        }
