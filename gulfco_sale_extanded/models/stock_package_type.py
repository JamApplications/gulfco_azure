
from odoo import models, fields

class StockPackageTypeInherited(models.Model):
    _inherit = "stock.package.type"
    
    is_each = fields.Boolean("Is Each", default=False, copy=False)