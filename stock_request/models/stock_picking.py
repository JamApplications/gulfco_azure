# Copyright 2017-2020 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
import time

_logger = logging.getLogger(__name__)
class StockPicking(models.Model):
    _inherit = "stock.picking"

    stock_request_ids = fields.Many2many(
        'stock.request',
        'stock_request_picking_rel',  # same relation table
        'picking_id',  # column for stock.picking
        'request_id',  # column for stock.request
        string="Stock Requests",
    )

    # stock_request_ids = fields.One2many(
    #     comodel_name="stock.request",
    #     string="Stock Requests",
    #     compute="_compute_stock_request_ids",
    # )
    stock_request_count = fields.Integer(
        "Stock Request #", compute="_compute_stock_request_ids"
    )

    stock_request_id = fields.Many2one('stock.request', string="Request Order")
    request_order_id = fields.Many2one('stock.request.order', string="Request Order")
    direction = fields.Selection(
        related='request_order_id.direction',
        string="Request Type",
        store=True
    )

    @api.depends("move_ids")
    def _compute_stock_request_ids(self):
        for rec in self:
            # rec.stock_request_ids = rec.move_ids.mapped("stock_request_ids")
            rec.stock_request_count = len(rec.stock_request_ids)

    def action_view_stock_request(self):
        """
        :return dict: dictionary value for created view
        """
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock_request.action_stock_request_form"
        )

        requests = self.mapped("stock_request_ids")
        if len(requests) > 1:
            action["domain"] = [("id", "in", requests.ids)]
        elif requests:
            action["views"] = [
                (self.env.ref("stock_request.view_stock_request_form").id, "form")
            ]
            action["res_id"] = requests.id
        return action



    van_api_only = fields.Boolean(
        string="Van app validation only",
        compute="_compute_van_api_only",
        store=True
    )

    van_approve_load_api = fields.Boolean(default=False)

    @api.depends('location_id', 'location_dest_id.location_group', 'trx_type')
    def _compute_van_api_only(self):
        """Mark pickings that are the final leg: Transit -> Van."""
        for p in self:
            p.van_api_only = bool(
                p.trx_type == 'van_load'
                and p.location_dest_id.location_group == 'van'
            )

    def button_validate(self):
        _logger.info("STOCK_REQUEST111111111111111111")
        _logger.info("STOCK_REQUEST111111111111111111")
        if self.request_order_id:
            _logger.info("stock request id %s" % self.stock_request_id)
            res = super(StockPicking,self.with_context(request_order_id = self.request_order_id)).button_validate()
            self.request_order_id.stock_request_ids.with_context(custom_picking_ids=self)._compute_qty()
            _logger.info("stock request id after compute")
            if not self.show_next_pickings:
                # stock_request = self.env['stock.request'].sudo().search([('picking_ids', 'in', self.ids)])                
                # Use SQL to fetch stock.request IDs via the M2M relation table
                query = """
                    SELECT DISTINCT srp.request_id
                    FROM stock_request_picking_rel srp
                    WHERE srp.picking_id = ANY(%s)
                """
                params = (self.ids,)
                self.env.cr.execute(query, params)
                rows = self.env.cr.fetchall()
                request_ids = [r[0] for r in rows if r and r[0]]
                stock_request = self.env['stock.request'].sudo().browse(request_ids)
                
                _logger.info("stock request ids %s" % stock_request)
                stock_request.action_done()
                _logger.info("action done")
        else:
            _logger.info("STOCK_REQUEST111111111111111111 Call Super")
            res = super(StockPicking, self).button_validate()
            return res
            _logger.info("STOCK_REQUEST111111111111111111 END of Call Super")

        for picking in self:
            request_order = picking.request_order_id
            van_ctx = picking.van_approve_load_api
            if picking.van_api_only and not (van_ctx):
                raise UserError(_(
                    "Final Van Load must be validated from the Van mobile app.\n"
                    "This transfer (Transit → Van) is locked for warehouse UI."
                ))

            if not request_order:
                continue

            # Collect analytic distributions from all stock.requests
            analytic_distribution = {}
            for stock_request in request_order.stock_request_ids:
                if stock_request.analytic_distribution:
                    # merge (if multiple requests exist, you might need to split %)
                    analytic_distribution.update(stock_request.analytic_distribution)

            if not analytic_distribution:
                continue

            # Apply only if direction matches
            if request_order.direction not in [
                'internal_transfer', 'van_load', 'van_off_load', 'stock_takeover'
            ]:
                i = 0
                y = 0
                z = 0
                for move in picking.move_ids:
                    i += 1
                    _logger.info("STOCK_REQUEST I %s" %i)
                    for svl in move.stock_valuation_layer_ids:
                        y += 1
                        _logger.info("STOCK_REQUEST Y %s" % y)
                        if svl.account_move_id:
                            for line in svl.account_move_id.line_ids:
                                z += 1
                                _logger.info("STOCK_REQUEST Z %s" % z)
                                if line.debit > 0 or line.credit > 0:
                                    line.write({'analytic_distribution': analytic_distribution})

        _logger.info("END STOCK_REQUEST111111111111111111")
        return res
    
    def _pre_action_done_hook(self):
        _logger.info("STOCK_REQUEST1111 _pre_action_done_hook")
        if not self.request_order_id:
            return super()._pre_action_done_hook()
        for picking in self:

            _logger.info("STOCK_REQUEST1111 enter _pre_action_done_hook")
            has_quantity = False
            has_pick = False
            if picking.move_ids.filtered(lambda s: s.quantity == 0 and s.picked) and picking.move_ids.filtered(
                    lambda s: s.quantity > 0 and not s.picked):
                green_moves = picking.move_ids.filtered(lambda s: s.quantity > 0)
                green_moves.picked = True
            for move in picking.move_ids:
                if move.quantity:
                    has_quantity = True
                    # if move.request_order_id and not move.picked:
                    #     move.picked = True
                if move.scrapped:
                    continue
                if move.picked:
                    has_pick = True
                if has_quantity and has_pick:
                    break
            if has_quantity and not has_pick:
                picking.move_ids.picked = True
            _logger.info("STOCK_REQUEST1111 out _pre_action_done_hook")

        if not self.env.context.get('skip_backorder'):
            _logger.info("STOCK_REQUEST1111 backorder _pre_action_done_hook")

            pickings_to_backorder = self._check_backorder()
            if pickings_to_backorder:
                return pickings_to_backorder._action_generate_backorder_wizard(show_transfers=self._should_show_transfers())
        return True
