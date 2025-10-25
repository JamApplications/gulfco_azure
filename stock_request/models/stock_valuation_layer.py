# -*- coding: utf-8 -*-

from odoo import models, api, fields, _


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    source_document = fields.Char(related='stock_move_id.origin')
    production_date = fields.Date(related='lot_id.production_date')
    expiry_date = fields.Datetime(related='lot_id.expiration_date')
    trx_type = fields.Selection(related='stock_move_id.trx_type')
    source_location = fields.Many2one('stock.location',related='stock_move_id.location_id')
    
    @api.model_create_multi
    def create(self, vals_list):
        model = self._context.get('active_model')
        id = self._context.get('active_id')
        is_scrap = self._context.get('is_scrap')
        if model and model == 'stock.request.order':
            stock_request_order = self.env[model].browse(id).exists()
            if stock_request_order and stock_request_order.direction in [
                "damage_expiry_issue_out",
                "miscellaneous_issue_out",
                "scrap_issuance",
            ]:
                for vals in vals_list:
                    qty = vals.get('quantity')
                    value = vals.get('value')
                    if qty and value and qty > 0 and value > 0:
                        vals['quantity'] = vals['quantity'] * -1
                        vals['value'] = vals['value'] * -1
        elif is_scrap:
            for vals in vals_list:
                if vals.get('stock_move_id'):
                    move = self.env['stock.move'].browse(vals.get('stock_move_id'))
                    if move and move.exists() and move.scrap_id and move.scrap_id.stock_request_line:
                        stock_request_direction = move.scrap_id.stock_request_line.order_id.direction
                        if stock_request_direction in [
                            "damage_expiry_issue_out",
                            "miscellaneous_issue_out",
                            "scrap_issuance",
                        ]:
                            qty = vals.get('quantity')
                            value = vals.get('value')
                            if qty and value and qty > 0 and value > 0:
                                vals['quantity'] = vals['quantity'] * -1
                                vals['value'] = vals['value'] * -1
        return super(StockValuationLayer, self).create(vals_list)
