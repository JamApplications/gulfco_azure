from odoo import _, api, fields, models


class StockLocationTag(models.Model):
    _inherit = "stock.location.tag"

    is_outbound = fields.Boolean(string="Is Outbound")
    is_inbound = fields.Boolean(string="Is Inbound")
    is_saleable = fields.Boolean(string="Is Saleable")
    is_not_saleable = fields.Boolean(string="Is Not Saleable")

