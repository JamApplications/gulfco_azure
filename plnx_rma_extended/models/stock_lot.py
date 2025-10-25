from odoo import fields, models, api


class StockLot(models.Model):
    _inherit = 'stock.lot'
    _description = 'Is salable lot'

    is_salable = fields.Boolean(default=True)
