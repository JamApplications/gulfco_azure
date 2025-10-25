
from odoo import models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id')
    def _compute_tax_totals(self):
        super(PurchaseOrder,self)._compute_tax_totals()
        for order in self:
            order.tax_totals['total_discount_amount'] = str(sum(order.order_line.mapped('discount_amount'))) + str(order.currency_id.symbol)
