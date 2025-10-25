from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_regenerate_invoices(self):
        """
        Action to regenerate invoices for selected sale orders
        """
        if not self:
            raise UserError(_("No sales orders selected."))

        # Call the invoice regeneration service
        regeneration_service = self.env['invoice.regeneration.service']
        return regeneration_service.regenerate_invoices(self)