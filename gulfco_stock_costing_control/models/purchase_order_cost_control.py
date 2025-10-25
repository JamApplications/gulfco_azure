from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    enable_costing = fields.Boolean(string="Enable Costing", default=False, readonly=False, copy=False)

    @api.constrains('po_category', 'enable_costing')
    def _check_enable_costing_for_lpo(self):
        for record in self:
            if record.po_category == 'local' and record.enable_costing:
                raise UserError("Enable Costing cannot be checked when PO Category is LPO.")

    @api.onchange('po_category')
    def onchange_po_category(self):
        if self.po_category != 'foreign':
            self.enable_costing = False

    @api.onchange('enable_costing')
    def _onchange_enable_costing(self):
        if not self.enable_costing:
            self.picking_ids.write({'enable_costing': False})
