# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from lxml import etree
from odoo.exceptions import UserError, ValidationError 
 
class SaleOrder(models.Model):
    _inherit = 'sale.order'
     
    def write(self, vals):
        res = super().write(vals)
        if vals.get('show_update_fpos', False) == True and 'assign_to' in vals:
            self.action_update_taxes()           
        return res