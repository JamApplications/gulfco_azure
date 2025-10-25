from odoo import _, api, fields, models

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity, reserved_quant)
        if reserved_quant and reserved_quant.lot_id and reserved_quant.lot_id.production_date:
            vals['production_date'] = reserved_quant.lot_id.production_date
        if self.move_orig_ids and self.move_orig_ids.move_line_ids:
            move_line = self.move_orig_ids.move_line_ids.filtered(lambda s:s.product_id == self.product_id)
            if move_line:

                vals['production_date'] = move_line[0].production_date
        return vals