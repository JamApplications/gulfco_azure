from odoo import models, fields, api, _

class StockRoute(models.Model):
    _inherit = 'stock.route'

    is_buy_route = fields.Boolean(string="Is Buy Route")
    is_manufacture_route = fields.Boolean(string="Is Manufacture Route")