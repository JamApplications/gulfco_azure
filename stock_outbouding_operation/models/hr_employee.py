from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeOutbouding(models.Model):
    _inherit = 'hr.employee'

    employee_limit = fields.Float(string='Employee Limit')

    @api.constrains('employee_limit')
    def _check_negative_employee_limit(self):
        for record in self:
            if record.employee_limit < 0:
                raise ValidationError("Employee Limit cannot be negative.")

class HrEmployeePublic(models.Model):
    _inherit ="hr.employee.public"
    employee_limit = fields.Float(readonly=True)