# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class accountpayment(models.Model):
    _inherit = 'account.payment'

    sequence_custom = fields.Char(string="Payment Seq",default="New",copy=False,readonly=False, required=True)

    @api.model
    def create(self, vals):
        if not self.env.context.get('default_is_internal_transfer', False):
            if vals.get('payment_type'):
                if vals['payment_type'] == 'outbound':
                    vals['sequence_custom'] = self.env['ir.sequence'].next_by_code('send.account.payment')
                else:
                    vals['sequence_custom'] = self.env['ir.sequence'].next_by_code('receive.account.payment')
        else:
            vals['sequence_custom'] = self.env['ir.sequence'].next_by_code('internal.transfer.account.payment')
        return super(accountpayment, self).create(vals)


