from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_accrued_journal = fields.Boolean(string="IS Accrued Journal")