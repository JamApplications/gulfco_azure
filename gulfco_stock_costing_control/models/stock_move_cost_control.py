from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from odoo.addons.stock_account.models.stock_move import StockMove as StockAccountStockMove
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    # def _get_price_unit(self):
    #     if self.env.context.get('from_exice'):
    #         price = super()._get_price_unit()
    #         if self.purchase_line_id and self.purchase_line_id.is_excise:
    #         if self.product_id.lot_valuated:
    #             p
    #         else:
    #             price = {""}
    #             return {self.env['stock.lot']: price}
    #     else:
    #         return super()._get_price_unit()

    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        svl_vals = super()._prepare_common_svl_vals()

        # Add the `is_deferred_costing` field to the common values.
        svl_vals['is_deferred_costing'] = False
        if (
            self.picking_id
            and self.picking_id.purchase_id
            and self.picking_id.purchase_id.enable_costing
            and not any(lc.state == "done" for lc in self.picking_id.landed_cost_ids)
        ):
            # If the picking is linked to a purchase order with costing enabled and there are not any Done Landed Cost,
            # we set `is_deferred_costing` to True.
            svl_vals['is_deferred_costing'] = True
        return svl_vals

    def product_price_update_before_done(self, forced_qty=None, before_cost=None):
        if self.env.context.get('force_avco_update_after_lc'):
            tmpl_dict = defaultdict(lambda: 0.0)
            for move in self:
                if not move._is_in():
                    continue
                if move.with_company(move.company_id).product_id.cost_method != 'average':
                    continue
                if move.state != 'done':
                    continue

                product = move.product_id.with_company(move.company_id).sudo()
                rounding = product.uom_id.rounding

                qty = forced_qty[1] if forced_qty else move.product_qty
                move_cost = sum(move.stock_valuation_layer_ids.mapped('value'))

                # deferred_svls = self.env['stock.valuation.layer'].sudo().search([
                #     ('stock_move_id.picking_id', 'in', self.picking_id.ids),
                #     ('is_deferred_costing', '=', True),
                #     ('product_id', '=', product.id),                  
                # ])
                # new_svl_qty = 0
                # if deferred_svls:
                #     new_svl_qty = sum(deferred_svls.mapped('quantity'))
                # product_tot_qty_available = product.quantity_svl + tmpl_dict[product.id] - new_svl_qty
                # picking= self.env['stock.picking']
                # excise_moves = self.env['stock.move'].search([('purchase_line_id', '!=', False),('picking_id.enable_costing', '=', True),('purchase_line_id.exercise_price', '>', 0), ('product_id', '=', product.id)])
                # po_line_move_ids = picking.move_ids.filtered(lambda s:s.purchase_line_id)
                # if po_line_move_ids:
                #     exice_move_ids = po_line_move_ids.filtered(lambda s:s.purchase_line_id.exercise_price > 0.0)
                #     if exice_move_ids and picking.purchase_id.enable_costing:
                # excise_entries = False
                # if excise_moves:
                #     excise_entries = self.env['account.move.line'].search([('move_id.excise_stock_picking_id', '!=', False),('move_id.excise_stock_picking_id', 'in', excise_moves.picking_id.ids)])
                # total_excise_amount = 0
                # if excise_entries:
                #     total_excise_amount = abs(sum((excise_entries.mapped('debit'))))
                # if self._context.get('from_excise_valuation'):
                all_svls_of_product = self.env['stock.valuation.layer'].sudo().search([
                    ('product_id', '=', product.id),
                    ('is_deferred_costing', '=', False)
                ])
                total_svl_value = sum(all_svls_of_product.mapped('value'))
                total_svl_qty = sum(all_svls_of_product.mapped('quantity'))
                
                # if float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                #     if self.env.context.get("from_excise_valuation"):
                #         new_std_price =  total_svl_value / total_svl_qty
                #     else:
                #         new_std_price = move_cost / qty
                #     # new_std_price = (move_cost + total_excise_amount) / qty
                # else:
                #     prev_cost = product.standard_price
                #     if before_cost and product.id in before_cost:
                #         prev_cost = before_cost.get(product.id)
                #     if self.env.context.get('from_excise_valuation'):
                #         new_std_price =  total_svl_value / total_svl_qty
                #     else:
                #         new_std_price = ((prev_cost * product_tot_qty_available) + move_cost) / (product_tot_qty_available + qty)
                    # new_std_price = ((prev_cost * product_tot_qty_available) + move_cost + total_excise_amount) / (product_tot_qty_available + qty)

                new_std_price =  total_svl_value / total_svl_qty
                
                # Update product cost
                product.with_context(disable_auto_svl=True).write({
                    'standard_price': new_std_price,
                })
                tmpl_dict[product.id] += qty

        else:
            # Default Odoo behavior
            return super().product_price_update_before_done(forced_qty=forced_qty)

