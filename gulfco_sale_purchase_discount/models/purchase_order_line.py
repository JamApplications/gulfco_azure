from odoo import models, fields, api, _

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    discount_amount = fields.Monetary(compute='_compute_discount_amount', string='Total', store=True)

    @api.depends('price_unit','discount','product_qty')
    def _compute_discount_amount(self):
        for line in self:
            line.discount_amount = (line.price_unit * line.discount * line.product_qty)/100