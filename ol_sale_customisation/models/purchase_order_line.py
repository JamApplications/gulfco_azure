from odoo import fields, models, api, _
from odoo.exceptions import UserError

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            package_ids = self.product_id.packaging_ids.filtered(
                lambda x: x.barcode and self.product_id.search_string and self.product_id.search_string.lower() in x.barcode.lower())
            self.product_packaging_id = package_ids[0].id if package_ids else False