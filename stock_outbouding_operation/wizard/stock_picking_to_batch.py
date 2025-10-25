from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPickingToBatchInh(models.TransientModel):
    _inherit = 'stock.picking.to.batch'


    def attach_pickings(self):
        self.ensure_one()
        pickings = self.env['stock.picking']
        if self.env.context.get('is_stock_move'):
            stock_moves = self.env['stock.move'].sudo().browse(self.env.context.get('active_ids'))
            pickings = stock_moves.picking_id
        else:
            pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids'))
        if self.mode == 'new':
            company = pickings.company_id
            if len(company) > 1:
                raise UserError(_("The selected pickings should belong to an unique company."))
            batch = self.env['stock.picking.batch'].create({
                'user_id': self.user_id.id,
                'company_id': company.id,
                'picking_type_id': pickings[0].picking_type_id.id,
                'description': self.description,
            })
        else:
            batch = self.batch_id

        pickings.write({'batch_id': batch.id})
        # you have to set some pickings to batch before confirm it.
        if self.mode == 'new' and not self.is_create_draft:
            batch.action_confirm()
        return {
            'name': _('Batch Transfer'),
            'view_mode': 'form',
            'res_model': 'stock.picking.batch',
            'type': 'ir.actions.act_window',
            'res_id': batch.id,
        }