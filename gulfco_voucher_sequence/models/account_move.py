# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    voucher_number = fields.Char(string="Voucher Number", copy=False)

    @api.model
    def create(self, vals):
        # assigning the sequence for the record
        if vals.get('move_type', False) in ('out_invoice','out_refund') or self.env.context.get('default_payment_type', False) == 'inbound':
            vals['voucher_number'] = self.env['ir.sequence'].next_by_code('ar.voucher.seq.code') or _('New')
        elif vals.get('move_type', False) in ('in_invoice','in_refund') or self.env.context.get('default_payment_type', False) == 'outbound':
            vals['voucher_number'] = self.env['ir.sequence'].next_by_code('ap.voucher.seq.code') or _('New')
        res = super(AccountMove, self).create(vals)
        return res

    # def action_post(self):
    #     for move in self:
    #         if not move.voucher_number:
    #             if move.move_type in ('out_invoice', 'out_refund') or self.env.context.get('default_payment_type') == 'inbound':
    #                 move.voucher_number = self.env['ir.sequence'].next_by_code('ar.voucher.seq.code') or _('New')
    #             elif move.move_type in ('in_invoice', 'in_refund') or self.env.context.get('default_payment_type') == 'outbound':
    #                 move.voucher_number = self.env['ir.sequence'].next_by_code('ap.voucher.seq.code') or _('New')
    # #
    #     return super().action_post()


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    voucher_number = fields.Char(related='move_id.voucher_number', string="Voucher Number", copy=False)

