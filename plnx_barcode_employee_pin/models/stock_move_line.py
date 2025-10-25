from odoo import _, api, fields, models

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    def _get_fields_stock_barcode(self):
        res = super()._get_fields_stock_barcode()
        res.append('origin')
        res.append('product_packaging_qty')
        return res
