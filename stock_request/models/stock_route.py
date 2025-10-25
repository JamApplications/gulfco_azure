# Copyright 2018 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# from dataclasses import fields

from odoo import _, api, models,fields
from odoo.exceptions import ValidationError


class StockRoute(models.Model):
    _inherit = "stock.route"

    is_delivery_route = fields.Boolean(string="Is Delivery Route")
    is_receive_route = fields.Boolean(string="Is Receive Route")

    @api.constrains("company_id")
    def _check_company_stock_request(self):
        if any(
            rec.company_id
            and self.env["stock.request"].search(
                [("company_id", "!=", rec.company_id.id), ("route_id", "=", rec.id)],
                limit=1,
            )
            for rec in self
        ):
            raise ValidationError(
                _(
                    "You cannot change the company of the route, as it is "
                    "already assigned to stock requests that belong to "
                    "another company."
                )
            )
