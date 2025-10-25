from odoo import api, fields, models,_
from datetime import date, timedelta

class UnreconciledStatementWizard(models.TransientModel):
    _name = 'unreconciled.statement.wizard'
    _description = 'Unreconciled Bank Statement Lines Wizard'

    statement_line_ids = fields.Many2many(
        'account.bank.statement.line',
        string="Unreconciled Statement Lines"
    )
    fiscalyear_lock_date = fields.Date(string="Fiscal Year Lock Date")


    def action_postpone(self):
        statement_lines = self.statement_line_ids
        for line in statement_lines:
            original_date = line.date
            # current_date = self.fiscalyear_lock_date
            # new_date = date(
            #     current_date.year + (1 if current_date.month == 12 else 0),
            #     1 if current_date.month == 12 else current_date.month + 1,
            #     1
            # )
            new_date = self.fiscalyear_lock_date + timedelta(days=1)
            # line.write({'transaction_date':original_date,'date': new_date})
            line.move_id.with_context(skip_readonly_check=True).write({'transaction_date':original_date,'date': new_date})

        # move_ids = statement_lines.mapped('move_id')
        print('-------------------')
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        # Close wizard without doing anything
        return {'type': 'ir.actions.act_window_close'}

    def action_statement_line_ids(self):
        action = {
            'name': _("Unreconciled Transactions"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'context': {'create': False},
        }
        if len(self.statement_line_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.statement_line_ids.id,
            })
        else:
            action.update({
                'view_mode': 'kanban,list,form',
                'domain': [('id', 'in', self.statement_line_ids.ids)],
            })
        return action
