from odoo import models, fields, api

class DisplayAreaLines(models.Model):
    _name = 'display.area.lines'
    _description = 'Display Area Lines'

    display_id = fields.Many2one('shelf.display', string='Shelf Display')
    customer_id = fields.Many2one('res.partner', string='Shelf Display',related="display_id.customer_id")
    display_area_id = fields.Many2one('display.area', string='Shelf Display',related="display_id.display_area_id")

    product_id = fields.Many2one('product.product', string='Item Code')
    item_name = fields.Char(string='Item Name', related='product_id.name')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='UOM')
    old_qty = fields.Integer(string='Old Quantity', compute='_compute_old_qty',store=True)
    current_qty = fields.Integer(string='Current Quantity')

    @api.depends('product_id', 'display_id')
    def _compute_old_qty(self):
        for record in self:
            # Fetch the old quantity based on the last recorded data for the same customer and display area
            previous_record = self.env['display.area.lines'].sudo().search([
                ('customer_id', '=', record.display_id.customer_id.id),
                ('display_area_id', '=', record.display_id.display_area_id.id),
                ('product_id', '=', record.product_id.id),
                ('id', '!=', record.id)
            ], order='id desc', limit=1)
            record.old_qty = previous_record.current_qty if previous_record else 0
