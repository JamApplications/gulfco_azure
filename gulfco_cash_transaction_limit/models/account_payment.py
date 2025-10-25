# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError, RedirectWarning
from datetime import datetime, timedelta, date



class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_pdc_receivable_bounced(self, bounce_date=fields.Date.today(),
                                      partner=False, original_payment=False,
                                      related_payments=False):
        res = super(AccountPayment, self).action_pdc_receivable_bounced(
            bounce_date=bounce_date,
            partner=partner,
            original_payment=original_payment,
            related_payments=related_payments
        )

        if self.pdc_state == 'bounced' and self.is_pdc_payment:
            partner = self.partner_id

            # Set credit hold
            partner.is_credit_hold = True

            # Assign reason from reason table
            reason = self.env['credit.hold.reason'].search([('reason', '=', 'bounced_cheque')], limit=1)
            if reason:
                partner.credit_hold_reason_id = reason.id

            # Notify users in CCD and Credit Officer groups
            group_xml_ids = [
                'gulfco_contact_registration_custom.group_ccd_approval',
                'gulfco_contact_registration_custom.group_credit_officer_approval',
            ]
            partner_ids = []
            for xml_id in group_xml_ids:
                group = self.env.ref(xml_id, raise_if_not_found=False)
                if group:
                    partner_ids += group.users.mapped('partner_id.id')

            # Remove duplicates
            partner_ids = list(set(partner_ids))

            # Post internal message on the bounced cheque
            self.message_post(
                body="The customer <b>%s</b> has a bounced cheque: <b>%s</b>." % (partner.name, self.pdc_ref or 'N/A'),
                partner_ids=partner_ids,
                subtype_xmlid='mail.mt_note'
            )

        if self.cdc_state == 'bounced' and self.is_cdc_payment:
            partner = self.partner_id

            # Set credit hold
            partner.is_credit_hold = True

            # Assign reason from reason table
            reason = self.env['credit.hold.reason'].search([('reason', '=', 'bounced_cheque')], limit=1)
            if reason:
                partner.credit_hold_reason_id = reason.id

            # Notify users in CCD and Credit Officer groups
            group_xml_ids = [
                'gulfco_contact_registration_custom.group_ccd_approval',
                'gulfco_contact_registration_custom.group_credit_officer_approval',
            ]
            partner_ids = []
            for xml_id in group_xml_ids:
                group = self.env.ref(xml_id, raise_if_not_found=False)
                if group:
                    partner_ids += group.users.mapped('partner_id.id')

            # Remove duplicates
            partner_ids = list(set(partner_ids))

            # Post internal message on the bounced cheque
            self.message_post(
                body="The customer <b>%s</b> has a bounced cheque: <b>%s</b>." % (partner.name, self.cdc_ref or 'N/A'),
                partner_ids=partner_ids,
                subtype_xmlid='mail.mt_note'
            )

        return res


    @api.onchange('due_date', 'payment_method_line_id')
    def onchange_pdc_due_date(self):
        if self.is_pdc_payment and self.pdc_state != 'collected' and self.due_date:
            if self.due_date < fields.Date.today():
                self.partner_id.is_credit_hold = True
        if self.is_cdc_payment and self.cdc_state != 'collected' and self.due_date:
            if self.due_date < fields.Date.today():
                self.partner_id.is_credit_hold = True

