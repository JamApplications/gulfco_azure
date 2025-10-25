from odoo import models, fields,api

class AccountTaxInh(models.Model):
    _inherit = 'account.tax'

    # @api.model
    # def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
    #     res = super(AccountTaxInh, self)._get_tax_totals_summary(base_lines, currency, company, cash_rounding)
    #     if self.env.context.get('custom_sale_id'):
    #         sale_order = self.env['sale.order'].sudo().browse([self.env.context.get('custom_sale_id')])
    #         if sale_order and sale_order.reward_discount_amount:
    #             amount = sum(sale_order.order_line.mapped('price_subtotal'))
    #             total_amount = sum(sale_order.order_line.mapped('price_total'))
    #             for so_line in res.get('subtotals'):
    #                 for tax_line in so_line.get('tax_groups'):
    #                     base_amount_currency = tax_line.get('base_amount_currency')
    #                     tax_line.update({
    #                         'base_amount_currency': base_amount_currency - sale_order.reward_discount_amount,
    #                     })
    #                 so_line.update({
    #                     'base_amount': amount - sale_order.reward_discount_amount,
    #                     'base_amount_currency': amount - sale_order.reward_discount_amount,
    #                 })
    #             res.update({
    #                 'total_amount_currency': total_amount - sale_order.reward_discount_amount,
    #                 'total_amount': total_amount - sale_order.reward_discount_amount,
    #             })
    #     return res