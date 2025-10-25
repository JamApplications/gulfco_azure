from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if self.env.context.get('_skip_discount_product_rename') and 'name' in vals:
            vals = dict(vals); vals.pop('name', None)   # skip the rename only
        return super().write(vals)