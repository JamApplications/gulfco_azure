from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # excise_journal_entries_count = fields.Integer(compute="compute_excise_journal_entries_count")
    excise_move_id = fields.Many2one('account.move',string="Excise Move")

    def button_validate(self):
        res = super().button_validate()
        for rec in self:
            if rec.state == 'done':
                # po_line_move_ids = rec.move_ids.filtered(lambda s:s.purchase_line_id)
                # if po_line_move_ids:
                #     exice_move_ids = po_line_move_ids.filtered(lambda s:s.purchase_line_id.exercise_price > 0.0)
                #     if exice_move_ids and not rec.purchase_id.enable_costing:
                #         rec.create_exice_journal_entery(exice_move_ids)
                rec.purchase_id._onchange_po_line_state()
        return res

    # def create_exice_journal_entery(self,exice_move_ids):
    #     if not self.company_id.excise_journal_id:
    #         raise UserError(_('Please configure a Excise Journal from accounting setting'))
    #     if not self.company_id.excise_debit_account_id:
    #         raise UserError(_('Please configure a Excise Debit Account from accounting setting'))
    #     if not self.company_id.excise_credit_account_id:
    #         raise UserError(_('Please configure a Excise Credit Account from accounting setting'))
    #     amount = sum(exice_move_ids.mapped('purchase_line_id').mapped('excise_price_total'))
    #     po_order = exice_move_ids.mapped('purchase_line_id').mapped('order_id')
    #     move_id = self.env['account.move'].create({
    #             'journal_id': self.company_id.excise_journal_id.id,
    #             'date': self.scheduled_date,
    #             'ref': 'Jounral entries of excise for the  {}'.format(po_order.name),
    #             'line_ids': [
    #                 (0, 0, {
    #                     'name': 'Excise {}'.format(po_order.name),
    #                     'account_id': self.company_id.excise_debit_account_id.id,
    #                     'debit': amount,
    #                     'credit': 0,
    #                 }),
    #                 (0, 0, {
    #                     'name': 'Excise {}'.format(po_order.name),
    #                     'account_id': self.company_id.excise_credit_account_id.id,
    #                     'debit': 0,
    #                     'credit': amount,
    #                 }),
    #             ],
    #             'excise_stock_picking_id': self.id,
    #         })
    #     move_id.action_post()
    #     self.sudo().write({'excise_move_id': move_id.id})

    def action_view_excise_journal_entries(self):
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False, 'edit': False},
            'res_id': self.excise_move_id.id,
            'view_mode': 'form',

        }