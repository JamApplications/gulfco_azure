from odoo import fields, models, api
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    media_id = fields.Many2one('account.payment.method', string="Media")

    def _compute_payment_counts(self):
        today = fields.Date.today()
        partner_ids = self.ids

        # --- PDC payments ---
        pdc_data = self.env['account.payment'].read_group(
            domain=[
                ('partner_id', 'in', partner_ids),
                ('payment_mode', '=', 'pdc'),
                ('due_date', '>=', today),
                ('state', 'not in', ['draft', 'canceled', 'rejected']),
                ('pdc_state', 'not in', ['collected']),
            ],
            fields=['partner_id', 'id:count', 'amount_company_currency_signed:sum'],
            groupby=['partner_id'],
        )
        # pdc_map = {d['partner_id'][0]: d['partner_id_count'] for d in pdc_data}
        pdc_map = {d['partner_id'][0]: [d['partner_id_count'], d['amount_company_currency_signed']] for d in pdc_data}

        # --- CDC payments ---
        # Total open payments (cash,CDC,bank transfer, pay by link,matured PDC) having residual balance.
        cdc_data = self.env['account.payment'].read_group(
            domain=[
                ('partner_id', 'in', partner_ids),
                ('state', 'not in', ['draft', 'canceled', 'rejected']),
                ('payment_amount_residual', '!=', 0),  # still open
                '|',
                '&', ('payment_mode', '=', 'cdc'), ('cdc_state', 'not in', ['collected']),
                ('payment_mode', 'not in', ['pdc', 'cdc']),
            ],
            fields=['partner_id', 'id:count', 'payment_amount_residual:sum'],
            groupby=['partner_id'],
        )
        # cdc_data = self.env['account.payment'].read_group(
        #     domain=[
        #         ('partner_id', 'in', partner_ids),
        #         ('is_cdc_payment', '=', True),
        #         ('due_date', '<=', today),
        #         ('state', 'not in', ['draft', 'canceled', 'rejected']),
        #         ('cdc_state', 'not in', ['collected']),
        #     ],
        #     fields=['partner_id', 'id:count'],
        #     groupby=['partner_id'],
        # )
        # cdc_map = {d['partner_id'][0]: d['partner_id_count'] for d in cdc_data}
        cdc_map = {d['partner_id'][0]: [d['partner_id_count'], abs(d['payment_amount_residual'])] for d in cdc_data}

        # --- Sale Orders On Hold ---
        so_data = self.env['sale.order'].read_group(
            domain=[
                ('partner_id', 'in', partner_ids),
                ('state', 'in', ['awaiting_credit_approval']),
            ],
            fields=['partner_id', 'id:count'],
            groupby=['partner_id'],
        )
        so_map = {d['partner_id'][0]: d['partner_id_count'] for d in so_data}

        for partner in self:
            partner.pdc_payment_count = pdc_map.get(partner.id, 0) and pdc_map.get(partner.id, 0)[0] or 0
            partner.cdc_payment_count = cdc_map.get(partner.id, 0) and cdc_map.get(partner.id, 0)[0] or 0
            partner.pdc_payment_total = pdc_map.get(partner.id, 0) and pdc_map.get(partner.id, 0)[1] or 0
            partner.cdc_payment_total_residual = cdc_map.get(partner.id, 0) and cdc_map.get(partner.id, 0)[1] or 0
            partner.order_on_hold = so_map.get(partner.id, 0)

        # for partner in self:
        #     partner.pdc_payment_count = self.env['account.payment'].search_count([
        #         ('partner_id', '=', partner.id),
        #         ('is_pdc_payment', '=', True),
        #         ('due_date', '>', fields.Date.today()),
        #         ('state', 'not in', ['draft', 'canceled', 'rejected']),
        #         ('pdc_state', 'not in', ['collected']),
        #     ])
        #     partner.cdc_payment_count = self.env['account.payment'].search_count([
        #         ('partner_id', '=', partner.id),
        #         ('is_cdc_payment', '=', True),
        #         ('due_date', '<=', fields.Date.today()),
        #         ('state', 'not in', ['draft','canceled', 'rejected']),
        #         ('cdc_state', 'not in', ['collected'])
        #     ])
        #     # partner.cdc_payment_count += self.env['account.payment'].search_count([
        #     #     ('partner_id', '=', partner.id),
        #     #     ('due_date', '<=', fields.Date.today()),
        #     #     ('is_pdc_payment', '=', True),
        #     #     ('state', 'not in', ['canceled', 'rejected'])
        #     # ])

        #     order_on_hold = self.env['sale.order'].search([('partner_id', '=', partner.id),('state', 'in', ['awaiting_credit_approval'])])
        #     partner.order_on_hold = len(order_on_hold) or 0

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.context.get(
                'is_vendor_payment') or 'res_partner_search_mode' in self.env.context and self.env.context.get(
                'res_partner_search_mode') == 'supplier':
            for d in domain:
                if isinstance(d, (list, tuple)) and d[0] in ['name', 'display_name'] and d[1] in ('ilike', 'like', '='):
                    # Add OR condition for 'vendor_code'
                    domain = expression.OR([
                        domain or [],
                        [('vendor_code', d[1], d[2])],
                    ])
                    break
        return super(ResPartner, self).search_fetch(domain=domain, field_names=field_names, offset=offset, limit=limit,
                                                    order=order)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []

        domain += [('vendor_code', operator, name)]

        return super(ResPartner, self)._name_search(name=name, domain=domain, operator=operator, limit=limit,
                                                    order=order)

    def _cron_uncovered_monthly_pdc_hold_check(self):
        Reason = self.env['credit.hold.reason']
        today = fields.Date.today()
        all_monthly_pdc_customers = self.search([('media_id', '!=', False),
                                                 ('media_id.is_monthly_pdc', '=', True),
                                                 ('customer_type', '=', 'credit'),
                                                 ('is_credit_hold', '=', False)])

        if not all_monthly_pdc_customers:
            return

        # PDC Not Collected
        overdue_pdc = self.env['account.payment'].read_group(
            domain=[
                ('partner_id', 'in', all_monthly_pdc_customers.ids),
                ('payment_mode', '=', 'pdc'),
                ('payment_type', '=', 'inbound'),
                ('pdc_state', '!=', 'collected'),
                ('due_date', '<', today)
            ],
            fields=['partner_id'],
            groupby=['partner_id'],
        )
        partner_has_overdue_pdc = {rec['partner_id'][0] for rec in overdue_pdc}

        not_overdue_partners = set(all_monthly_pdc_customers.ids) - partner_has_overdue_pdc
        invoice_lines = self.env['account.move.line']
        if not_overdue_partners:
            invoice_lines = self.env['account.move.line'].search([
                ('partner_id', 'in', list(not_overdue_partners)),
                ('move_id.move_type', '=', 'out_invoice'),
                ('parent_state', '=', 'posted'),
                ('move_id.uncovered_balance', '>', 0),
            ])

        lines_by_partner = {}
        for line in invoice_lines:
            if not line.partner_id.id in lines_by_partner:
                lines_by_partner[line.partner_id.id] = line
            else:
                lines_by_partner[line.partner_id.id] |= line

        reason_uncollected = Reason.search([('reason', '=', 'uncollected_pdc')], limit=1)
        reason_uncovered = Reason.search([('reason', '=', 'uncovered_invoice')], limit=1)
        ccd_group = self.env.ref('gulfco_contact_registration_custom.group_ccd_approval')
        template = self.env.ref('gulfco_cash_transaction_limit.email_template_credit_hold_due_to_overdue')

        for partner in all_monthly_pdc_customers:
            selected_reason = None

            # PDC Not Collected
            if partner.id in partner_has_overdue_pdc:
                selected_reason = reason_uncollected

            # Invoices not covered by any PDC payment
            if not selected_reason:
                # invoice_lines = self.env['account.move.line'].search([
                #     ('partner_id', '=', partner.id),
                #     ('move_id.move_type', '=', 'out_invoice'),
                #     ('parent_state', '=', 'posted'),
                #     ('move_id.uncovered_balance', '>', 0),
                # ])
                invoice_lines = lines_by_partner.get(partner.id, self.env['account.move.line'])

                for line in invoice_lines:
                    related_credits = (line.matched_credit_ids.credit_move_id
                                       .filtered(lambda l: l.payment_id and
                                                           l.payment_id.payment_mode == 'pdc' and
                                                           l.payment_id.payment_type == 'inbound'))

                    if not related_credits:
                        reconciled_partials = line.move_id.sudo()._get_all_reconciled_invoice_partials()
                        for partial in reconciled_partials:
                            aml = partial.get('aml', False)
                            if aml:
                                related_credits |= aml.filtered(lambda
                                                                    l: l.payment_id and l.payment_id.payment_mode == 'pdc' and l.payment_id.payment_type == 'inbound')
                                if related_credits:
                                    break

                    if not related_credits:
                        # This invoice is not linked with any PDC inbound payment
                        selected_reason = reason_uncovered
                        break

            # Apply Credit Hold if needed
            if selected_reason:
                partner.is_credit_hold = True
                partner.credit_hold_reason_id = selected_reason.id

                # Send email notification
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