from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # excise_journal_entries_count = fields.Integer(compute="compute_excise_journal_entries_count")
    excise_move_id = fields.Many2one('account.move',string="Excise Move")

    # def button_validate(self):
    #     # try:
    #     for rec in self:
    #         partner_id = rec.partner_id.parent_id if rec.partner_id.parent_id else rec.partner_id
    #         reason = "Not specified."
    #         if partner_id and partner_id.credit_hold_reason_id:
    #             reason = partner_id.credit_hold_reason_id.name
    #         if partner_id.credit_hold_reason_id.reason == 'manual_reason':
    #             reason = str(reason) + ':\n' + self.partner_id.credit_hold_reason
    #         else:
    #             reason = reason
    #
    #         if rec.state != 'done' and rec.sale_id and rec.sale_id.partner_id.is_credit_hold and rec.sale_id.order_creation_source not in ("vansales", "presales"):
    #             if rec.is_out_type or rec.is_pack_type or rec.is_pick_type:
    #                 raise UserError(_(
    #                     "The delivery cannot be validated because the customer '%s' is currently on credit hold.\n"
    #                     "Reason: %s \n"
    #                     "Please contact the Finance or Credit Control team to proceed."
    #                 ) % (rec.sale_id.partner_id.display_name, reason))
    #     # except Exception as e:
    #     #     pass
    #     res = super().button_validate()
    #     return res