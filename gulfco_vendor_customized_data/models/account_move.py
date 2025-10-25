from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"
    
    vendor_code = fields.Char(related="partner_id.vendor_code", store=True)

    @api.constrains("ref", "move_type")
    def _check_unique_vendor_bill_ref(self):
        for rec in self:
            if rec.move_type == "in_invoice" and rec.ref:
                existing_bill = self.search(
                    [
                        ("id", "!=", rec.id),
                        ("move_type", "=", "in_invoice"),
                        ("partner_id", "=", rec.partner_id.id),
                        ("ref", "=", rec.ref),
                    ],
                    limit=1,
                )
                if existing_bill:
                    raise ValidationError(
                        _(f"This Bill Reference already exists for a bill: {existing_bill.name}. Please enter a unique reference.")
                    )