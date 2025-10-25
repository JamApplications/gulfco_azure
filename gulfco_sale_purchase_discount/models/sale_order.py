
from odoo import models, api, fields

class SaleOrder(models.Model):
    _inherit = "sale.order"

    discount_amount_total = fields.Monetary(string='Total Discount Amount',
                                            compute='_compute_discount_totals',
                                            store=True,
                                            currency_field='currency_id')

    @api.depends('order_line.price_subtotal')
    def _compute_discount_totals(self):
        for order in self:
            order.discount_amount_total = sum(order.order_line.mapped('discount_amount'))

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_tax_totals(self):
        super(SaleOrder,self)._compute_tax_totals()
        for order in self:
            order.tax_totals['total_discount_amount'] = str(sum(order.order_line.mapped('discount_amount'))) + str(order.currency_id.symbol)

            exercise_price = 0
            for line in order.order_line:
                if line.exercise_price:
                    exercise_price += line.exercise_price * line.qty_delivered

            order.tax_totals['total_excise_amount'] = str(exercise_price) + str(order.currency_id.symbol)
            # order.tax_totals['total_excise_amount'] = str(sum(order.order_line.mapped('exercise_price'))) + str(order.currency_id.symbol)  #use for backup if need only sum

            # for inv in order.invoice_ids:
            #     pass
            # order.tax_totals['payment_received'] = str(exercise_price) + str(order.currency_id.symbol)
            # order.tax_totals['amount_due'] = str(exercise_price) + str(order.currency_id.symbol)
