from odoo import api, fields, models, _
from odoo.exceptions import UserError


class QuantDataFixWizard(models.TransientModel):
    _name = "quant.data.fix.wizard"
    _description = "Quant Data Fix Wizard"

    quant_id = fields.Many2one(
        "stock.quant",
        string="Quant",
        required=True,
        help="Select the quant record you want to update."
    )
    quantity_to_update = fields.Float(
        string="New Quantity",
        required=True,
        help="Enter the new quantity value for this quant."
    )
    update_reserved_qty = fields.Boolean(
        string="Update Reserved Quantity?",
        help="Check to also update the reserved quantity."
    )
    reserved_qty_to_update = fields.Float(
        string="New Reserved Quantity",
        help="Enter the new reserved quantity value (if applicable)."
    )

    @api.onchange('update_reserved_qty')
    def _onchange_update_reserved_qty(self):
        if not self.update_reserved_qty:
            self.reserved_qty_to_update = 0.0

    def action_update_quant(self):
        """Update quant quantity and optionally reserved quantity"""
        self.ensure_one()
        quant = self.quant_id.sudo()

        if not quant:
            raise UserError(_("Quant record not found."))

        original_qty = quant.quantity
        original_reserved_qty = quant.reserved_quantity
        # Update quantity
        quant.write({"quantity": self.quantity_to_update})

        # Optionally update reserved qty
        if self.update_reserved_qty:
            quant.write({"reserved_quantity": self.reserved_qty_to_update})

        msg = _(f"The quant values were successfully updated.\n• Original Qty: {original_qty} |  New Quantity: {self.quantity_to_update}")
        if self.update_reserved_qty:
            msg += _(f"• Original Reserved Qty: {original_reserved_qty} | New Reserved Quantity: {self.reserved_qty_to_update}")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Quant Updated"),
                "message": msg,
                "sticky": False,
                "type": "success",
            },
        }
