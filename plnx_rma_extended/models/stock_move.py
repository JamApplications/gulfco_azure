# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.rma.models.stock_move import StockMove


class StockMoveInherit(models.Model):
    _inherit = "stock.move"


    return_reason_id = fields.Many2one(
        comodel_name="rma.return.reason",
        string="Return Reason",
        copy=False,
        tracking=True,
        required=False,
    )

    def _action_done(self, cancel_backorder=False):
        """Avoids to validate stock.move with less quantity than the
        quantity in the linked receiver RMA. It also set the appropriated
        linked RMA to 'received' or 'delivered'.
        """
        for move in self.filtered(lambda r: r.state not in ("done", "cancel")):
            rma_receiver = move.sudo().rma_receiver_ids
            if rma_receiver and rma_receiver[0].rma_type == 'base_on_delivery' and rma_receiver[0].line_ids:
                line = rma_receiver[0].line_ids.filtered(lambda s:s.move_id == move.origin_returned_move_id)
                if line and line.product_uom_qty != move.quantity:
                    raise ValidationError(
                        _(
                            "The quantity done for the product '%(id)s' must "
                            "be equal to its initial demand because the "
                            "stock move is linked to an RMA (%(name)s)."
                        )
                        % (
                            {
                                "id": move.product_id.name,
                                "name": move.rma_receiver_ids[0].name,
                            }
                        )
                    )
            else:
                if rma_receiver and rma_receiver[0].rma_type == 'base_on_product' and rma_receiver.product_line_ids.filtered(lambda r: r.product_id == move.product_id) and  move.quantity > sum(rma_receiver.product_line_ids.filtered(lambda r: r.product_id == move.product_id).mapped('product_uom_qty')):
                    raise ValidationError(
                        _(
                            "The quantity done for the product '%(id)s' must "
                            "be equal to its initial demand because the "
                            "stock move is linked to an RMA (%(name)s)."
                        )
                        % (
                            {
                                "id": move.product_id.name,
                                "name": move.rma_receiver_ids.name,
                            }
                        )
                    )
        res = super(StockMove,self)._action_done(cancel_backorder=cancel_backorder)
        move_done = self.filtered(lambda r: r.state == "done").sudo()
        # Set RMAs as received. We sudo so we can grant the operation even
        # if the stock user has no RMA permissions.
        to_be_received = (
            move_done.sudo()
            .mapped("rma_receiver_ids")
            .filtered(lambda r: r.state == "confirmed")
        )
        to_be_received.update_received_state_on_reception()
        # Set RMAs as delivered
        move_done.mapped("rma_id").update_replaced_state()
        move_done.mapped("rma_id").update_returned_state()
        return res

    def _get_price_unit(self):
        if self.rma_receiver_ids and self.rma_receiver_ids[0].rma_type == 'base_on_product':
            # last_line = self.env['purchase.order.line'].search([
            #     ('product_id', '=', self.product_id.id),
            #     ('price_unit','>',0.0),
            #     ('order_id.state', 'in', ['purchase', 'done'])
            # ], order='date_planned desc,id desc', limit=1)
            # last_line = self.env['sale.order.line'].search([
            #     ('product_id', '=', self.product_id.id),
            #     ('order_partner_id','=',self.rma_receiver_ids[0].partner_id.id),
            #     ('price_unit','>',0.0),
            #     ('order_id.state', 'in', ['sale'])
            # ], order='id desc', limit=1)
            value = 0.0
            last_stock_move = self.env['stock.move'].search([
                ('product_id', '=', self.product_id.id),
                ('picking_type_code','=','outgoing'),
                ('state', 'in', ['done']),
                ('partner_id','child_of',self.rma_receiver_ids[0].partner_id.id),
                ('stock_valuation_layer_ids','!=',False)
            ], order='create_date desc,id desc', limit=1)
            if last_stock_move:
                valuation_layers = self.env['stock.valuation.layer'].search(
                    [('stock_move_id', '=', last_stock_move.id)],
                    order='create_date desc',
                    limit=1)
                if valuation_layers:
                    value = valuation_layers.unit_cost
                    if self.product_id.lot_valuated:
                        return {lot: value for lot in self.lot_ids}
                    else:
                        return {self.env['stock.lot']: value}
                else:
                    return super()._get_price_unit()
            else:
                return super()._get_price_unit()
        else:
            return super()._get_price_unit()
    # StockMove._action_done = _action_done

    # def _get_in_svl_vals(self, forced_quantity):
    #     svl_vals_list = super()._get_in_svl_vals(forced_quantity)
    #     for idx, move in enumerate(self):
    #         if move.picking_type_id.code != 'incoming':
    #             continue
    #         excise_price = move.purchase_line_id.exercise_price or 0.0
    #         if not excise_price:
    #             continue
    #         qty = svl_vals_list[idx].get('quantity', 0.0)
    #         additional_value = excise_price * qty
    #         svl_vals_list[idx]['unit_cost'] += excise_price
    #         svl_vals_list[idx]['value'] += additional_value
    #     return svl_vals_list
    
    
    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries"""
        self.ensure_one()
        svl_am_vals = super(StockMove, self)._account_entry_move(qty=qty, description=description, svl_id=svl_id, cost=cost)
        datafix_effective_date = self._context.get('datafix_effective_date', False)
        if not datafix_effective_date:
            return svl_am_vals
        
        for vals in svl_am_vals:
            vals['date'] = datafix_effective_date
        return svl_am_vals
             
