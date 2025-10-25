import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state', 'stock_move_ids.quantity',
    #              'stock_quant_ids.not_landed_quantity')
    # @api.depends_context(
    #     'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
    #     'location', 'warehouse_id', 'allowed_company_ids', 'is_storable'
    # )
    # def _compute_quantities(self):
    #     return super()._compute_quantities()
    #
    # def _compute_quantities_dict(self, lot_id=None, owner_id=None, package_id=None, from_date=False, to_date=False):
    #     # Call base logic first
    #     res = super()._compute_quantities_dict(
    #         lot_id=lot_id,
    #         owner_id=owner_id,
    #         package_id=package_id,
    #         from_date=from_date,
    #         to_date=to_date
    #     )
    #
    #     # Only modify when no date filter and current (live stock view)
    #     if not to_date:
    #         Quant = self.env['stock.quant'].with_context(active_test=False)
    #
    #         for product in self:
    #             origin_id = product._origin.id
    #             if origin_id not in res:
    #                 continue
    #
    #             rounding = product.uom_id.rounding
    #
    #             # Find all matching quant records
    #             domain_quant_loc, _, _ = product._get_domain_locations()
    #             quant_domain = [('product_id', '=', origin_id)] + domain_quant_loc
    #             quant_records = Quant.search(quant_domain)
    #
    #             # Sort the quant records by in_date (latest first)
    #             sorted_quants = quant_records.sorted(key=lambda q: q.in_date or fields.Datetime.from_string('1970-01-01'), reverse=True)
    #
    #             # Keep only the latest quant per unique lot_id
    #             seen_lots = set()
    #             unique_latest_quants = self.env['stock.quant']
    #             StockMoveLine = self.env['stock.move.line']
    #             for quant in sorted_quants:
    #                 if quant.lot_id and quant.lot_id.id not in seen_lots:
    #                     seen_lots.add(quant.lot_id.id)
    #                     # Find move lines matching this quant's lot and location
    #                     move_lines = StockMoveLine.search([
    #                         ('lot_id', '=', quant.lot_id.id),
    #                         ('location_dest_id', '=', quant.location_id.id),
    #                         ('move_id.picking_id', '!=', False),
    #                         ('product_id', '=', quant.product_id.id)
    #                     ], order='id desc', limit=1)
    #                     if move_lines and move_lines.move_id and move_lines.move_id.picking_id:
    #                         if not move_lines.move_id.picking_id.enable_costing:
    #                             unique_latest_quants |= quant  # append quant to recordset
    #                     else:
    #                         unique_latest_quants |= quant
    #
    #             # Sum not landed quantity
    #             not_landed_qty = sum(unique_latest_quants.mapped('not_landed_quantity'))
    #
    #             # Adjust qty_available and free_qty
    #             res[origin_id]['qty_available'] = float_round(
    #                 res[origin_id]['qty_available'] - not_landed_qty, precision_rounding=rounding
    #             )
    #
    #             res[origin_id]['free_qty'] = float_round(
    #                 res[origin_id]['free_qty'] - not_landed_qty, precision_rounding=rounding
    #             )
    #
    #             # Adjust virtual_available too
    #             res[origin_id]['virtual_available'] = float_round(
    #                 res[origin_id]['qty_available'] + res[origin_id]['incoming_qty'] - res[origin_id]['outgoing_qty'],
    #                 precision_rounding=rounding
    #             )
    #
    #     return res

