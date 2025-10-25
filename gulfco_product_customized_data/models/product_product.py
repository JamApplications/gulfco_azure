from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    pallete_qty = fields.Float('PL', compute='_compute_package_qty',digits='Product Unit of Measure')
    cs_qty = fields.Float('CS', compute='_compute_package_qty', digits='Product Unit of Measure')

    @api.depends('qty_available')
    def _compute_package_qty(self):
        for record in self:
            pallete_qty = 0.0
            cs_qty  = 0.0
            if record.packaging_ids:
                pallete_package = record.packaging_ids.filtered(lambda s: s.package_type_id and s.package_type_id.is_pallete_package)
                # pallete_package = record.packaging_ids.sorted(lambda s:s.sequence)[0]
                if pallete_package:
                    pallete_package = pallete_package[0]
                    if pallete_package.qty > 0.0:
                        pallete_qty = record.qty_available / pallete_package.qty
                    if pallete_package.secondary_package:
                        if pallete_package.secondary_package.qty > 0.0:
                            cs_qty = record.qty_available / pallete_package.secondary_package.qty
            record.pallete_qty = pallete_qty
            record.cs_qty = cs_qty

    def open_packaging_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Product Packaging',
            'res_model': 'product.packaging',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
            }
        }