from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    division_code = fields.Char(string="Division Code")