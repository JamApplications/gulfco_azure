from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        if self.product_template_id:
            package_ids = self.product_template_id.packaging_ids.filtered(lambda x:x.barcode and self.product_template_id.search_string and self.product_template_id.search_string.lower() in x.barcode.lower())
            if package_ids:
                self.product_packaging_id  = package_ids[0] if package_ids else False
                self.product_packaging_qty  = self.product_packaging_id.qty
                self.product_uom_qty = self.product_packaging_qty
                self.product_uom = self.product_packaging_id.product_uom_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            package_ids = self.product_id.packaging_ids.filtered(
                lambda x: x.barcode and self.product_id.product_tmpl_id.search_string and self.product_id.product_tmpl_id.search_string.lower() in x.barcode.lower())
            if package_ids:
                self.product_packaging_id = package_ids[0].id if package_ids else False
                self.product_packaging_qty = self.product_packaging_id.qty
                self.product_uom_qty = self.product_packaging_qty
                self.product_uom = self.product_packaging_id.product_uom_id
