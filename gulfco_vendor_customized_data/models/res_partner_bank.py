from odoo import api, fields, models, _
from odoo.api import ValuesType, Self


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_name = fields.Char(string="Account Name")
    iban_number = fields.Char(string="IBAN")
    swift_number = fields.Char(string="SWIFT Code")
    branch_name = fields.Char(string="Bank Branch Name")
    branch_code = fields.Integer(string="Branch Code")
    sort_code = fields.Integer(string="Sort Code")
    contact_type = fields.Selection(related="partner_id.contact_type")
