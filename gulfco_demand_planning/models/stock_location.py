from odoo import fields, models, api, _
from odoo.exceptions import UserError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_saleable_location = fields.Boolean(string="Is Saleable Location",copy=False)