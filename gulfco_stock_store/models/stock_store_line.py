from odoo import models, fields, api

class MerchandiseStockLines(models.Model):
    _name = 'merchandise.stock.store.lines'
    _description = 'Merchandise Stock Lines'
    _rec_name = 'store_id'

    store_id = fields.Many2one(
        'merchandise.stock.store',
        string='Store'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Item Code',
        required=True
    )
    item_name = fields.Char(
        string='Item Name',
        related='product_id.name'
    )
    qty = fields.Integer(
        string='Quantity',
    )
    uom = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
    )
    expiration_date = fields.Date(
        string='Expiration Date'
    )

    @api.onchange('product_id')
    def _onchange_product_id_id(self):
        for record in self:
            if record.product_id:
                record.uom = record.product_id.uom_id.id if record.product_id.uom_id else False