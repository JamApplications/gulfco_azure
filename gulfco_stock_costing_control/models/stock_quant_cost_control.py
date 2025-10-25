from odoo import models, api, fields, _
from odoo.tools.float_utils import float_round

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    picking_id = fields.Many2one('stock.picking', string='Related Picking')
    not_landed_quantity = fields.Float('Not landed cost quantity',
                                       default=0.0,
                                       readonly=True,
    )

    @api.depends('quantity', 'reserved_quantity', 'not_landed_quantity')
    def _compute_available_quantity(self):
        for quant in self:
            # quant.available_quantity = quant.quantity - quant.reserved_quantity - quant.not_landed_quantity
            quant.available_quantity = quant.quantity - quant.reserved_quantity

    @api.depends('quantity', 'reserved_quantity', 'not_landed_quantity')
    def _compute_inventory_quantity_auto_apply(self):
        stock_locations = set(self.env['stock.warehouse'].search([]).lot_stock_id.ids)
        for quant in self:
            if quant.location_id.id in stock_locations:
                # Last picking quant → adjust with not_landed_quantity
                quant.inventory_quantity_auto_apply = quant.quantity
            else:
                quant.inventory_quantity_auto_apply = quant.quantity - quant.not_landed_quantity
            # quant.inventory_quantity_auto_apply = quant.quantity - quant.reserved_quantity - quant.not_landed_quantity

    @api.model
    def _unlink_zero_quants(self):
        """ _update_available_quantity may leave quants with no
        quantity and no reserved_quantity. It used to directly unlink
        these zero quants but this proved to hurt the performance as
        this method is often called in batch and each unlink invalidate
        the cache. We defer the calls to unlink in this method.
        """
        precision_digits = max(6, self.sudo().env.ref('product.decimal_product_uom').digits * 2)
        # Use a select instead of ORM search for UoM robustness.
        query = """SELECT id FROM stock_quant WHERE (round(quantity::numeric, %s) = 0 OR quantity IS NULL)
                                                            AND round(reserved_quantity::numeric, %s) = 0
                                                            AND (round(inventory_quantity::numeric, %s) = 0 OR inventory_quantity IS NULL)
                                                            AND user_id IS NULL;"""
        params = (precision_digits, precision_digits, precision_digits)
        self.env.cr.execute(query, params)
        quants = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
        quants.filtered(lambda
                            s: s.location_id != s.location_id.warehouse_id.lot_stock_id or s.not_landed_quantity == 0.0).sudo().unlink()



