from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CommissionKpi(models.Model):
    _name = "commission.kpi"
    _description = "Commission KPI"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'name'

    name = fields.Char( required=True)
    kpi_type = fields.Selection([('sale_target', 'Sale target'),
                                 ('collection', 'Collection'),
                                 ('msl_availability', 'MSL Availability'),
                                 ('market_execution', 'Market Execution'),
                                 ('journal_plan', 'Journal Plan'),], required=True)
