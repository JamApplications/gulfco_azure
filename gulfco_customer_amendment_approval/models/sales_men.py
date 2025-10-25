from odoo import models, fields, api, _


class SalesMen(models.Model):
    _inherit = 'sales.men'

    cust_amendment_id = fields.Many2one('customer.amendment', string="Customer Amendment")
