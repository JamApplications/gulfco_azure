from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        data = super()._prepare_purchase_order(picking_type,group_id,company,origin)
        if self.supplier_id and self.supplier_id.supplier_type:
            data['po_category'] = self.supplier_id.supplier_type
        return data

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        picking_type = False
        company_id = False

        for line in self.env["purchase.request.line"].browse(request_line_ids):
            if line.request_id.request_type == 'normal' and line.request_id.state == "done":
                raise UserError(_("The purchase has already been completed."))
            if line.request_id.request_type == 'normal' and line.request_id.state != "approved":
                raise UserError(
                    _("Purchase Request %s is not approved") % line.request_id.name
                )
            if line.request_id.request_type == 'order_analysis' and line.state != "approved":
                raise UserError(
                    _("Purchase Request %s is not approved") % line.request_id.name
                )
            if line.request_id.request_type == 'order_analysis' and line.state == "done":
                raise UserError(_("The purchase has already been completed."))
            if line.state == "done":
                raise UserError(_("The purchase has already been completed."))

            line_company_id = line.company_id and line.company_id.id or False
            if company_id is not False and line_company_id != company_id:
                raise UserError(_("You have to select lines from the same company."))
            else:
                company_id = line_company_id

            line_picking_type = line.request_id.picking_type_id or False
            if not line_picking_type:
                raise UserError(_("You have to enter a Picking Type."))
            if picking_type is not False and line_picking_type != picking_type:
                raise UserError(
                    _("You have to select lines from the same Picking Type.")
                )
            else:
                picking_type = line_picking_type