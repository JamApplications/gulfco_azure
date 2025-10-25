# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date


class Company(models.Model):
    _inherit = "res.company"

    demand_planning_period = fields.Selection([
        ('year', 'Yearly'),
        ('month', 'Monthly'),
        ('week', 'Weekly'),
        ('day', 'Daily')], string="Demand Planning Period",
        default='month', required=True,
        help="Default value for the time ranges in Demand Planning report.")
    demand_planning_period_to_display_year = fields.Integer(
        'Number of columns for the yearly period to display in Demand Planning', default=3)
    demand_planning_period_to_display_month = fields.Integer(
        'Number of columns for the monthly period to display in Demand Planning', default=12)
    demand_planning_period_to_display_week = fields.Integer(
        'Number of columns for the weekly period to display in Demand Planning', default=12)
    demand_planning_period_to_display_day = fields.Integer(
        'Number of columns for the daily period to display in Demand Planning', default=30)
    previous_column_number = fields.Integer(default=3)