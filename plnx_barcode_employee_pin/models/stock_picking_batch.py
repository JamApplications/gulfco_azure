# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta, date


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    employee_ids = fields.Many2many('hr.employee', 'picking_batch_employee_rel')
    employee_history_line = fields.One2many('stock.picking.batch.employee.history', 'batch_id')

    def action_add_pickings_and_confirm(self, vals):
        self.ensure_one()
        if vals['picking_ids']:
            # picking = self.env['stock.picking'].browse(vals['picking_ids'])
            for picking in self.env['stock.picking'].browse(vals['picking_ids']):
                picking.employee_ids = [(4, emp.id) for emp in self.employee_ids]
                picking.write({'employee_history_line': [(0, 0,
                                                          {'employee_id': emp.employee_id.id,
                                                           'access_date': emp.access_date,
                                                           'picking_id': picking.id})
                                                         for emp in self.employee_history_line]
                               })
        self.write(vals)
        self.action_confirm()
        return self._get_stock_barcode_data()


class StockPickingBatchEmployeeHistory(models.Model):
    _name = "stock.picking.batch.employee.history"
    _description = "Stock Picking Batch Employee History"

    employee_id = fields.Many2one('hr.employee', required=True)
    access_date = fields.Datetime('Access Date', default=datetime.now())

    batch_id = fields.Many2one('stock.picking.batch')

    def _get_fields_stock_barcode(self):
        return [
            'employee_id',
            'access_date',
            'batch_id',
        ]
