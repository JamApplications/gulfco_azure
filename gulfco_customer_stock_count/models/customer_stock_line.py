from odoo import models, fields, api


class CustomerStockLine(models.Model):
    _name = 'customer.stock.line'
    _description = 'Customer Stock Line'
    _rec_name = 'stock_id'

    stock_id = fields.Many2one('customer.stock', string='Stock Reference')
    product_id = fields.Many2one(
        'product.product',
        string='Item Code',
        required=True
    )
    item_name = fields.Char(
        string='Item Name',
        related='product_id.name'
    )
    qty = fields.Integer(string='Quantity')