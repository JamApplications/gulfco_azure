from odoo import api, fields, models 

class MrpBomLineInh(models.Model):
    _inherit = 'mrp.bom.line'

    item_code = fields.Char(string="Gulfco Code", related='product_id.default_code')