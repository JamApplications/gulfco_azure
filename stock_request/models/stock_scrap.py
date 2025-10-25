# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from ast import literal_eval

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    stock_request_line = fields.One2many('stock.request', 'scrap_id')


    # stock_valuation_ids = fields.Many2many('stock.valuation.layer',string="Stock Valuations")

    # def do_scrap(self):
    #     res = super(StockScrap,self).do_scrap()
    #     for record in self:
    #         if record.move_ids:
    #             # stock_valuation_ids = []
    #             stock_request_id = self.env['stock.request'].sudo().search([('scrap_id','=',record.id)])
    #             if stock_request_id and stock_request_id.order_id and stock_request_id.order_id.direction in ['damage_expiry_issue_out','miscellaneous_issue_out']:
    #                 for move in record.move_ids:
    #                     if move.stock_valuation_layer_ids:
    #                         for stock_valuation_layer_id in move.stock_valuation_layer_ids:
    #                             if stock_valuation_layer_id.account_move_id and stock_request_id.order_id.warehouse_id and stock_request_id.order_id.warehouse_id.stock_analytic_account_id:
    #                                 for line in stock_valuation_layer_id.account_move_id.invoice_line_ids:
    #                                     analytic_distribution = {
    #                                         stock_request_id.order_id.warehouse_id.stock_analytic_account_id.id: 100,
    #                                     }
    #                                     line.write({'analytic_distribution': analytic_distribution or None})
    #                             # stock_valuation_ids.append(stock_valuation_layer_id.id)
    #                     else:
    #                         stock_valuation_record = record.move_ids[0]._create_out_svl()
    #                         if stock_valuation_record:
    #                             # record.sudo().write({'stock_valuation_id': stock_valuation_record.id})
    #                             if stock_request_id.order_id.warehouse_id and stock_request_id.order_id.warehouse_id.stock_analytic_account_id:
    #                                 if stock_valuation_record.account_move_id and stock_request_id.order_id.warehouse_id and stock_request_id.order_id.warehouse_id.stock_analytic_account_id:
    #                                     for line in stock_valuation_record.account_move_id.invoice_line_ids:
    #                                         analytic_distribution = {
    #                                             stock_request_id.order_id.warehouse_id.stock_analytic_account_id.id: 100,
    #                                         }
    #                                         line.write({'analytic_distribution': analytic_distribution or None})
    #                             # stock_valuation_ids.append(stock_valuation_record.id)
    #
    #                 # vals = {
    #                 #     'product_id': stock_request_id.product_id.id,
    #                 #     'value': stock_request_id.,
    #                 #     'unit_cost': cost,
    #                 #     'quantity': quantity,
    #                 #     'lot_id': lot.id if lot else False,
    #                 # }
    #             # if len(stock_valuation_ids) > 0:
    #             #     record.write({'stock_valuation_ids':stock_valuation_ids})
    #         stock_request = self.env['stock.request'].sudo().search([('scrap_id','=',record.id)])
    #         if stock_request:
    #             stock_request.action_done()
    #     return res

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        domain = [('id', 'in', (self.move_ids).stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        return dict(action, domain=domain, context=context)

    def _prepare_move_values(self):
        res = super()._prepare_move_values()
        trx_type = None
        for rec in self:
            if rec.stock_request_line.order_id.direction in ['damage_expiry_issue_out']:
                trx_type = 'damage_expiry_issue_out'
            elif rec.stock_request_line.order_id.direction in ['miscellaneous_issue_out']:
                trx_type = 'miscellaneous_issue_out'
            elif rec.stock_request_line.order_id.direction in ['scrap_issuance']:
                trx_type = 'scrap_issuance'
        res['trx_type'] = trx_type

        return res


    def do_scrap(self):
        res = super(StockScrap, self).do_scrap()
        for record in self:
            if record.move_ids:
                stock_request = self.env['stock.request'].sudo().search([('scrap_id', '=', record.id)])
                if (
                        stock_request
                        and stock_request.order_id
                        and stock_request.order_id.direction not in ['internal_transfer', 'van_load', 'van_off_load', 'stock_takeover']
                        # and stock_request.order_id.direction in ['damage_expiry_issue_out', 'miscellaneous_issue_out']
                ):
                    # Use analytic distribution directly from stock.request
                    analytic_distribution = stock_request.analytic_distribution or {}

                    for move in record.move_ids:
                        if move.stock_valuation_layer_ids:
                            for svl in move.stock_valuation_layer_ids:
                                if not svl.lot_id:
                                    svl.write({'lot_id': move.scrap_id.lot_id.id if move.scrap_id and move.scrap_id.lot_id else None})
                                if svl.account_move_id and analytic_distribution:
                                    for line in svl.account_move_id.line_ids:
                                        if line.debit > 0 or line.credit > 0:  # only affect accounting lines
                                            line.write({'analytic_distribution': analytic_distribution})
                        else:
                            # If no SVL, force-create one
                            svl = record.move_ids[0]._create_out_svl()
                            if svl and svl.account_move_id and analytic_distribution:
                                for line in svl.account_move_id.line_ids:
                                    if line.debit > 0 or line.credit > 0:
                                        line.write({'analytic_distribution': analytic_distribution})

                # Finally mark request as done
                if stock_request:
                    stock_request.action_done()

                    order = stock_request.order_id
                    if order and all(order.stock_request_ids.mapped('state')):
                        if set(order.stock_request_ids.mapped('state')) == {'done'}:
                            order.state = 'done'
        return res

