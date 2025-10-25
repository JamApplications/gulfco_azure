from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date

import logging

_logger = logging.getLogger("============API Authenticate========")


class ResPartner(models.Model):
    _inherit = "res.partner"

    use_partner_order_limit = fields.Boolean('Order Limit', tracking=True)
    order_limit = fields.Float(string="Order Limit Amount", default=1, tracking=True)
    is_credit_hold = fields.Boolean(string="Is Credit Hold", tracking=True)
    credit_hold_reason = fields.Text(string="Describe Reason", tracking=True)
    credit_hold_reason_id = fields.Many2one(
        'credit.hold.reason',
        string='Credit Hold Reason',
        help='Reason why this customer is on credit hold.',
        tracking=True
    )
    reason = fields.Selection(related="credit_hold_reason_id.reason", tracking=True)

    is_key_account = fields.Boolean('Key account classification', default=False, copy=False, tracking=True, )

    has_overdue_warning = fields.Boolean(compute='_compute_has_overdue_warning', store=False)
    total_sales_order_count = fields.Integer(
        string="SO approved not invoiced",
        compute="_compute_total_sales_order_count", store=True
    )
    credit_remaining = fields.Float('Credit Remaining', compute="_compute_total_sales_order_count", store=True)

    @api.depends('sale_order_ids')
    def _compute_total_sales_order_count(self):
        for partner in self:
            # Filter out invoiced or cancelled orders
            filtered_orders = partner.sale_order_ids.filtered(
                lambda o: o.state in ('approved', 'sale') and not o.invoice_ids
            )
            partner.total_sales_order_count = sum(filtered_orders.mapped('amount_total'))
            credit_remaining = 0
            if partner.use_partner_credit_limit:
                credit_remaining = (partner.credit_limit - partner.credit - partner.total_sales_order_count) or 0
            partner.credit_remaining = credit_remaining

    @api.depends('invoice_ids')
    def _compute_has_overdue_warning(self):
        today = fields.Date.today()
        overdue_date = today - timedelta(days=30)
        if not self:
            return

        self.env.cr.execute("""
            SELECT partner_id
            FROM account_move
            WHERE partner_id IN %s
              AND invoice_date_due <= %s
              AND state = 'posted'
              AND payment_state != 'paid'
              AND move_type = 'out_invoice'
            GROUP BY partner_id
        """, [tuple(self.ids), overdue_date])

        overdue_partner_ids = {row[0] for row in self.env.cr.fetchall()}
        for partner in self:
            partner.has_overdue_warning = partner.id in overdue_partner_ids

    pdc_payment_count = fields.Integer(compute="_compute_payment_counts")
    cdc_payment_count = fields.Integer(compute="_compute_payment_counts")
    pdc_payment_total = fields.Float(compute="_compute_payment_counts")
    cdc_payment_total_residual = fields.Float(compute="_compute_payment_counts")
    order_on_hold = fields.Integer('Orders on Hold', compute="_compute_payment_counts", tracking=True)

    def _compute_payment_counts(self):
        # Check method overridden in gulfco_account_payment_extended module
        pass

    def action_view_pdc_payments(self):
        return {
            'name': 'PDC Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('is_pdc_payment', '=', True)],
            'context': {'default_partner_id': self.id, 'search_default_is_pdc_payment': 1},
        }

    def action_view_cdc_payments(self):
        return {
            'name': 'CDC Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('is_cdc_payment', '=', True)],
            'context': {'default_partner_id': self.id, 'search_default_is_cdc_payment': 1},
        }

    def write(self, vals):
        res = super(ResPartner, self).write(vals)

        # Check if TL expiry date is updated
        if vals.get('tl_expiry_date'):
            today = fields.Date.today()

            # Get credit hold reason record only once
            expired_reason = self.env['credit.hold.reason'].search(
                [('reason', '=', 'expired_license')], limit=1
            )

            # Load mail template and group
            ccd_group = self.env.ref('gulfco_contact_registration_custom.group_ccd_approval', raise_if_not_found=False)
            template = self.env.ref('gulfco_cash_transaction_limit.email_template_credit_hold_due_to_tl',
                                    raise_if_not_found=False)

            for partner in self:
                expired_license = partner.tl_expiry_date and partner.tl_expiry_date < today - timedelta(days=30)

                if partner.customer_type == 'credit' and expired_license:
                    partner.is_credit_hold = True

                    # Assign credit hold reason
                    if expired_reason:
                        partner.credit_hold_reason_id = expired_reason.id

                    # Notify CCD group
                    if ccd_group and template:
                        for user in ccd_group.users:
                            email_to = user.email or (user.partner_id.email or '')
                            if email_to:
                                template.send_mail(
                                    partner.id,
                                    force_send=True,
                                    email_values={
                                        'model': False,
                                        'res_id': False,
                                        'email_to': email_to,
                                    },
                                    email_layout_xmlid='mail.mail_notification_light'
                                )
        return res

    @api.onchange('tl_expiry_date')
    def _onchange_tl_expiry_date(self):
        reason = self.env['credit.hold.reason'].search([('reason', '=', 'expired_license')], limit=1)
        ccd_group = self.env.ref('gulfco_contact_registration_custom.group_ccd_approval')
        template = self.env.ref('gulfco_cash_transaction_limit.email_template_credit_hold_due_to_tl')

        for partner in self:
            expired_license = partner.tl_expiry_date and partner.tl_expiry_date < fields.Date.today() - timedelta(
                days=30)

            if partner.customer_type == 'credit' and expired_license:
                partner.is_credit_hold = True

                # Set credit hold reason
                if reason:
                    partner.credit_hold_reason_id = reason.id

                # Send email to CCD
                if template:
                    for user in ccd_group.users:
                        template.with_context(partner=partner).send_mail(
                            user.id,
                            force_send=True,
                            email_values={
                                'model': False,
                                'res_id': False,
                                'email_to': user.email or (user.partner_id.email or ''),
                            },
                            email_layout_xmlid='mail.mail_notification_light'
                        )

    def check_auto_hold_conditions(self):
        Reason = self.env['credit.hold.reason']
        today = fields.Date.today()

        for partner in self:
            selected_reason = None

            # Expired Trade License
            if partner.tl_expiry_date and partner.tl_expiry_date < (today - timedelta(days=30)):
                selected_reason = Reason.search([('reason', '=', 'expired_license')], limit=1)

            # Apply Credit Hold if needed
            if partner.customer_type == 'credit' and selected_reason and not partner.is_credit_hold:
                partner.is_credit_hold = True
                partner.credit_hold_reason_id = selected_reason.id

                # Send email notification
                ccd_group = self.env.ref('gulfco_contact_registration_custom.group_ccd_approval')
                template = self.env.ref('gulfco_cash_transaction_limit.email_template_credit_hold_due_to_overdue')
                for user in ccd_group.users:
                    template.with_context(partner=partner).send_mail(
                        partner.id,
                        force_send=True,
                        email_values={
                            'model': False,
                            'res_id': False,
                            'email_from': user.email_formatted or user.email,
                            'email_to': user.email or user.partner_id.email or '',
                        },
                        email_layout_xmlid='mail.mail_notification_light'
                    )

    cash_transaction_limit = fields.Monetary(
        string="Cash Transaction Limit",
        currency_field="currency_id",
        default=3000.0,
        help="Maximum cash transaction limit for this customer."
    )
    cash_transaction_limit_ref = fields.Monetary(related='cash_transaction_limit', readonly=1)

    show_cash_limit = fields.Boolean(compute="_compute_show_cash_limit", store=False)

    @api.depends_context()
    def _compute_show_cash_limit(self):
        config_enabled = self.env['ir.config_parameter'].sudo().get_param('account.enable_cash_transaction_limit',
                                                                          'False')
        for record in self:
            record.show_cash_limit = config_enabled == 'True'

    def get_total_outstanding_balance(self):
        _logger.info("GULFCO_TRANSACTION_LIMIT: inside get_total_outstanding_balance")
        """Calculate the total outstanding (unpaid) balance for the customer."""
        self.ensure_one()
        _logger.info("GULFCO_TRANSACTION_LIMIT: inside get_total_outstanding_balance1")
        total_unpaid = self.env["account.move"].search([
            ("partner_id", "=", self.id),
            ("state", "=", "posted"),
            ("payment_state", "!=", "paid"),
            ("move_type", "=", "out_invoice"),
        ]).mapped("amount_residual")
        _logger.info("GULFCO_TRANSACTION_LIMIT: inside get_total_outstanding_balance %s" % total_unpaid)

        return sum(total_unpaid)

    @api.onchange('is_credit_hold')
    def _onchange_credit_hold(self):
        if self.is_credit_hold:
            pass
        else:
            self.credit_hold_reason_id = None
            self.credit_hold_reason = None

    # @api.model
    # def _get_view(self, view_id=None, view_type='form', **options):
    #     arch, view = super(ResPartner, self)._get_view(view_id, view_type, **options)
    #
    #     if view_type == 'form':
    #
    #             for node in arch.xpath(
    #                     "//field[@name='is_credit_hold']"
    #             ):
    #                 if (self.env.user.has_group('gulfco_contact_registration_custom.group_credit_officer_approval')
    #                         or self.env.user.has_group('gulfco_contact_registration_custom.group_ccd_approval')):
    #                     node.set('readonly', '0')
    #                 else:
    #                     node.set('readonly', '1')
    #
    #     return arch, view

    total_due_over30 = fields.Float(
        compute="_compute_total_due_over"
    )
    total_due_over90 = fields.Float(
        compute="_compute_total_due_over"
    )

    def _compute_total_due_over(self):
        for partner in self:
            domain = partner._get_unreconciled_aml_domain()
            domain += [('account_type', '=', 'asset_receivable')]
            lines = self.env['account.move.line'].search(domain=domain)
            lines_over_30 = lines.filtered(lambda line: 30 < (fields.Date.today() - line.move_id.date).days < 90)
            lines_over_90 = lines.filtered(lambda line: 90 < (fields.Date.today() - line.move_id.date).days)
            partner.total_due_over30 = sum(lines_over_30.mapped('amount_residual'))
            partner.total_due_over90 = sum(lines_over_90.mapped('amount_residual'))
