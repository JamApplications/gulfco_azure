from odoo import _, api, fields, models

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_packaging_qty = fields.Float(string='Packaging Quantity',related="move_id.product_packaging_qty",store=True)
    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='restrict', required=False, check_company=True,
        domain="['|', '|', ('location_id', '=', False), ('location_id', '=', location_dest_id), ('id', '=', package_id)]",
        help="If set, the operations are packed into this package")
    # result_package_id = fields.Many2one(
    #     'stock.quant.package', 'Destination Package',
    #     ondelete='restrict', required=False, check_company=True,
    #     domain="['|', '|', ('location_id', '=', False), ('location_id', '=', location_dest_id),('id', '=', package_id),('stock_move_id','=',move_id)]",
    #     help="If set, the operations are packed into this package")
    picking_purchase_order_id = fields.Many2one(
        "purchase.order",
        related='picking_id.purchase_id'
    )