from odoo import _, api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    excise_journal_id = fields.Many2one('account.journal',string="Excise Journal")
    excise_debit_account_id = fields.Many2one('account.account',string="Excise Debit Account",check_company=True,)
    excise_credit_account_id = fields.Many2one('account.account',string="Excise Credit Account",check_company=True,)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    excise_journal_id = fields.Many2one('account.journal',related="company_id.excise_journal_id",string="Excise Journal",readonly=False)
    excise_debit_account_id = fields.Many2one('account.account',related="company_id.excise_debit_account_id",string="Excise Debit Account",readonly=False,check_company=True)
    excise_credit_account_id = fields.Many2one('account.account',related="company_id.excise_credit_account_id",string="Excise Credit Account",readonly=False,check_company=True)