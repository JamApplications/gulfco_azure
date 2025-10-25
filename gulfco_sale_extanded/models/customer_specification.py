from odoo import models, fields

class CustomerSpecification(models.Model):
    _name = 'customer.specification'
    _description = 'Customer Specification'

    name = fields.Char(string="Name", required=True)