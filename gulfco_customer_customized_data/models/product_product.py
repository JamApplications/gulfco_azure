from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self._context.get('custom_product_category'):
            domain = domain.copy()
            domain.append((('categ_id', 'child_of', self._context.get('custom_product_category'))))
        return super()._search(domain, offset, limit, order)