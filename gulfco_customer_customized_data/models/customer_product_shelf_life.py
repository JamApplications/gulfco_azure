from odoo import models, fields, api, _
from  datetime import datetime

class CustomerProductShelfLife(models.Model):
    _name = 'customer.product.shelf.life'
    _description = 'Customer Product Shelf Life'

    product_category = fields.Many2one('product.category', string="Product Category")
    product_id = fields.Many2one('product.product', string="Product")
    shelf_life = fields.Integer(string='Shelf Life')
    partner_id = fields.Many2one('res.partner', string="Partner")
    division = fields.Selection([('food', 'Food'),
                                            ('non_food', 'Non-Food'),
                                            ('mars', 'MARS')
                                        ], string='Division')
    percentage = fields.Float(string="Percentage")
    country_of_origin_ids = fields.Many2many('res.country')
    production_year = fields.Selection(
        selection=[(str(y), str(y)) for y in range(2000, 2100)],
        string="Production Year",
        default=lambda self: str(datetime.today().year)
    )


