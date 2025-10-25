from odoo import fields, models,api


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    bank_line = fields.Integer(string='Bank Line',compute="_compute_bank_line",store=True)

    @api.depends('statement_id','statement_id.line_ids')
    def _compute_bank_line(self):
        all_statement_ids = self.mapped('statement_id').ids
        for statement_id in all_statement_ids:
            lines = self.search([('statement_id', '=', statement_id)], order='id asc')
            for idx, line in enumerate(lines, start=1):
                line.bank_line = idx