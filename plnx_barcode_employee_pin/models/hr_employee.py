# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid

from datetime import datetime, time, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo import fields, models, _, api

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = "hr.employee"


    def get_direct_employees_pin_validated(self, employee_id=None, res_id=None, res_model=None):
        employee = self.search([('id', '=', employee_id)], limit=1)
        if employee:
            picking = self.env[res_model].search([('id', '=', res_id)])
            picking.employee_ids = [(4, employee.id)]
            vals = {
                'employee_id': employee.id,
                'access_date': datetime.today(),
                }
            if res_model == 'mrp.production':
                picking.mrp_employee_ids = [(4, employee.id)]
                vals['mrp_id'] = picking.id
                picking.employee_history_mrp_line.create(vals)
            else:
                vals['picking_id'] = picking.id
                picking.employee_history_line.create(vals)
            return employee
        else:
            raise ValidationError('Employee for this PIN does not exist.')




    barcode_pin = fields.Char(string='Barcode PIN')

    _sql_constraints = [
        ('barcode_pin_uniq', 'unique (barcode_pin)', "Barcode PIN already exists. \nBarcode PIN must be Unique."),
    ]

    def get_employees_barcode_stock_quant_pin_validated(self, access_pin=None, res_id=None, res_model=None):
        employee = self.search([('barcode_pin', '=', access_pin)], limit=1)
        if employee:
            if res_model == 'stock.quant':
                stock_quant = self.env[res_model].browse(res_id)

                for quant in stock_quant:
                    quant.employee_ids = [(4, employee.id)]
                # # vals = {
                # #     'employee_id': employee.id,
                # #     'access_date': datetime.today(),
                # #     'batch_id': picking.id
                # # }
                # # picking.employee_history_line.create(vals)
                return employee
            else:
                # picking = self.env[res_model].search([('id', '=', res_id)])
                # picking.employee_ids = [(4, employee.id)]
                # vals = {
                #     'employee_id': employee.id,
                #     'access_date': datetime.today(),
                #     'batch_id': picking.id
                # }
                # picking.employee_history_line.create(vals)
                pass
        else:
            raise ValidationError('Employee for this PIN does not exist.')



    def get_employees_barcode_batch_picking_pin_validated(self, access_pin=None, res_id=None, res_model=None):
        employee = self.search([('barcode_pin', '=', access_pin)], limit=1)

        if employee:
            picking = self.env[res_model].search([('id', '=', res_id)])
            picking.employee_ids = [(4, employee.id)]
            vals = {
                'employee_id': employee.id,
                'access_date': datetime.today(),
                'batch_id': picking.id
                }
            picking.employee_history_line.create(vals)
            return employee
        else:
            raise ValidationError('Employee for this PIN does not exist.')


    def _employees_pin_validated(self, access_pin=None, res_id=None, res_model=None):
        employee = self.search([('barcode_pin', '=', access_pin)], limit=1)
        if not employee:
            raise ValidationError('Employee for this PIN does not exist.')

        return employee.id

    def get_employees_pin_validated(self, access_pin=None, res_id=None, res_model=None):
        employee = self.search([('barcode_pin', '=', access_pin)], limit=1)

        if employee:
            picking = self.env[res_model].search([('id', '=', res_id)])
            picking.employee_ids = [(4, employee.id)]
            vals = {
                'employee_id': employee.id,
                'access_date': datetime.today(),
                }
            if res_model == 'mrp.production':
                picking.mrp_employee_ids = [(4, employee.id)]
                vals['mrp_id'] = picking.id
                picking.employee_history_mrp_line.create(vals)
            else:
                vals['picking_id'] = picking.id
                picking.employee_history_line.create(vals)
            return employee
        else:
            raise ValidationError('Employee for this PIN does not exist.')


class HrEmployeePublic(models.Model):
    _inherit ="hr.employee.public"
    barcode_pin = fields.Char(readonly=True)