from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentCdcBounce(models.TransientModel):
    _name = 'account.payment.cdc.bounce'
    _description = 'Account Payment CDC Receivable Bounce Wizard'

    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='CDC',
    )
    payment_ids = fields.Many2many(
        relation= "rel_account_payment_account_payment_cdc_bounce_wizard",
        comodel_name='account.payment',
        string='CDC Payments',
    )
    bounce_date = fields.Date(
        default=fields.Date.context_today,
    )
    cancel_id = fields.Many2one('cheque.cancel.reason', string="Reason")
    payment_ref = fields.Char(
        string='CDC',
        related='payment_id.memo',
    )
    payment_cdc_state = fields.Selection(
        related='payment_id.cdc_state',
    )

    allow_merge_cdc = fields.Boolean(
        string='Allow Merge CDC'
    )
    allowed_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        compute='_compute_allowed_partner'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Assign To',
    )
    related_payment_ids = fields.Many2many(
        comodel_name='account.payment',
        string='Related CDC',
        domain="[('id', '!=', payment_id),"
               "('cdc_state', '=', payment_cdc_state)]",
    )

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentCdcBounce, self).default_get(fields)
        if 'active_ids' in self.env.context and len(self.env.context.get('active_ids')) > 1:
            payment_ids = self.env['account.payment'].browse(
                self.env.context['active_ids'])
            res['payment_ids'] = payment_ids.ids
        elif 'active_id' in self.env.context and self.env.context.get(
                'active_model') == 'account.payment':
            payment = self.env['account.payment'].browse(
                self.env.context['active_id'])
            related_payments = self.env['account.payment'].search([
                ('id', '!=', payment.id),
                ('cdc_state', '=', payment.cdc_state),
                ('memo', '=', payment.memo),
                ('company_id', '=', payment.company_id.id),
            ])
            res['payment_id'] = payment.id
            res['partner_id'] = payment.partner_id.id
            if related_payments:
                res['allow_merge_cdc'] = True
                # res['related_payment_ids'] = [(6, 0, related_payments.ids)]
        return res

    @api.depends('related_payment_ids', 'payment_id')
    def _compute_allowed_partner(self):
        """
        get all partners can be assigned
        """
        for record in self:
            partners = record.payment_id.partner_id
            for line in record.related_payment_ids:
                partners |= line.partner_id
            record.allowed_partner_ids = partners

    @api.onchange('allow_merge_cdc')
    def _onchange_allow_merge_cdc(self):
        """
        reset data
        """
        if not self.allow_merge_cdc:
            self.partner_id = self.payment_id.partner_id
            self.allowed_partner_ids = False
        else:
            pass
            # related_payments = self.env['account.payment'].search([
                # ('id', '!=', self.payment_id.id),
                # ('cdc_state', '=', self.payment_id.cdc_state),
                # ('memo', '=', self.payment_id.memo),
                # ('company_id', '=', self.payment_id.company_id.id),
            # ])
            # self.related_payment_ids = related_payments

    def action_bounce_cdc(self):
        """ bounce cdc receivable """
        if self.payment_ids and len(self.payment_ids) > 1:
            for payment in self.payment_ids:
                payment.action_cdc_receivable_bounced(
                    partner=payment.partner_id,
                    original_payment=payment,
                    bounce_date=self.bounce_date
                )
        else:
            payment = self.payment_id
            if self.related_payment_ids and self.allow_merge_cdc:
                related_pay_journals = self.related_payment_ids.mapped('journal_id')
                if len(related_pay_journals) > 1:
                    raise ValidationError(_('Related CDC must have same journal'))
                if related_pay_journals != self.payment_id.journal_id:
                    raise ValidationError(_('Related CDC must have journal %s')
                                        % self.payment_id.journal_id.display_name)
                related_pay_state = self.related_payment_ids.mapped('cdc_state')

                if related_pay_state[0] != self.payment_id.cdc_state:
                    raise ValidationError(_('Related CDC must has same '
                                            'status as payment %s')
                                        % self.payment_id.display_name)
                related_deposit_journals = self.related_payment_ids.mapped('deposit_cdc_id.bank_journal_id')
                if len(related_deposit_journals) > 1:
                    raise ValidationError(_('Related CDC must has same deposit bank'))
                if related_deposit_journals[0] != self.payment_id.deposit_cdc_id.bank_journal_id:
                    raise ValidationError(_('Related CDC must has same deposit bank %s')
                                        % self.payment_id.deposit_cdc_id.bank_journal_id.display_name)
                (payment + self.related_payment_ids). \
                    action_cdc_receivable_bounced(
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                    related_payments=self.related_payment_ids,
                    bounce_date=self.bounce_date,
                )
            else:
                payment.action_cdc_receivable_bounced(
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                    bounce_date=self.bounce_date
                )
