from odoo import _, api, models, fields


class StockLocation(models.Model):
    _inherit = "stock.location"

    location_group = fields.Selection([('wh', 'WH'), ('van', 'VAN')], string="Location Group")
