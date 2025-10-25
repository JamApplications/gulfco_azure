from odoo import models, fields, api

class ASNRequestLine(models.Model):
    _inherit = 'asn.request.line'

    asn_released_qty = fields.Float(string='ASN Released Qty',compute="_compute_asn_released_qty",related=False,store=True)

    @api.depends('purchase_order_line_id.move_ids','purchase_order_line_id.move_ids.state')
    def _compute_asn_released_qty(self):
        for record in self:
            asn_released_qty = 0.0
            if record.purchase_order_line_id.move_ids:
                asn_released_qty = sum(record.purchase_order_line_id.move_ids.mapped('quantity'))
            record.asn_released_qty = asn_released_qty
