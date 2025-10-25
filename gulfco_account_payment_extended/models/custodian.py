from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
from odoo.tools.populate import fetch_last_id


class Custodian(models.Model):
    _name = 'custodian'
    _description = 'Custodian'

    custodian_code = fields.Char(string="Custodian Code")
    name = fields.Char(string="Custodian Name")
    responsible_custodian = fields.Many2one('res.partner', string="Responsible Custodian")
    journal_ids = fields.Many2many('account.journal',string="Journals",domain="[('type', 'in', ['bank', 'cash'])]")
    restriction_custodian_ids = fields.Many2many('custodian','custodian_restriction_rel','restriction_custodian_id','custodian_id',string="Restriction Custodian")
    custodian_branch_id = fields.Many2one('custodian.branch',string="Branch")
    custodian_user_job_id = fields.Many2one('custodian.user.jobs',string="User Job")
    employee_code = fields.Char(string="Employee Code")
    # line_ids = fields.One2many('custodian.line','custodian_id',string="Lines")
    # dest_journal_id = fields.Many2one('account.journal',string="Destination Journal",domain="[('type', 'in', ['bank', 'cash'])]")
    inbound_payment_method_line_ids = fields.Many2many('account.payment.method.line',string="Incoming Payment Methods")


    @api.onchange('employee_code')
    def onchange_employee_code(self):
        if self.employee_code:
            employee = self.env['hr.employee'].search([('employee_code','=',self.employee_code)],limit=1)
            if employee and employee.work_contact_id:
                self.responsible_custodian = employee.work_contact_id.id

    @api.constrains('custodian_code')
    def _check_unique_custodian_code(self):
        for record in self:
            if self.search_count([('custodian_code', '=', record.custodian_code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(_('Custodian Code must be unique.'))

    def action_custodian_report(self):
        action = {
            'name': _('Custodian Report'),
            'view_mode': 'list',
            'type': 'ir.actions.act_window',
            'res_model': 'custodian.payment.report',
            'domain': [('custodian_id', 'in', self.ids)],
            'context': {'show_custodian_report':1}
        }
        return action

class CustodianLine(models.Model):
    _name = 'custodian.line'
    _description = 'Custodian Line'

    journal_id = fields.Many2one('account.journal',string="Journal")
    responsible_custodian = fields.Many2one('res.partner',string="Responsible Custodian")
    custodian_id = fields.Many2one('custodian',string="Custodian")

class CustodianBranch(models.Model):
    _name = 'custodian.branch'
    _description = 'Custodian Branch'

    name = fields.Char(string="Name")


class CustodianUserJobs(models.Model):
    _name = 'custodian.user.jobs'
    _description = 'Custodian User Jobs'

    name = fields.Char(string="Name")