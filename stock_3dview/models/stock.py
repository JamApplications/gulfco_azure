# Copyright 2020 Openindustry.it SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def threedView(self):
        return {
            "name": _("Location 3D View"),
            "type": "ir.actions.act_window",
            "customdata_request_type": "tagged",
            "view_mode": "threed",
            "res_model": "stock.location",
            "domain": [("id", "child_of", self.id)],
            "context": dict(self.env.context, request_type="tagged"),
        }

    @api.model
    def get_3d_view_item_info(self, id):
        location = self.browse(id)
        stock_quants = []
        for stock_quant in self.env["stock.quant"].search(
            [("location_id", "=", location.id)]
        ):
            stock_quants.append(
                {
                    "product_name": stock_quant.product_id.name,
                    "product_qty": stock_quant.quantity,
                    "product_code": stock_quant.product_id.default_code,
                    "product_lot": stock_quant.lot_id.name,
                }
            )

        # return {"barcode": location.barcode, "stock_quants": stock_quants}
        return {"location": location.complete_name, "barcode": location.barcode, "stock_quants": stock_quants}
