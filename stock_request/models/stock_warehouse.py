# Copyright 2018 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    van_load_route_id = fields.Many2one("stock.route")
    van_offload_route_id = fields.Many2one("stock.route")

    @api.constrains("company_id")
    def _check_company_stock_request(self):
        if any(
            self.env["stock.request"].search(
                [
                    ("company_id", "!=", rec.company_id.id),
                    ("warehouse_id", "=", rec.id),
                ],
                limit=1,
            )
            for rec in self
        ):
            raise ValidationError(
                _(
                    "You cannot change the company of the warehouse, as it is "
                    "already assigned to stock requests that belong to "
                    "another company."
                )
            )
        if any(
            self.env["stock.request.order"].search(
                [
                    ("company_id", "!=", rec.company_id.id),
                    ("warehouse_id", "=", rec.id),
                ],
                limit=1,
            )
            for rec in self
        ):
            raise ValidationError(
                _(
                    "You cannot change the company of the warehouse, as it is "
                    "already assigned to stock request orders that belong to "
                    "another company."
                )
            )
