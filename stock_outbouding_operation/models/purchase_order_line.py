from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        res = super()._prepare_stock_moves(picking)
        for re in res:
            re['product_packaging_qty'] = self.product_packaging_qty
        return res
