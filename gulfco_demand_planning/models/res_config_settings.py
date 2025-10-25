from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    demand_planning_period = fields.Selection(related="company_id.demand_planning_period", string="Demand Planning Period", readonly=False)
    demand_planning_period_to_display_year = fields.Integer(
        related='company_id.demand_planning_period_to_display_year',
        string='Number of Yearly Demand Planning Period Columns', readonly=False)
    demand_planning_period_to_display_month = fields.Integer(
        related='company_id.demand_planning_period_to_display_month',
        string='Number of Monthly Demand Planning Period Columns', readonly=False)
    demand_planning_period_to_display_week = fields.Integer(
        related='company_id.demand_planning_period_to_display_week',readonly=False,string="Number of Week Days Demand Planning Columns")
    demand_planning_period_to_display_day = fields.Integer(
        related='company_id.demand_planning_period_to_display_day',readonly=False,string="Number of Days Demand Planning Columns")
    previous_column_number = fields.Integer(related='company_id.previous_column_number',readonly=False,string="Previous Column Number")