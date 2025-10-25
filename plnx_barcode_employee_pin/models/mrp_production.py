# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools import file_open


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    mrp_employee_ids = fields.Many2many('hr.employee', 'mrp_production_employee_rel', string='Employee')
    employee_history_mrp_line = fields.One2many('mrp.employee.history', 'mrp_id')




class MrpEmployeeHistory(models.Model):
    _name = "mrp.employee.history"
    _description = "Manufacturing Employee History"

    employee_id = fields.Many2one('hr.employee', required=True)
    access_date = fields.Datetime('Access Date', default=datetime.now())

    mrp_id = fields.Many2one('mrp.production')

    def _get_fields_stock_barcode(self):
        return [
            'employee_id',
            'access_date',
            'mrp_id',
        ]


