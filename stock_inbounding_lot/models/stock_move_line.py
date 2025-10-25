
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    def get_remaining_qty_for_new_line(self, current_line=None):
        """Calculate remaining qty for a move, excluding a given line (e.g. the current unsaved one)."""
        self.ensure_one()

        lines = self.move_line_ids
        if current_line:
            lines = lines.filtered(lambda l: l != current_line)

        total_done = sum(lines.mapped('quantity'))
        return self.product_uom_qty - total_done



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    production_date = fields.Date(
        string='Production Date',
        help='The date when the product was produced',
    )

    internal_reference = fields.Char(
        string='Internal Lot Ref',
        compute="compute_internal_reference",
        store=True,readonly=True
    )

    expiration_days = fields.Integer(
        string='Expiration Days',
        related='product_id.expiration_time',
    )

    @api.onchange('lot_id')
    def onchange_lot_set_production_date(self):
        if self.lot_id and self.lot_id.production_date:
            self.production_date = self.lot_id.production_date
            self.expiration_date = self.lot_id.production_date + timedelta(days=self.product_id.expiration_time)


    @api.depends('expiration_date')
    def compute_internal_reference(self):
        for record in self:
            if record.expiration_date:
                record.internal_reference = record.expiration_date.strftime('%Y%m')
            else:
                record.internal_reference = False

    @api.onchange('production_date')
    def onchange_production_date(self):
        for line in self:
            if line.production_date:
                line.expiration_date = line.production_date + timedelta(days=line.product_id.expiration_time)
                lot_name = line.expiration_date.strftime('%Y%m')
                # line.internal_reference = line.expiration_date.strftime('%Y%m')
                if line.move_id and line.move_id.has_tracking != 'none' and not line.move_id.show_lots_text:
                    existing_lot = self.env['stock.lot'].search([
                                                    '|',('name','=',lot_name),('production_date', '=', line.production_date),
                                                    ('product_id', '=', line.product_id.id),
                                                    '|', ('company_id', '=', line.company_id.id), ('company_id', '=', False)
                                                ], limit=1)
                    if existing_lot:
                        line.lot_id = existing_lot.id
                    else:
                        lot = self.env['stock.lot'].create({
                            'name': lot_name,
                            'product_id': line.product_id.id,
                            'production_date': line.production_date
                        })
                        if lot:
                            line.lot_id = lot.id
                else:
                    line.lot_name = lot_name



    @api.onchange('expiration_date')
    def onchange_expiration_date(self):
        for line in self:
            if line.expiration_date:
                line.lot_name = line.expiration_date.strftime('%Y%m')

    def _prepare_new_lot_vals(self):
        vals = super()._prepare_new_lot_vals()
        vals['ref'] = self.internal_reference
        vals['production_date'] = self.production_date
        return vals

    @api.onchange('product_id', 'move_id',)
    def _onchange_product_fill_remaining_qty(self):
        if self.product_id and self.move_id and self.picking_id.picking_type_code == 'incoming':
            remaining_qty = self.move_id.get_remaining_qty_for_new_line(current_line=self)

            if remaining_qty > 0:
                self.quantity = remaining_qty
            # else:
            #     self.quantity = 0
