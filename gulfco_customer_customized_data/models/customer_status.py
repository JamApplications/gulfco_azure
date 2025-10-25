from odoo import models, fields, api, _

class CustomerStatus(models.Model):
    _name = 'customer.status'
    _description = 'Customer Status'

    name = fields.Char(required=True)