from odoo import models, fields

class StockTakeoverReason(models.Model):
    _name = 'stock.takeover.reason'
    _description = 'Reason of Stock Takeover'

    name = fields.Char(required=True, string="Reason")