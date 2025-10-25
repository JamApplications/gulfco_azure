# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    @api.constrains('discount_type', 'discount_percentage')
    def _check_discount_amount(self):
        for wizard in self:
            if (
                wizard.discount_type in ('sol_discount', 'so_discount')
                and wizard.discount_percentage > 1.0
            ):
                raise ValidationError(_("Invalid discount amount"))
            elif wizard.discount_type == 'amount' and wizard.discount_amount > wizard.sale_order_id.amount_total:
                raise ValidationError(_("Discount Amount is More than Sale Order Amount"))

    def action_apply_discount(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        if self.discount_type == 'sol_discount':
            self.sale_order_id.order_line.filtered(lambda s:not s.reward_id).write({'discount': self.discount_percentage*100})
        else:
            self._create_discount_lines()