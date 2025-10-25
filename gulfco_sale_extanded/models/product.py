from odoo import api, fields, models 
from odoo.osv import expression
import re


class ProductTmpCust(models.Model):
    _inherit = 'product.template'

    customer_article_ids = fields.One2many(
        comodel_name='customer.article',
        inverse_name='product_tmpl_id',
        string='Customer_article'
    )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not name:
            return super(ProductTmpCust, self).name_search(name, args, operator, limit)
        else:
            res = super(ProductTmpCust, self).name_search(name, args, operator, limit)
            customer_article = self.env['customer.article'].sudo().search([('name', 'ilike', name)])
            if customer_article and customer_article.product_tmpl_id and self.env.context.get('is_article'):
                products = self.search_fetch(
                    expression.AND([[], [('id', 'in', customer_article.product_tmpl_id.ids)]]),
                    ['display_name'], limit=limit)
                return res + [(product.id, product.display_name) for product in products.sudo()]
            else:
                return res



class ProductPCust(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not name:
            return super(ProductPCust, self).name_search(name, args, operator, limit)
        else:
            res = super(ProductPCust, self).name_search(name, args, operator, limit)
            customer_article = self.env['customer.article'].sudo().search([('name', 'ilike', name)])
            if customer_article and customer_article.product_tmpl_id and self.env.context.get('is_article'):
                products = self.search_fetch(expression.AND([[],[('product_tmpl_id', 'in', customer_article.product_tmpl_id.ids)]]), ['display_name'], limit=limit)
                return res + [(product.id, product.display_name) for product in products.sudo()]
            else:
                return res


