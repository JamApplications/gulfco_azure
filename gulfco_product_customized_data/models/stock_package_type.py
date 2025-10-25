from odoo import models, fields, api


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    type = fields.Selection([('box', 'Box'),
                             ('ctn', 'CTN'),
                             ('plt', 'PLT')
                             ], string="Type")
    is_pallete_package = fields.Boolean(string="Is Pallete Package")
