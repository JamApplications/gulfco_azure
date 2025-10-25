# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class CommissionPlanTarget(models.Model):
    _inherit = 'sale.commission.plan.target'

    kpi_type = fields.Selection(related='plan_id.kpi_type', store=True)
    amount_percentage = fields.Monetary("Target(%)", default=0, required=True, currency_field='currency_id')
    target_plan = fields.Integer("Target Plan", default=0, required=True)
