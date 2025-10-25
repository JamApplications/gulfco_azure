from odoo import models, fields, api, _

class CustomerClass(models.Model):
    _name = 'customer.class'
    _description = 'Customer Class'

    name = fields.Char(required=True)