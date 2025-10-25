from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    api_time = fields.Char("Api Time",tracking=True,default="Api Time")