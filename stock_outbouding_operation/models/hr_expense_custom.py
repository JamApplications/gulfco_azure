from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    # vendor_trn = fields.Char(related='vendor_id.vat_trn', string="TRN", store=False, readonly=True)
    vendor_trn = fields.Char(string='TRN')
    invoice_no = fields.Char(string="Invoice No")
    vendor = fields.Char(string="Vendor")
    invoice_date = fields.Date(string="Invoice Date")
    responsible_id = fields.Many2one('res.users',string="Responsible",related="employee_id.user_id",store=True)
    responsible_employee_id =fields.Many2one('hr.employee',string="Responsible Employee")

    def _get_default_expense_sheet_values(self):
        result = super()._get_default_expense_sheet_values()
        for sheet_vals in result:
            if 'expense_line_ids' in sheet_vals and sheet_vals.get('expense_line_ids') and len(sheet_vals.get('expense_line_ids')) > 0 and len(sheet_vals.get('expense_line_ids')[0]) > 2:
                expense = self.filtered(lambda e: e.id in sheet_vals.get('expense_line_ids')[0][2])
                if expense and expense[0].responsible_employee_id:
                    sheet_vals['responsible_employee_id'] = expense[0].responsible_employee_id.id
        return result

    @api.constrains("date")
    def _check_payment_date_future_date(self):
        for record in self:
            if record.date and record.date != date.today():
                raise UserError('Expense date should be today date.')

    @api.constrains('vendor','invoice_no')
    def _check_duplicate_expense_invoice(self):
        for expense in self:
            if not expense.vendor or not expense.invoice_no:
                continue
            domain = [
                ('id', '!=', expense.id),
                ('vendor','=',expense.vendor),
                ('invoice_no', '=', expense.invoice_no),
                ('state', '!=', 'refused'),
            ]

            if self.search_count(domain):
                raise UserError(
                    _("Invoice Number '%s' and Vendor '%s' is already in another Expense.")
                    % (expense.invoice_no, expense.vendor)
                )

#     def _get_default_expense_sheet_values(self):
#         res =  super()._get_default_expense_sheet_values()
#         raise UserError(str(res[0].expense_line_ids))

# [{'company_id': 1, 'employee_id': 1, 'name': '[COMM] Communication', 'expense_line_ids': [(<Command.SET: 6>, 0, [8])], 'state': 'draft'}]