# Copyright 2017-2020 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from collections import defaultdict
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    package_id = fields.Many2one('stock.quant.package', 'Package Type', copy=False)
    allocation_ids = fields.One2many(
        comodel_name="stock.request.allocation",
        inverse_name="stock_move_id",
        string="Stock Request Allocation",
    )
    stock_request_ids = fields.One2many(
        comodel_name="stock.request",
        string="Stock Requests",
        compute="_compute_stock_request_ids",
    )

    # ------------------------------
    # Small helper shortcuts
    # ------------------------------
    def _req_order(self):
        """Return request order on the picking (single move-safe)."""
        self.ensure_one()
        picking = self.picking_id
        return picking and picking.request_order_id or False

    def _is_recv_direction(self):
        """True if picking request order direction is in the special receiving set."""
        self.ensure_one()
        ro = self._req_order()
        return bool(ro and ro.direction in ('foc_receiving', 'miscellaneous_receiving'))

    # ------------------------------
    # Core overrides
    # ------------------------------
    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        ro = self.env.context.get('request_order_id')
        if ro:
            vals['request_order_id'] = ro.id
        return vals

    def _get_price_unit(self):
        # Keep semantics: when special directions, derive cost from request lines.
        if self._is_recv_direction():
            ro = self._req_order()
            # Single product cost lookup (avoid .filtered in Python with lambda)
            # Build a dict product_id -> cost once and read from it
            lines = ro.stock_request_ids
            cost_by_product = {l.product_id.id: l.cost for l in lines if l.product_id}
            unit_cost = cost_by_product.get(self.product_id.id)
            if unit_cost is not None:
                if self.product_id.lot_valuated:
                    # map each lot in this move to the same unit_cost
                    return {lot: unit_cost for lot in self.lot_ids}
                # preserve your original fallback key
                return {self.env['stock.lot']: unit_cost}
        return super()._get_price_unit()

    def _prepare_account_move_line(
        self, qty, cost, credit_account_id, debit_account_id, svl_id, description
    ):
        """
        Optimize:
        - Resolve stock request lines once.
        - Pre-compute default expense/valuation account per product in batch.
        - Use a compact product -> list[(direction, override_acc)] map.
        - Single pass over valuation lines.
        """
        res = super()._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description
        )

        # Skip for purchase / direct_delivery_order same as your code
        if self.picking_id.trx_type in ("direct_delivery_order", "purchase"):
            return res

        StockRequest = self.env["stock.request"].sudo()

        # Resolve stock request *lines* once
        req_lines = self.env['stock.request']
        if self.picking_id and self._req_order():
            # From the order on the picking (no extra query)
            req_lines = self._req_order().stock_request_ids.sudo()
        elif self.scrap_id:
            # Search only when scrapping
            req_lines = StockRequest.search([('scrap_id', '=', self.scrap_id.id)], limit=0)
        # else: empty recordset, nothing to override

        if not req_lines:
            return res

        # Build product -> list of (direction, override_account) (keep full behavior)
        overrides_by_product = defaultdict(list)
        for rl in req_lines:
            product_id = rl.product_id.id if rl.product_id else False
            if not product_id:
                continue
            direction = rl.order_id.direction if rl.order_id else None
            override_acc = rl.direction_account_id.id or (rl.order_id.direction_account_id.id if rl.order_id else False)
            if override_acc and direction:
                overrides_by_product[product_id].append((direction, override_acc))

        if not res:
            return res

        # Batch compute default accounts for all products appearing in result
        product_ids = {line[2].get('product_id') for line in res if line and isinstance(line, (list, tuple))}
        product_ids.discard(None)
        products = self.env['product.product'].browse(list(product_ids))
        default_acc_by_product = {
            p.id: (p.property_account_expense_id.id or p.categ_id.property_stock_valuation_account_id.id or False)
            for p in products
        }

        # Single pass over valuation lines
        for line in res:
            vals = line[2]
            pid = vals.get("product_id")
            if not pid:
                continue

            # Start with default account (same as original)
            account_id = default_acc_by_product.get(pid)

            # Apply override rule if any
            ov_list = overrides_by_product.get(pid)
            if ov_list:
                bal = vals.get("balance", 0)
                # Follow your original polarity rules
                for direction, ov_acc in ov_list:
                    if not ov_acc:
                        continue
                    # for the credit side
                    if direction in ["miscellaneous_receiving", "foc_receiving"] and bal < 0:
                        account_id = ov_acc
                        break
                    # for the debit side
                    if direction in ["sample_issue_out","consumable_issuance","scrap_issuance","damage_expiry_issue_out","miscellaneous_issue_out"] and bal > 0:
                        account_id = ov_acc
                        break

            if account_id:
                vals["account_id"] = account_id

        return res

    def _get_out_svl_vals(self, forced_quantity):
        """
        Optimize:
        - Build a quick index of returned svl dicts by move_id (no repeated scans).
        - Avoid per-iteration searches; reuse order lines / scrap once.
        """
        svl_vals_list = super()._get_out_svl_vals(forced_quantity)
        if not svl_vals_list:
            return svl_vals_list

        # Index once: move_id -> list(svl_dict)
        by_move = defaultdict(list)
        for svl in svl_vals_list:
            mid = svl.get('stock_move_id')
            if mid:
                by_move[mid].append(svl)

        for move in self:
            # 1) Receiving directions with order lines: set cost from request lines
            if move._is_recv_direction():
                ro = move._req_order()
                if ro:
                    cost_by_product = {l.product_id.id: l.cost for l in ro.stock_request_ids if l.product_id}
                    unit_cost = cost_by_product.get(move.product_id.id)
                    if unit_cost is not None:
                        for svl in by_move.get(move.id, ()):
                            qty = svl.get('quantity', 0.0)
                            svl['unit_cost'] = unit_cost
                            svl['value'] = unit_cost * qty

            # 2) Scrap path: compute once (at most 1 small query)
            if move.scrap_id:
                # Usually 1 line; no limit to keep parity with your code
                req_scrap = self.env['stock.request'].sudo().search([
                    ('scrap_id', '=', move.scrap_id.id),
                ])
                for rl in req_scrap:
                    # Keep original exclusions
                    if not rl or not rl.order_id or rl.order_id.direction in (
                        'internal_transfer', 'van_load', 'van_off_load', 'stock_takeover'
                    ):
                        continue
                    custom_cost = rl.cost or move.product_id.standard_price
                    qty = rl.product_uom_qty
                    for svl in by_move.get(move.id, ()):
                        svl.update({
                            'unit_cost': custom_cost,
                            'value': custom_cost * qty,
                            'quantity': qty,
                        })
        return svl_vals_list

    def _generate_valuation_lines_data(
        self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description
    ):
        rslt = super()._generate_valuation_lines_data(
            partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description
        )
        # Keep same behavior; just minimize lookups
        if not self._is_recv_direction():
            return rslt
        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if svl.account_move_line_id:
            return rslt
        ro = self._req_order()
        wh = ro and ro.warehouse_id
        aa = wh and wh.stock_analytic_account_id
        if aa:
            dist = {aa.id: 100}
            rslt['credit_line_vals']['analytic_distribution'] = dist
            rslt['debit_line_vals']['analytic_distribution'] = dist
        return rslt

    def _get_analytic_distribution(self):
        if self._is_recv_direction():
            ro = self._req_order()
            wh = ro and ro.warehouse_id
            aa = wh and wh.stock_analytic_account_id
            if aa:
                return {aa.id: 100}
        return super()._get_analytic_distribution()

    @api.depends("allocation_ids")
    def _compute_stock_request_ids(self):
        # Already efficient: pure in-memory mapping
        for rec in self:
            rec.stock_request_ids = rec.allocation_ids.mapped("stock_request_id")

    def _merge_moves_fields(self):
        res = super()._merge_moves_fields()
        res["allocation_ids"] = [(4, m.id) for m in self.mapped("allocation_ids")]
        return res

    @api.constrains("company_id")
    def _check_company_stock_request(self):
        """
        Optimize: single query to fetch allocations for all moves,
        then validate in memory (instead of N× search_count).
        """
        allocs = self.env["stock.request.allocation"].search([('stock_move_id', 'in', self.ids)])
        # Any allocation whose company differs from its move's company
        bad = any(a.company_id.id != a.stock_move_id.company_id.id for a in allocs)
        if bad:
            raise ValidationError(_("The company of the stock request must match with that of the location."))

    def copy_data(self, default=None):
        default = dict(default or {})
        if "allocation_ids" not in default:
            default["allocation_ids"] = [
                (0, 0, {
                    "stock_request_id": alloc.stock_request_id.id,
                    "requested_product_uom_qty": alloc.requested_product_uom_qty,
                })
                for alloc in self.allocation_ids
            ]
        return super().copy_data(default)

    def _action_cancel(self):
        res = super()._action_cancel()
        self.mapped("allocation_ids.stock_request_id").sudo().check_cancel()
        return res

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        self.mapped("allocation_ids.stock_request_id").sudo().check_done()
        return res