def _action_done_with_deferred_costing(self, cancel_backorder=False):
    _logger.info("GULFCO_STOCK_COSTING_CONTROL _action_done_with_deferred_costing")
    # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
    valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
    for move in self:
        if move.state == 'done':
            continue
        if float_is_zero(move.quantity, precision_rounding=move.product_uom.rounding):
            continue
        if not any(move.move_line_ids.mapped('picked')):
            continue
        for valued_type in self._get_valued_types():
            if getattr(move, '_is_%s' % valued_type)():
                valued_moves[valued_type] |= move

    res = super(StockAccountStockMove, self)._action_done(cancel_backorder=cancel_backorder)

    # # AVCO application
    # valued_moves['in'].product_price_update_before_done()

    # AVCO application — skip deferred costing POs
    avco_moves = valued_moves['in'].filtered(
        lambda m: not (
            m.picking_id
            and m.picking_id.purchase_id
            and m.picking_id.purchase_id.enable_costing
            and not any(lc.state == "done" for lc in m.picking_id.landed_cost_ids)
        )
    )
    avco_moves.product_price_update_before_done()

    # '_action_done' might have deleted some exploded stock moves
    valued_moves = {value_type: moves.exists() for value_type, moves in valued_moves.items()}

    # '_action_done' might have created an extra move to be valued
    for move in res - self:
        for valued_type in self._get_valued_types():
            if getattr(move, '_is_%s' % valued_type)():
                valued_moves[valued_type] |= move

    stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
    # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
    for valued_type in self._get_valued_types():
        todo_valued_moves = valued_moves[valued_type]
        if todo_valued_moves:
            todo_valued_moves._sanity_check_for_valuation()
            stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

    # Only validate accounting for SVLs that are not deferred (Custom check using `is_deferred_costing`)
    impacting_svls = stock_valuation_layers.filtered(lambda svl: not svl.is_deferred_costing)
    if impacting_svls:
        impacting_svls._validate_accounting_entries()
        impacting_svls._validate_analytic_accounting_entries()
        impacting_svls._check_company()

    # Skip product price update for lot-valuated products if SVLs are deferred (Custom check)
    out_moves_to_update = valued_moves['out'].filtered(
        lambda m: m.product_id.lot_valuated and not any(
            svl.is_deferred_costing for svl in m.stock_valuation_layer_ids)
    )
    if out_moves_to_update:
        out_moves_to_update.sudo()._product_price_update_after_done()

    # stock_valuation_layers._validate_accounting_entries()
    # stock_valuation_layers._validate_analytic_accounting_entries()

    # valued_moves['out'].filtered(lambda m: m.product_id.lot_valuated).sudo()._product_price_update_after_done()

    # stock_valuation_layers._check_company()

    # For every in move, run the vacuum for the linked product.
    # Only vacuum for products with non-deferred SVLs (Custom)
    products_to_vacuum = valued_moves['in'].filtered(
        lambda m: not any(svl.is_deferred_costing for svl in m.stock_valuation_layer_ids)
    ).mapped('product_id')
    if products_to_vacuum:
        company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
        # products_to_vacuum._run_fifo_vacuum(company)
    # products_to_vacuum = valued_moves['in'].mapped('product_id')
    # company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
    # products_to_vacuum._run_fifo_vacuum(company)

    return res

# Monkey patch original method with SVL no impact for non landed picking support
StockAccountStockMove._action_done = _action_done_with_deferred_costing
