from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class SaleOrderLineReward(models.Model):
    _name = 'sale.order.line.reward'
    
    name = fields.Char()
    sale_order_line_id = fields.Many2one('sale.order.line', required=True, ondelete='cascade')
    applied_reward_id = fields.Many2one(
        comodel_name='loyalty.reward', ondelete='restrict', readonly=True, required=True)
    applied_discount = fields.Float(
        string="Applied Discount (%)"
    )    
    applied_discount_value = fields.Float(
        string="Applied Discount"
    )
    discount_type = fields.Selection(
        selection=[
            ('percent', 'Percentage'),
            ('fixed', 'Fixed Amount')
        ],
        string="Discount Type",
        default='percent'
    )
    active = fields.Boolean(default=False)
    
    def unlink(self):
        for rec in self:
            rec.sale_order_line_id.test_discount = rec.sale_order_line_id.test_discount - rec.applied_discount
            rec.sale_order_line_id.test_discount_value = rec.sale_order_line_id.test_discount_value - rec.applied_discount_value
        return super().unlink()
    

        
        
    