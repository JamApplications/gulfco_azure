from odoo import fields, models, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def write(self, vals):
        if self.env.context.get('_skip_discount_product_rename') and 'name' in vals:
            vals = dict(vals); vals.pop('name', None)
        return super().write(vals)