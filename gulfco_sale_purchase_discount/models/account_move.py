
from odoo import models, api

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        super(AccountMove,self)._compute_tax_totals()
        for move in self:
            if isinstance(move.tax_totals,dict):
                before_discount_amount = (
                        sum(l.price_subtotal for l in move.invoice_line_ids if (l.price_subtotal or 0) > 0)
                        + sum(l.discount_amount for l in move.invoice_line_ids if (l.discount_amount or 0) > 0)
                )

                # before_discount_amount = sum(
                #     move.invoice_line_ids.mapped('price_subtotal')) + sum(move.invoice_line_ids.mapped('discount_amount'))
                move.tax_totals['before_discount_amount'] = str(before_discount_amount) + str(move.currency_id.symbol)
                # total_discount_amount = (
                #         sum(l.price_subtotal for l in move.invoice_line_ids if (l.price_subtotal or 0) < 0)
                #         + sum(l.discount_amount for l in move.invoice_line_ids if (l.discount_amount or 0) < 0)
                # )
                total_discount_amount = sum(move.invoice_line_ids.mapped('discount_amount'))

                move.tax_totals['total_discount_amount'] = str(total_discount_amount) + str(move.currency_id.symbol)


                move.tax_totals['payment_received'] = str(move.amount_total - move.amount_residual) + str(move.currency_id.symbol)
                move.tax_totals['due_amount'] = str(move.amount_residual) + str(move.currency_id.symbol)
