from odoo import models, fields, api


class ServicesLines(models.Model):
    _name = "services.lines"
    _description = "Services Lines"

    product_id = fields.Many2one('product.product')
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', readonly=True)
    picking_id = fields.Many2one('stock.picking') ## Revert One2Many
    po_line_id = fields.Many2one('purchase.order.line')
    product_qty = fields.Float(digits=(12, 2))
    price_unit = fields.Float()
    product_uom_qty = fields.Float(
        'Demand',
        readonly=True,
        digits='Product Unit of Measure',
        help="This is the quantity of product that is planned to be moved."
             "Lowering this quantity does not generate a backorder."
             "Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    price_subtotal = fields.Monetary(currency_field='currency_id')
    analytic_distribution = fields.Json("Analytic Distribution", copy=True)