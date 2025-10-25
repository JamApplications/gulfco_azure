from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partners'

    accrued_account_id = fields.Many2one('account.account', string="Accrued Account")



