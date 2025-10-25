from collections import defaultdict
from datetime import timedelta

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import groupby, SQL
from odoo.tools.misc import formatLang


class AccountReconcileWizard(models.TransientModel):
    _inherit = 'account.reconcile.wizard'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move_line_ids = self.env['account.move.line'].browse(self.env.context['active_ids'])
        res['partial_move_line_ids'] = [Command.set(move_line_ids.ids)]
        return res

    partial_move_line_ids = fields.Many2many('account.move.line','account_reconcile_wizard_move_line_rel','wizard_id','move_line_id',
        string='Move lines to reconcile',
        required=True)
    
    @api.depends('company_id')
    def _compute_journal_id(self):
        misc_journal = self.env.ref("account.1_general")
        for wizard in self:            
            if misc_journal and misc_journal.type == 'general' and misc_journal.company_id == wizard.company_id:
                wizard.journal_id = misc_journal
            else:
                wizard.journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(wizard.company_id),
                    ('type', '=', 'general')
                ], limit=1)

    def reconcile(self):
        """ Reconcile selected moves, with a transfer and/or write-off move if necessary."""
        self.ensure_one()
        self = self.with_context(from_reconcile_popup=True)  # no need to sync to delete everything
        if self.allow_partials and self.partial_move_line_ids:
            for line in self.partial_move_line_ids:
                if line.amount_residual < 0 :
                    if abs(line.payment_amount) > abs(line.amount_residual):
                        raise UserError("Line %s: Payment amount must not exceed the residual amount." % line.name)
                else:
                    if line.payment_amount > line.amount_residual:
                        raise UserError("Line %s: Payment amount must not exceed the residual amount." % line.name)
                if line.credit > 0.0 and line.payment_amount > 0:
                    raise UserError("Line %s: Credit transactions must have a negative amount." % line.name)
                if line.debit > 0.0 and line.payment_amount < 0:
                    raise UserError("Line %s: Debit transactions cannot have a negative amount." % line.name)

        move_lines_to_reconcile = self.move_line_ids._origin
        do_transfer = self.is_transfer_required
        do_write_off = self.edit_mode or (self.is_write_off_required and not self.allow_partials)
        if do_transfer:
            transfer_move = self.create_transfer()
            lines_to_transfer = move_lines_to_reconcile \
                .filtered(lambda line: line.account_id == self.transfer_from_account_id)
            transfer_line_from = transfer_move.line_ids \
                .filtered(lambda line: line.account_id == self.transfer_from_account_id)
            transfer_line_to = transfer_move.line_ids \
                .filtered(lambda line: line.account_id == self.reco_account_id)
            (lines_to_transfer + transfer_line_from).reconcile()
            move_lines_to_reconcile = move_lines_to_reconcile - lines_to_transfer + transfer_line_to

        if do_write_off:
            write_off_move = self.create_write_off()
            write_off_line_to_reconcile = write_off_move.line_ids[0]
            move_lines_to_reconcile += write_off_line_to_reconcile
            amls_plan = [[move_lines_to_reconcile, write_off_line_to_reconcile]]
        else:
            amls_plan = [move_lines_to_reconcile]

        self.env['account.move.line'].with_context(partial_move_line_ids=self.partial_move_line_ids)._reconcile_plan(amls_plan)
        return move_lines_to_reconcile if not do_transfer else (move_lines_to_reconcile + transfer_move.line_ids)
