from odoo import models, fields, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    discount_amount = fields.Monetary(string='Total',)
    # discount_amount = fields.Monetary(compute='_compute_discount_amount', string='Total', store=True, precompute=True,)

    # @api.depends('price_unit','discount','quantity')
    # def _compute_discount_amount(self):
    #     for line in self:
    #         if line.discount_amount:
    #             continue
    #         if not line.sale_line_ids.mapped('reward_id'):
    #             if line.discount_unit_price:
    #                 line.discount_amount = ((line.price_unit - line.discount_unit_price) * line.quantity)
    #             else:
    #                 line.discount_amount = (line.price_unit * line.discount * line.quantity)/100
    #
    #         # line.discount_amount = (line.price_unit * line.discount * line.quantity)/100