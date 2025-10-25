
from odoo import fields, models, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []

        if name and '|' in name:
            # Split the name into lot_name and product_code
            lot_name, product_code = [x.strip() for x in name.split('|', 1)]

            # Find the product by code
            product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
            if product:
                args += [('product_id', '=', product.id)]

            # Search lot by name + product
            lot_records = self.search([('name', '=', lot_name)] + args, limit=limit)
            return [(lot.id, lot.name) for lot in lot_records]

        # fallback to normal search if format not matched
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

