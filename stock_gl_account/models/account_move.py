from odoo import fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    gl_stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Picking',
    )