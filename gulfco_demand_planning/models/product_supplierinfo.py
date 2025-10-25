from odoo import api, fields, models, _

class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    source_of_good_country_ids = fields.Many2many('res.country',string="Source of Goods")
    supplier_mos = fields.Integer(string="MOS")
