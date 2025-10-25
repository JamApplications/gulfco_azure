from odoo import models,fields


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    is_channel_common = fields.Boolean(string="Is Channel common")