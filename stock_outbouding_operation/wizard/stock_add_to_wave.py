# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPickingToWaveInh(models.TransientModel):
    _inherit = 'stock.add.to.wave'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'stock.move' and self.env.context.get('is_stock_move'):
            pickings = self.env['stock.picking']
            if self.env.context.get('is_stock_move'):
                stock_moves = self.env['stock.move'].sudo().browse(self.env.context.get('active_ids'))
                pickings = stock_moves.picking_id
                res['picking_ids'] = pickings.ids
        return res