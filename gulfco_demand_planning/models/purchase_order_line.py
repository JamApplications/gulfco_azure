from odoo import api, fields, models, _

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def action_open_request_line_tree_view(self):
        request_line_ids = []
        for line in self:
            request_line_ids += line.purchase_request_lines.ids

        domain = [("id", "in", request_line_ids)]

        return {
            "name": _("Order Anaysis Lines"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request.line",
            "view_mode": "list,form",
            "domain": domain,
        }
