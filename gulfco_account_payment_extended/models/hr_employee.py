from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_code = fields.Char(string="Employee Code")

class HrEmployeePublic(models.Model):
    _inherit ="hr.employee.public"
    employee_code = fields.Char(readonly=True)