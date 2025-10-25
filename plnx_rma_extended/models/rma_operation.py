# -*- coding: utf-8 -*-

from odoo import models, fields, api,Command,_

class RmaOperation(models.Model):
    _inherit = "rma.operation"

    operation_type = fields.Selection([('return','Return'),('replace','Replace'),('refund','Refund')])