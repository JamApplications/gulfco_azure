# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    is_rma_refund = fields.Boolean(string="Is RMA Refund")
    sale_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        compute='_compute_sale_id',
        store=True,
        readonly=False
    )

    @api.depends('invoice_line_ids.sale_line_ids.order_id')
    def _compute_sale_id(self):
        for move in self:
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            move.sale_id = sale_orders[0] if sale_orders else False

    def _check_rma_invoice_lines_qty(self):
        # Override base RMA module method
        pass
    #     """Ensure refunded quantity doesn't exceed RMA quantity, supporting multi-line RMAs."""
    #     precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
    #
    #     def is_invalid_line(line):
    #         if not line.rma_id or not line.product_id:
    #             return False
    #
    #         # Find the matching RMA line by product
    #         rma_line = line.rma_id.rma_product_line_ids.filtered(
    #             lambda l: l.product_id.id == line.product_id.id
    #         )
    #         if not rma_line:
    #             return False
    #
    #         # Compare invoice quantity against RMA qty
    #         return float_compare(
    #             line.quantity, rma_line[0].product_uom_qty, precision
    #         ) > 0
    #
    #     return self.sudo().mapped("invoice_line_ids").filtered(is_invalid_line)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()
        if self.move_id and self.move_id.is_rma_refund:
            rma = self.move_id.invoice_line_ids.mapped('rma_id')
            if rma and rma[0].rma_type == 'base_on_product':
                last_stock_move = self.env['stock.move'].search([
                    ('product_id', '=', self.product_id.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', 'in', ['done']),
                    ('partner_id', 'child_of', self.partner_id.id),
                    ('stock_valuation_layer_ids', '!=', False)
                ], order='create_date desc,id desc', limit=1)
                if last_stock_move:
                    valuation_layers = self.env['stock.valuation.layer'].search(
                        [('stock_move_id', '=', last_stock_move.id)],
                        order='create_date desc',
                        limit=1)
                    if valuation_layers:
                        # price_unit = abs(valuation_layers.value)
                        price_unit = abs(valuation_layers.unit_cost)
            elif (
                rma
                and rma[0].rma_type in ["base_on_delivery", "base_on_invoice"]
                and "rma_line_cogs_map" in self.env.context
            ):
                rma_line_cogs_map = self.env.context["rma_line_cogs_map"]
                rma_lines = rma[0].line_ids.filtered(lambda l: l.product_id == self.product_id)
                if rma_lines and rma_lines[0] in rma_line_cogs_map:
                    price_unit = abs(rma_line_cogs_map[rma_lines[0]])
        return price_unit
