# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'    
    
    @api.depends('date', 'auto_post', 'origin_payment_id', 'origin_payment_id.payment_type')
    def _compute_hide_post_button(self):
        for record in self:
            base_hide_post_button = record.state != 'draft' \
                or record.auto_post != 'no' and \
                record.date and record.date > fields.Date.context_today(record)
            hide_due_to_vendor_payment = (
                record.origin_payment_id
                and record.origin_payment_id.payment_type == 'outbound'
                and record.origin_payment_id.partner_type == 'supplier'
            )
            record.hide_post_button = base_hide_post_button or hide_due_to_vendor_payment