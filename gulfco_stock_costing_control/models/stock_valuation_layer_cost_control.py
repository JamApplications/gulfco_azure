# -*- coding: utf-8 -*-

from odoo import models, api, fields, _


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    is_deferred_costing = fields.Boolean(
        "Deferred Costing",
        default=False,
        help="This stock valuation layer is deferred and does not impact product valuation or accounting entries until the related landed cost is validated.",
    )