# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection_add=[('waiting_for_release', 'Request to Release'),('awaiting_credit_approval', 'Awaiting Credit Approval')],
                             ondelete={'awaiting_credit_approval': 'cascade', 'waiting_for_realese': 'cascade'})
    credit_override_requested = fields.Boolean('Credit Override Requested', copy=False)
    order_limit_requested = fields.Boolean('Order Limit Requested', copy=False)

    overdue_warning_message = fields.Char(compute='_compute_overdue_warning', store=True)
    
    total_sales_order_count = fields.Integer(
        related = 'partner_id.total_sales_order_count', store=True
    )

    partner_credit_limit = fields.Float(
        related='partner_id.credit_limit'
    )
    partner_outstanding = fields.Monetary(
        related='partner_id.credit'
    )
    partner_code = fields.Char(
        related='partner_id.customer_code'
    )
    partner_pdc_payment_count = fields.Integer(
        related='partner_id.pdc_payment_count'
    )
    partner_tl_expiry_date = fields.Date(
        related='partner_id.tl_expiry_date'
    )
    partner_class_id = fields.Many2one(
        'customer.class',related='partner_id.customer_class_id'
    )
    partner_is_credit_hold = fields.Boolean(
        related='partner_id.is_credit_hold'
    )
    partner_total_due_over30 = fields.Float(
        related='partner_id.total_due_over30'
    )
    partner_total_due_over90 = fields.Float(
        related='partner_id.total_due_over90'
    )
    @api.depends('partner_id')
    def _compute_overdue_warning(self):
        for order in self:
            if order.partner_id.has_overdue_warning:
                order.overdue_warning_message = _(
                    "%s has overdue invoices older than 30 days. Please review credit status."
                ) % order.partner_id.name
            # elif order.partner_id.credit_remaining <= 0:
            #     order.overdue_warning_message = _(
            #         "%s not have the Credit. Please review Credit Remaining."
            #     ) % order.partner_id.name
            else:
                order.overdue_warning_message = False

    @api.onchange('partner_id')
    def _onchange_is_credit_hold(self):
        if self.partner_id.is_credit_hold and self.order_creation_source != 'vansales' and not self.partner_id.is_key_account:
            reason = "Not specified."
            if self.partner_id and self.partner_id.credit_hold_reason_id:
                reason = self.partner_id.credit_hold_reason_id.name

            if self.partner_id.credit_hold_reason_id.reason =='manual_reason':
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

    def action_confirm(self):
        for order in self:
            if order.partner_id:

                if order.partner_id.customer_type == 'credit' and order.order_creation_source != 'vansales' and not order.partner_id.is_key_account:
                    if order.partner_id.use_partner_order_limit and order.amount_total > order.partner_id.order_limit:
                        if not order.order_limit_requested:
                            order.write({
                                'order_limit_requested': True,
                                'state': 'waiting_for_release'
                            })
                            return order

                    if order.partner_id.is_credit_hold and order.order_creation_source != 'vansales':
                        raise UserError(_('Customer is on Credit Hold. Approval required.'))

                    if order.partner_id.credit_remaining <= 0 and not order.credit_override_requested:
                        order.write({
                            'state': 'awaiting_credit_approval',
                            'credit_override_requested': True,
                        })
                        return order
                    receivables = order.partner_id.credit
                    total_after = receivables + order.amount_total
                    credit_limit = order.partner_id.credit_limit

                    # overdue_invoices = self.env['account.move'].search_count([
                    #     ('partner_id', '=', order.partner_id.id),
                    #     ('invoice_date_due', '<', fields.Date.today() - timedelta(days=30)),
                    #     ('state', '=', 'posted'),
                    #     ('payment_state', '!=', 'paid'),
                    #     ('move_type', '=', 'out_invoice'),
                    # ])
                    date_threshold = fields.Date.today() - timedelta(days=30)
                    query = """
                        SELECT COUNT(*)
                        FROM account_move
                        WHERE partner_id = %s
                          AND invoice_date_due < %s
                          AND state = 'posted'
                          AND payment_state != 'paid'
                          AND move_type = 'out_invoice'
                    """
                    self.env.cr.execute(query, (order.partner_id.id, date_threshold))
                    overdue_invoices = self.env.cr.fetchone()[0]

                    if total_after > credit_limit:
                        # if overdue_invoices:
                        #     raise ValidationError(_(
                        #         "This customer has overdue invoices and is on credit hold.\n"
                        #         "Please review the customer's outstanding invoices or adjust the credit limit before proceeding."
                        #     ))
                        if self.env.user.has_group('gulfco_contact_registration_custom.group_ccd_approval') and not self.env.user.has_group('gulfco_contact_registration_custom.group_credit_officer_approval'):
                            raise ValidationError(_(
                                "Transaction exceeds the Credit limit for this customer. "
                                "Please adjust the limit on customer."
                            ))
                        if not order.credit_override_requested:

                            order.write({
                                'state': 'awaiting_credit_approval',
                                'credit_override_requested': True,
                            })

                            group_xml_ids = [
                                'gulfco_contact_registration_custom.group_ccd_approval',
                                'gulfco_contact_registration_custom.group_credit_officer_approval',
                            ]

                            partner_ids = []
                            for xml_id in group_xml_ids:
                                group = self.env.ref(xml_id)
                                partner_ids += group.users.mapped('partner_id.id')

                            partner_ids = list(set(partner_ids))

                            order.message_post(
                                body="Credit override required.",
                                partner_ids=partner_ids,
                            )
                            return  order# Block confirm
                    elif overdue_invoices:
                        if self.env.user.has_group('gulfco_contact_registration_custom.group_ccd_approval') and not self.env.user.has_group('gulfco_contact_registration_custom.group_credit_officer_approval'):
                            raise ValidationError(_(
                                "This customer has overdue invoices.\n"
                                "Please review the customer's outstanding invoices or approval the order before proceeding."
                            ))

                        if not order.credit_override_requested:

                            order.write({
                                'state': 'awaiting_credit_approval',
                                'credit_override_requested': True,
                            })

                            group_xml_ids = [
                                'gulfco_contact_registration_custom.group_ccd_approval',
                                'gulfco_contact_registration_custom.group_credit_officer_approval',
                            ]

                            partner_ids = []
                            for xml_id in group_xml_ids:
                                group = self.env.ref(xml_id)
                                partner_ids += group.users.mapped('partner_id.id')

                            partner_ids = list(set(partner_ids))

                            order.message_post(
                                body="Credit override required.",
                                partner_ids=partner_ids,
                            )
                            return order  # Block confirm


                outstanding_balance = order.partner_id.get_total_outstanding_balance()
                new_order_total = order.amount_total
                limit = order.partner_id.cash_transaction_limit
                config_enabled_cash_limit = order.partner_id.show_cash_limit

                if order.partner_id.customer_type == 'cash' and config_enabled_cash_limit and limit and outstanding_balance + new_order_total > limit:
                    raise ValidationError(_(
                        "Transaction exceeds the cash limit for this customer. "
                        "Please collect payment or adjust the order."
                    ))

        return super(SaleOrder, self).action_confirm()

    def action_approve_credit_override(self):
        for order in self:
            if order.state == 'awaiting_credit_approval':
                order.write({
                    'state': 'sale',
                    'credit_override_requested': False
                })
                order._action_confirm()

    def action_reject_credit_override(self):
        self.write({'state': 'cancel'})

    def action_approve_order_limit(self):
        for order in self:
            if order.state == 'waiting_for_release':
                order.write({
                    'state': 'sale',
                    'order_limit_requested': False
                })
                order._action_confirm()
