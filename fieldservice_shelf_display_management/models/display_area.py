
from odoo import models, fields, api

class DisplayArea(models.Model):
    _name = 'display.area'
    _description = 'Display Area'

    name = fields.Char(string='Name', required=True)