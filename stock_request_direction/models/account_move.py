from odoo import _, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_request_order_id = fields.Many2one(
        comodel_name='stock.request.order',
        copy=False,
    )