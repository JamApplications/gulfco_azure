from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentPdcCollect(models.TransientModel):
    _name = 'account.payment.pdc.collect'
    _description = 'Account Payment PDC Receivable Collect Wizard'

    collect_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='PDC',
    )
    payment_ids = fields.Many2many(
        relation= "rel_account_payment_account_payment_pdc_collect",
        comodel_name='account.payment',
        string='PDC Payments',
    )
    payment_ref = fields.Char(
        string='PDC',
        related='payment_id.memo',
    )
    payment_pdc_state = fields.Selection(
        related='payment_id.pdc_state',
    )

    allow_merge_pdc = fields.Boolean(
        string='Allow Merge PDC'
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
        string='Related PDC',
        domain="[('id', '!=', payment_id),"
               "('pdc_state', '=', payment_pdc_state)]",
    )

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentPdcCollect, self).default_get(fields)
        if 'active_ids' in self.env.context and len(self.env.context.get('active_ids')) > 1 and self.env.context.get(
                'active_model') == 'account.payment':
            payment_ids = self.env['account.payment'].browse(
                self.env.context['active_ids'])
            res['payment_ids'] = payment_ids.ids
        elif 'active_id' in self.env.context and self.env.context.get(
                'active_model') == 'account.payment':
            payment = self.env['account.payment'].browse(
                self.env.context['active_id'])
            related_payments = self.env['account.payment'].search([
                ('id', '!=', payment.id),
                ('pdc_state', '=', payment.pdc_state),
                ('memo', '=', payment.memo),
                ('company_id', '=', payment.company_id.id),
            ])
            res['payment_id'] = payment.id
            res['partner_id'] = payment.partner_id.id
            if related_payments:
                res['allow_merge_pdc'] = True
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

    @api.onchange('allow_merge_pdc')
    def _onchange_allow_merge_pdc(self):
        """
        reset data
        """
        if not self.allow_merge_pdc:
            self.partner_id = self.payment_id.partner_id
            self.allowed_partner_ids = False
        else:
            pass
            # related_payments = self.env['account.payment'].search([
            #     ('id', '!=', self.payment_id.id),
            #     ('pdc_state', '=', self.payment_id.pdc_state),
            #     ('memo', '=', self.payment_id.memo),
            #     ('company_id', '=', self.payment_id.company_id.id),
            # ])
            # self.related_payment_ids = related_payments

    def action_collect_pdc(self):
        """ collect pdc receivable """
        if self.payment_ids and len(self.payment_ids) > 1:
            for payment in self.payment_ids:
                payment.action_collect_payment_pdc_receivable(
                collect_date=self.collect_date,
                partner=payment.partner_id,
                original_payment=payment,
            )
        else:
            payment = self.payment_id
            if payment.due_date > fields.date.today:
                raise ValidationError(_('You can not collect PDC till its due date'))
            if self.related_payment_ids and self.allow_merge_pdc:
                related_pay_journals = self.related_payment_ids.mapped('journal_id')
                if len(related_pay_journals) > 1:
                    raise ValidationError(_('Related PDC must have same journal'))
                if related_pay_journals != self.payment_id.journal_id:
                    raise ValidationError(_('Related PDC must have journal %s')
                                        % self.payment_id.journal_id.display_name)
                related_pay_state = self.related_payment_ids.mapped('pdc_state')
                if related_pay_state[0] != self.payment_id.pdc_state:
                    raise ValidationError(_('Related PDC must has same '
                                            'status as payment %s')
                                        % self.payment_id.display_name)
                related_deposit_journals = self.related_payment_ids.mapped(
                    'deposit_pdc_id.bank_journal_id')
                if len(related_deposit_journals) > 1:
                    raise ValidationError(
                        _('Related PDC must has same deposit bank'))
                if related_deposit_journals[0] != \
                        self.payment_id.deposit_pdc_id.bank_journal_id:
                    raise ValidationError(
                        _('Related PDC must has same deposit bank %s')
                        % self.payment_id.deposit_pdc_id.bank_journal_id.display_name)
                (payment + self.related_payment_ids). \
                    action_collect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                    related_payments=self.related_payment_ids,
                )
            else:
                payment.action_collect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                )

    def action_recollect_pdc(self):
        """ collect pdc receivable """
        if self.payment_ids and len(self.payment_ids) > 1:
            for payment in self.payment_ids:
                payment.action_recollect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=payment.partner_id,
                    original_payment=payment,
                )
        else:
            payment = self.payment_id
            if self.related_payment_ids and self.allow_merge_pdc:
                related_pay_journals = self.related_payment_ids.mapped('journal_id')
                if len(related_pay_journals) > 1:
                    raise ValidationError(_('Related PDC must have same journal'))
                if related_pay_journals != self.payment_id.journal_id:
                    raise ValidationError(_('Related PDC must have journal %s')
                                        % self.payment_id.journal_id.display_name)
                related_pay_state = self.related_payment_ids.mapped('pdc_state')
                if related_pay_state[0] != self.payment_id.pdc_state:
                    raise ValidationError(_('Related PDC must has same '
                                            'status as payment %s')
                                        % self.payment_id.display_name)
                related_deposit_journals = self.related_payment_ids.mapped(
                    'deposit_pdc_id.bank_journal_id')
                if len(related_deposit_journals) > 1:
                    raise ValidationError(
                        _('Related PDC must has same deposit bank'))
                if related_deposit_journals[0] != \
                        self.payment_id.deposit_pdc_id.bank_journal_id:
                    raise ValidationError(
                        _('Related PDC must has same deposit bank %s')
                        % self.payment_id.deposit_pdc_id.bank_journal_id.display_name)
                (payment + self.related_payment_ids). \
                    action_recollect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                    related_payments=self.related_payment_ids,
                )
            else:
                payment.action_recollect_payment_pdc_receivable(
                    collect_date=self.collect_date,
                    partner=self.partner_id,
                    original_payment=self.payment_id,
                )
    
    def action_redeposit_pdc_payment(self, payment, collect_date):
        if payment.pdc_state not in ['bounced', 'returned']:
            raise ValidationError(_('PDC must be in bounced or returned state to re-deposit.'))
        company_currency = payment.journal_id.company_id.currency_id
        if payment.state == 'in_process':
            payment.mark_as_sent()
            amount_currency = payment._get_payment_amount()
            currency = company_currency
            if payment.currency_id != company_currency:
                amount_currency = payment._get_payment_amount(company_currency=False)
                currency = payment.currency_id
            payment_company_amount = payment._get_payment_amount()
            liquidity_analytic_tag_ids = False
            if hasattr(payment, 'liquidity_analytic_tag_ids'):
                liquidity_analytic_tag_ids = payment.liquidity_analytic_tag_ids.ids

            payment_method = payment.payment_method_line_id
            if not payment_method.payment_account_id:
                raise ValidationError(_("You need to configure the outstanding account in the journal!"))
            if not payment.journal_id.pdc_bounce_receivable_account_id or not payment.journal_id.pdc_bounce_beneficiaries_account_id:
                raise ValidationError(_("You need to configure the bounce account in the journal!"))

            move = payment._create_pdc_bounce_journal_entry(
                journal=payment.journal_id,
                partner=payment.partner_id,
                label='Cheque Redeposit %s - %s' % (payment.memo, payment.name),
                amount=payment._get_payment_amount(),
                debit_account=payment_method.payment_account_id,
                credit_account=payment.partner_id.property_account_receivable_id,
                bounce_debit=payment.journal_id.pdc_bounce_beneficiaries_account_id,
                bounce_credit=payment.journal_id.pdc_bounce_receivable_account_id,
                amount_currency=amount_currency,
                currency=currency,
                ref=payment.name,
                debit_analytic_tag_ids=liquidity_analytic_tag_ids,
                credit_analytic_tag_ids=liquidity_analytic_tag_ids,
                cheque_payment_type='deposit',
                date=collect_date or fields.date.today(),
            )


            payment.deposit_move_id = move.id
        # payment_line = payment.move_id.line_ids.filtered(
        #     lambda line: line.account_id == payment.journal_id.pdc_notes_receivable_account_id)
        # deposit_line = move.line_ids.filtered(
        #     lambda line: line.account_id == payment.journal_id.pdc_notes_receivable_account_id)
        # (payment_line + deposit_line).reconcile()
        payment.pdc_state = 'deposit'
    
    def action_redeposit_pdc(self):
        """ Re-deposit PDC Receivable 
            Related PDC not considered currently.
        """
        if self.payment_ids and len(self.payment_ids) > 1:
            for payment in self.payment_ids:
                self.action_redeposit_pdc_payment(payment, self.collect_date)
        else:
            self.action_redeposit_pdc_payment(self.payment_id, self.collect_date)