from odoo import models, fields, api, _
from  datetime import datetime

class CustomerGroup(models.Model):
    _name = 'customer.group'
    _description = 'Customer Group'

    name = fields.Char(string="Name")