from odoo import api, fields, models
from odoo.exceptions import UserError

class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    item_qty = fields.Integer(string="PLT Qty")
    driver_id = fields.Many2one('res.partner', string="Driver name")
    vehicle_id = fields.Many2one('fleet.vehicle',related="driver_id.vehicle_id",store=True)
    stock_move_id = fields.Many2one('stock.move',string="Stock Move")
    purchase_order_id = fields.Many2one("purchase.order")

    # @api.model
    # def _search(self, domain, offset=0, limit=None, order=None):
    #     if self._context.get('stock_move_id') and self._context.get('picking_id'):
    #         domain = domain.copy()
    #         domain.append((('stock_move_id', '=', self._context.get('stock_move_id'))))
    #     return super()._search(domain, offset, limit, order)

    def action_load_dispatched_picking(self):
        if self.filtered(lambda s:s.item_qty == 0):
            raise UserError('Please Set first PLT Qty')
        domain = ['|', ('result_package_id', 'in', self.ids), ('package_id', 'in', self.ids)]
        pickings = self.env['stock.move.line'].search(domain).mapped('picking_id')
        pickings.delivery_load_dispatched()



    tag_id = fields.Many2one(
        'stock.location.tag',
        string="Tag",
        compute='_compute_tag_id',
        store=True,
        readonly=False
    )

    @api.depends('location_id.tag_ids')
    def _compute_tag_id(self):
        for rec in self:
            rec.tag_id = rec.location_id.tag_ids[:1].id if rec.location_id.tag_ids else False
