from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_invoice_journal = fields.Boolean(string="IS Invoice Journal")
    is_debit_note_journal = fields.Boolean(string="Is Debit Note Journal")