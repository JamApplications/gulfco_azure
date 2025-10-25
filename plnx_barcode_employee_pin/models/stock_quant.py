from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta,date



class StockQuant(models.Model):
    _inherit = 'stock.quant'

    employee_ids = fields.Many2many('hr.employee', 'quant_employee_rel')

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when he want to edit a quant in `inventory_mode`.
        """
        res = super()._get_inventory_fields_write()
        res += ['employee_ids']
        return res
