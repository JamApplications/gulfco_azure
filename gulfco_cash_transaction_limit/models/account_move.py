# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date



class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(selection_add=[('waiting_for_release', 'Request to Release'),('awaiting_credit_approval', 'Awaiting Credit Approval')],
                             ondelete={'awaiting_credit_approval': 'cascade', 'waiting_for_release': 'cascade'})
    credit_override_requested = fields.Boolean('Credit Override Requested', copy=False)
    order_limit_requested = fields.Boolean('Order Limit Requested', copy=False)

    def action_approve_credit_override_move(self):
        for move in self:
            move.write({
                # 'state': 'posted',
                'credit_override_requested': True
            })
            if move:
                move.action_post()

    def action_reject_credit_override_move(self):
        self.write({'state': 'draft'})


    @api.onchange('partner_id')
    def _onchange_is_credit_hold(self):
        if self.partner_id.is_credit_hold and not self.partner_id.is_key_account:
            reason = "Not specified."
            if self.partner_id and self.partner_id.credit_hold_reason_id:
                reason = self.partner_id.credit_hold_reason_id.name
            if self.partner_id.credit_hold_reason_id.reason == 'manual_reason':
                reason = str(reason) + ':\n' + self.partner_id.credit_hold_reason
            else:
                reason = reason

            self.partner_id = None
            return {
                'warning': {
                    'title': "Credit Hold Warning",
                    'message': "This Customer is on credit hold.\n\nReason: %s" % (
                        reason),
                }
            }

    def action_post(self):
        # res = super(AccountMove, self).action_post()
        for move in self:
            if move.move_type == "out_invoice" and move.partner_id:
                partner_id = move.partner_id.parent_id if move.partner_id.parent_id else move.partner_id
                outstanding_balance = partner_id.get_total_outstanding_balance()
                new_invoice_total = move.amount_total
                total_after = outstanding_balance + new_invoice_total
                credit_limit = partner_id.credit_limit

                sale_order = self.env['sale.order'].sudo().search([("invoice_ids", "in" , [move.id])], limit=1)
                #
                if sale_order and sale_order.order_creation_source in ["vansales", "presales"]:
                    continue
                # elif partner_id.is_credit_hold and partner_id.customer_type == 'credit':
                #     raise UserError(_('Customer is on Credit Hold. Approval required.'))


                # Check overdue invoices
                # overdue_invoices = self.search_count([
                #     ('partner_id', '=', partner_id.id),
                #     ('invoice_date_due', '<', fields.Date.today() - timedelta(days=30)),
                #     ('state', '=', 'posted'),
                #     ('status_in_payment', '!=', 'paid'),
                #     ('move_type', '=', 'out_invoice'),
                # ])
                #
                # # Trigger credit hold
                # if partner_id.customer_type == 'credit' and partner_id.use_partner_credit_limit and not move.partner_id.is_key_account:
                #
                #     if partner_id.use_partner_order_limit and move.amount_total > partner_id.order_limit:
                #         if not move.order_limit_requested:
                #             move.write({
                #                 'order_limit_requested': True,
                #                 'state': 'waiting_for_release'
                #             })
                #             return move

                    # not overdue_invoices:
                    # partner_id.is_credit_hold = True

                    # # Set credit hold reason
                    # reason_key = 'overdue_invoice' if overdue_invoices else 'manual_reason'
                    # reason = self.env['credit.hold.reason'].search([('reason', '=', reason_key)], limit=1)
                    # if reason:
                    #     partner_id.credit_hold_reason_id = reason.id

                    # CCD users warning only (if not Credit Officer)
                    # if self.env.user.has_group('gulfco_contact_registration_custom.group_ccd_approval') and not \
                    #         self.env.user.has_group('gulfco_contact_registration_custom.group_credit_officer_approval'):
                    #     raise ValidationError(_(
                    #         "Transaction exceeds the Credit limit for this customer. "
                    #         "Please adjust the limit on customer."
                    #     ))
                    #
                    # # Credit override requested handling
                    # if partner_id.credit_remaining <= 0 and not move.credit_override_requested:
                    #     move.write({
                    #         'state': 'awaiting_credit_approval',
                    #         'credit_override_requested': True,
                    #     })
                    #     return move
                    #
                    # if not move.credit_override_requested and total_after > credit_limit:
                    #     move.write({
                    #         'state': 'awaiting_credit_approval',
                    #         'credit_override_requested': True,
                    #     })
                    #
                    #     # Notify approval groups
                    #     group_xml_ids = [
                    #         'gulfco_contact_registration_custom.group_ccd_approval',
                    #         'gulfco_contact_registration_custom.group_credit_officer_approval',
                    #     ]
                    #     partner_ids = []
                    #     for xml_id in group_xml_ids:
                    #         group = self.env.ref(xml_id, raise_if_not_found=False)
                    #         if group:
                    #             partner_ids += group.users.mapped('partner_id.id')
                    #     partner_ids = list(set(partner_ids))
                    #
                    #     move.message_post(
                    #         body="Credit override required.",
                    #         partner_ids=partner_ids,
                    #     )
                    #     return move  # Stop confirmation

                # Cash customer cash transaction limit
                if move.partner_id.parent_id:
                    limit = move.partner_id.parent_id.cash_transaction_limit
                    config_enabled_cash_limit = move.partner_id.parent_id.show_cash_limit
                else:
                    limit = move.partner_id.cash_transaction_limit
                    config_enabled_cash_limit = move.partner_id.show_cash_limit

                if sale_order and sale_order.order_creation_source in ["vansales", "presales"]:
                    continue
                elif partner_id.customer_type == 'cash' and config_enabled_cash_limit and limit and total_after > limit:
                    raise ValidationError(_(
                        "Transaction exceeds the cash limit for this customer. "
                        "Please collect payment or adjust the order."
                    ))

        return super(AccountMove, self).action_post()


    def action_approve_order_limit(self):
        for move in self:
            move.write({
                'order_limit_requested': True
            })
            move.action_post()
