# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    assign_to = fields.Many2one('res.partner',  string="Assign To", domain="[('contact_type', '=', 'worker')]",
                                default=lambda self: self.env.user.partner_id.id)

    @api.depends('move_type', 'partner_id')
    def _compute_invoice_default_sale_person(self):
        # We want to modify the sale person only when we don't have one and if the move type corresponds to this condition
        # If the move doesn't correspond, we remove the sale person
        for move in self:
            if move.is_sale_document(include_receipts=True):
                if move.partner_id:
                    move.invoice_user_id = (
                            move.invoice_user_id
                            or move.partner_id.user_id
                            or move.partner_id.commercial_partner_id.user_id
                            or self.env.user
                    )
                    move.assign_to = move.invoice_user_id.partner_id.id
            else:
                move.invoice_user_id = False
