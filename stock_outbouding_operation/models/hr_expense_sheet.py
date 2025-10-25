from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrExpenseSheetOutbouding(models.Model):
    _inherit = 'hr.expense.sheet'

    state = fields.Selection(selection_add=[
        ('financial_approval', 'Financial Approval'),
        ('director_approval','Director Approval'),
    ], ondelete={'financial_approval': 'cascade','director_approval':'cascade'})
    responsible_id = fields.Many2one('res.users',string="Responsible",related="employee_id.user_id",store=True)
    responsible_employee_id =fields.Many2one('hr.employee',string="Responsible Employee")

    def action_director_approval(self):
        self.state = 'director_approval'

    def financial_approve(self):
        self.ensure_one()
        employee = self.employee_id
        employee_limit = employee.employee_limit
        unposted_expenses = self.env['hr.expense'].search([
            ('employee_id', '=', employee.id),
            ('state', '!=', 'post'),
        ])
        total_unposted = sum(unposted_expenses.mapped('total_amount_currency'))
        self.state = 'financial_approval'
        if total_unposted > employee_limit:
            difference = total_unposted - employee_limit
            notification = f"This employee (employee ({employee.name}) is exceed his limitation of employee limit with different of total {difference:.2f})."
            self.message_post(
                body=notification, message_type="notification", subtype_xmlid="mail.mt_comment"
            )
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _(f"This employee ({employee.name}) exceeds their limit of {employee_limit:.2f} "
                    f"by {difference:.2f} in unposted expenses."),
                               'type': 'warning',
                   'sticky': False,
                   'next': {'type': 'ir.actions.act_window_close'},},}
