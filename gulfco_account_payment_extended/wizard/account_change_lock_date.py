from odoo import fields, models,api,_
from datetime import date, timedelta
from odoo.exceptions import UserError


class AccountChangeLockDate(models.TransientModel):
    """
    This wizard is used to change the lock date
    """
    _inherit = 'account.change.lock.date'

    def change_lock_date(self):
        self.ensure_one()
        if self.env.user.has_group('account.group_account_manager'):
            exception_vals_list = self._prepare_exception_values()
            changed_lock_date_values = self._prepare_lock_date_values(exception_vals_list=exception_vals_list)

            if exception_vals_list:
                self.env['account.lock_exception'].create(exception_vals_list)

            res = self._change_lock_date(changed_lock_date_values)
            if res and isinstance(res,dict):
                return res
        else:
            raise UserError(_('Only Billing Administrators are allowed to change lock dates!'))
        return {'type': 'ir.actions.act_window_close'}

    def _change_lock_date(self, lock_date_values=None):
        self.ensure_one()
        if lock_date_values is None:
            lock_date_values = self._prepare_lock_date_values()

        # Possibly create default report external values for tax
        tax_lock_date = lock_date_values.get('tax_lock_date', None)
        if tax_lock_date and tax_lock_date != self.env.company['tax_lock_date']:
            self._create_default_report_external_values('tax_lock_date')

        # Possibly create default report external values for fiscal year
        fiscalyear_lock_date = lock_date_values.get('fiscalyear_lock_date', None)
        hard_lock_date = lock_date_values.get('hard_lock_date', None)
        if fiscalyear_lock_date or hard_lock_date:
            fiscal_lock_date, field = max([
                (fiscalyear_lock_date, 'fiscalyear_lock_date'),
                (hard_lock_date, 'hard_lock_date'),
            ], key=lambda t: t[0] or date.min)
            company_fiscal_lock_date = max(
                self.env.company.fiscalyear_lock_date or date.min,
                self.env.company.hard_lock_date or date.min,
            )
            if fiscal_lock_date != company_fiscal_lock_date:
                self._create_default_report_external_values(field)
        if fiscalyear_lock_date:
            unreconciled_statement_lines = self.env['account.bank.statement.line'].search(
                self.env.company._get_unreconciled_statement_lines_domain(fiscalyear_lock_date)
            )
            if unreconciled_statement_lines:
                # wizard = self.env['unreconciled.statement.wizard'].create({
                #     'statement_line_ids': [(6, 0, unreconciled_statement_lines.ids)]
                # })
                action = {
                    'name': _("Unreconciled Transactions"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'unreconciled.statement.wizard',
                    'context': {'create': False, 'default_statement_line_ids': unreconciled_statement_lines.ids,'default_fiscalyear_lock_date':fiscalyear_lock_date},
                    'view_mode': 'form',
                    'view_id': self.env.ref('gulfco_account_payment_extended.view_unreconciled_statement_wizard_form').id,
                    'target': 'new'
                }
                return action
            else:
                self.env.company.sudo().write(lock_date_values)
                return True
        else:
            self.env.company.sudo().write(lock_date_values)
            return True
        # self.env.company.sudo().write(lock_date_values)