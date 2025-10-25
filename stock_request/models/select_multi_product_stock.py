from odoo import api, fields, models

class ProductSelection(models.Model):
    _inherit = 'product.product'

    quantity_stock = fields.Float(string="Quantity")

class StockMultiProductSelection(models.TransientModel):
    _name = 'stock.multi.product.selection'

    product_ids = fields.Many2many('product.product', string="Products")

    def add_products(self):
        for line in self.product_ids:
            order_id = self.env.context.get("active_id")
            order_req = self.env["stock.request.order"].browse(order_id)
            stock_req_line = self.env['stock.request'].create({
                'product_id': line.id,
                'order_id': order_req.id or self._context.get('active_id'),
                'product_uom_qty': line.quantity_stock or 1,
                'product_uom_id': line.uom_po_id.id or line.uom_id.id
            })
            # stock_req_line.onchange_source_location()