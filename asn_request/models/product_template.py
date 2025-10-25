
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        accounts = super(ProductTemplate, self).get_product_accounts(fiscal_pos=fiscal_pos)
        if self.env.context.get('from_price_diff_move'):
            accounts.update({'stock_valuation': self.categ_id.property_account_creditor_price_difference_categ or False})
        return accounts

