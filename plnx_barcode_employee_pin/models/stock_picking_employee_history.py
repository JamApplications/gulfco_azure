from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta,date



class StockPickingEmployeeHistory(models.Model):
    _name = "stock.picking.employee.history"
    _description = "Stock Picking Employee History"

    employee_id = fields.Many2one('hr.employee', required=True)
    access_date = fields.Datetime('Access Date', default=datetime.now())

    picking_id = fields.Many2one('stock.picking')

    def _get_fields_stock_barcode(self):
        return [
            'employee_id',
            'access_date',
            'picking_id',
        ]
