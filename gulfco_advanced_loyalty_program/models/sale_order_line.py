# in your custom module (e.g., gulfco_sale_extanded/models/sale_order_line.py)
from odoo import models, api
import random

def _gen_reward_code(order_id=None):
    base = str(random.getrandbits(32))
    return f"cust-{order_id or '0'}-{base}"

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def create(self, vals):
        if vals.get('reward_id') and not vals.get('reward_identifier_code'):
            vals['reward_identifier_code'] = _gen_reward_code(vals.get('order_id'))
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.reward_id and not line.reward_identifier_code:
                line.reward_identifier_code = _gen_reward_code(line.order_id.id)
        return res