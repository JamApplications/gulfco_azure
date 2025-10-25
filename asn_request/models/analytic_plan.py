from odoo import models,fields


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    is_channel_plan = fields.Boolean(string="Is Channel Plan")