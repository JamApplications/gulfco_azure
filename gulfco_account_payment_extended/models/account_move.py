from odoo import api, fields, models, Command, _
from odoo.tools import float_compare, float_round, float_repr
from datetime import date
from odoo.exceptions import ValidationError
from lxml import etree

class AccountMove(models.Model):
    _inherit = "account.move"

    payment_transfer_id = fields.Many2one('payments.transfer', string="Payment Transfer")
    show_payment_ribbon = fields.Boolean(
        string="Show Payment Ribbon", compute='_compute_show_payment_ribbon'
    )
    bill_date = fields.Date(string="Bill Date")
    transaction_date = fields.Date(string="Transaction Date")

    @api.constrains('invoice_date', 'receipt_date', 'date')
    def _check_dates_not_future(self):
        today = date.today()
        for move in self:
            if move.move_type not in ['in_invoice', 'in_refund']:
                continue
            if move.invoice_date and move.invoice_date > today:
                raise ValidationError(_("Bill Date cannot be in the future."))
            if move.receipt_date and move.receipt_date > today:
                raise ValidationError(_("Invoice Received Date cannot be in the future."))
            if move.date and move.date > today:
                raise ValidationError(_("Accounting Date cannot be in the future."))

    @api.constrains('partner_id', 'ref')
    def _check_unique_customer_reference(self):
        for move in self:
            if move.ref and move.move_type in ['out_invoice','out_refund']:
                domain = [
                    ('id', '!=', move.id),
                    ('partner_id', '=', move.partner_id.id),
                    ('ref', '=', move.ref),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        _("The Customer Reference '%s' is already used for this customer.") % move.ref
                    )

    @api.depends('payment_state','line_ids.matched_debit_ids.debit_move_id.payment_id',
                 'line_ids.matched_credit_ids.credit_move_id.payment_id')
    def _compute_show_payment_ribbon(self):
        for move in self:
            show = True
            if move.payment_state in ['paid', 'partial']:
                # Find all related payments via reconciliation
                related_payments = move.line_ids.mapped('matched_debit_ids.debit_move_id.payment_id') | \
                                   move.line_ids.mapped('matched_credit_ids.credit_move_id.payment_id')
                # Filter PDC/CDC payments that are not cleared
                cheque_payments = related_payments.filtered(
                    lambda p: p.payment_mode in ['pdc', 'cdc']
                            and (p.pdc_state and p.pdc_state != 'collected')
                            and (p.pdc_payable_state and p.pdc_payable_state != 'cleared')
                            and (p.cdc_payable_state and p.cdc_payable_state != 'cleared')
                            and (p.cdc_state and p.cdc_state != 'collected')
                )
                if cheque_payments:
                    show = False
            move.show_payment_ribbon = show

    media_id = fields.Many2one('account.payment.method', string="Media")

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        if self.partner_id and self.partner_id.media_id:
            self.media_id = self.partner_id.media_id.id

    @api.depends('restrict_mode_hash_table', 'state', 'inalterable_hash')
    def _compute_show_reset_to_draft_button(self):
        super(AccountMove, self)._compute_show_reset_to_draft_button()
        for move in self:
            # If payment_state is paid, in payment or partially paid, do not show reset to draft button in vendor bills
            if move.move_type == 'in_invoice' and move.payment_state in ['paid', 'partial', 'in_payment']:
                move.show_reset_to_draft_button = False

    @api.depends('partner_id')
    def _compute_invoice_payment_term_id(self):
        for move in self:
            move = move.with_company(move.company_id)
            if move.is_sale_document(include_receipts=True) and move.partner_id.property_payment_term_id:
                move.invoice_payment_term_id = move.partner_id.property_payment_term_id
            elif move.is_purchase_document(include_receipts=True) and move.partner_id.property_supplier_payment_term_id:
                move.invoice_payment_term_id = move.partner_id.property_supplier_payment_term_id
            else:
                payment_term = self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False)
                if payment_term:
                    move.invoice_payment_term_id = payment_term.id
                else:
                    move.invoice_payment_term_id = False


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('price_unit')
    def check_onchange_price_unit(self):
        if self.price_unit < 0 and self.move_type in ['out_invoice','out_refund','in_invoice','in_refund'] and not self.env.company.anglo_saxon_accounting:
            raise ValidationError(_("Unit Price cannot be negative on line: %s") % self.name or '')

    payment_amount = fields.Monetary(
        string="Payment Amount",
        currency_field='company_currency_id',
        help="Amount paid in company currency.",
    )

    payment_amount_currency = fields.Monetary(
        string="Payment Amount in Currency",
        currency_field='currency_id',
        compute='_compute_payment_amount_currency',
        store=True,
        help="Amount paid in transaction currency.",
    )
    comment = fields.Char(string="Comment")
    matched_date = fields.Date(string="Matched Date",copy=False)
    cheque_number = fields.Char('Cheque Number', compute='_compute_payment_data', store=True)
    payment_memo = fields.Char('Memo', compute='_compute_payment_data', store=True)

    @api.depends('payment_id', 'payment_id.pdc_ref', 'payment_id.cdc_ref', 'payment_id.memo',
                 'move_id.cheque_payment_id', 'move_id.cheque_payment_id.pdc_ref', 'move_id.cheque_payment_id.cdc_ref',
                 'move_id.cheque_payment_id.memo',
                 'move_id.origin_payment_id', 'move_id.origin_payment_id.pdc_ref', 'move_id.origin_payment_id.cdc_ref',
                 'move_id.origin_payment_id.memo')
    def _compute_payment_data(self):
        for rec in self:
            cheque_number = ""
            payment_memo = ""
            payment_id = rec.payment_id or rec.move_id.cheque_payment_id or rec.move_id.origin_payment_id
            if payment_id:
                if payment_id.pdc_ref:
                    cheque_number = payment_id.pdc_ref
                elif payment_id.cdc_ref:
                    cheque_number = payment_id.cdc_ref

                if payment_id.memo:
                    payment_memo = payment_id.memo

            rec.cheque_number = cheque_number
            rec.payment_memo = payment_memo
            

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self._context.get('from_reconciled') and not self._context.get('from_reconcile_popup') and self.env.user.has_group('gulfco_account_payment_extended.group_hide_misc_entries_reconcile'):
            domain = domain.copy()
            domain.append((('journal_id.type', '!=', 'general')))
        return super()._search(domain, offset, limit, order)

    @api.depends('payment_amount', 'currency_id', 'company_currency_id','date')
    def _compute_payment_amount_currency(self):
        for line in self:
            if line.currency_id and line.company_currency_id and line.date and line.payment_amount:
                converted = line.company_currency_id._convert(
                    from_amount=line.payment_amount,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.date
                )
                line.payment_amount_currency = float_round(
                    converted, precision_rounding=line.currency_id.rounding
                )
            else:
                line.payment_amount_currency = 0.0

    matching_reference = fields.Char(
        string="Matching Reference",
        help="Reference used to match this line with payment."
    )

    @api.constrains('quantity', 'price_unit')
    def _check_positive_qty_price(self):
        for line in self:
            if line.move_type in ['out_invoice','out_refund','in_invoice','in_refund'] and not self.env.company.anglo_saxon_accounting:
                if line.quantity < 0:
                    raise ValidationError(_("Quantity cannot be negative on line: %s") % line.name or '')
                if line.price_unit < 0:
                    raise ValidationError(_("Unit Price cannot be negative on line: %s") % line.name or '')

    @api.depends('product_id', 'product_uom_id','move_id','move_id.move_type')
    def _compute_tax_ids(self):
        super()._compute_tax_ids()  # keep native logic

        default_sale_tax_id = self.company_id.account_sale_tax_id
        default_purchase_tax_id = self.company_id.account_purchase_tax_id

        for line in self:
            if line.display_type in ('line_section', 'line_note', 'payment_term') or line.is_imported:
                continue

            # If tax_ids is empty, try product tax
            taxes = False
            if not line.tax_ids and not line.product_id:
                if line.move_id.move_type and line.move_id.move_type in ('out_invoice'):
                    taxes = default_sale_tax_id
                elif line.move_id.move_type and line.move_id.move_type in ('in_invoice'):
                    taxes = default_purchase_tax_id
                else:
                    taxes = self.env['account.tax']

            if (not line.tax_ids and not line.product_id) or self._context.get("update_fp_taxes"):
                if not taxes:
                    taxes = line.tax_ids
                tax_ids = taxes.filtered(lambda tax: tax.company_id == line.company_id)
                if tax_ids and self.move_id.fiscal_position_id:
                    tax_ids = self.move_id.fiscal_position_id.map_tax(tax_ids)
                line.tax_ids = tax_ids


    def action_reconcile(self):
        """ This function is called by the 'Reconcile' button of account.move.line's
        list view. It performs reconciliation between the selected lines.
        - If the reconciliation can be done directly we do it silently
        - Else, if a write-off is required we open the wizard to let the client enter required information
        """
        if not self._context.get('is_pdc_payment_matching'):
            return super(AccountMoveLine, self).action_reconcile()
        
        self = self.filtered(lambda x: x.balance or x.amount_currency)  # noqa: PLW0642
        if not self:
            return

        # Custom: Directly reconcile PDC payment line and Invoice lines without opening the wizard
        pdc_journals = self.env['account.journal'].search([('type', '=', 'bank'), ('is_pdc', '=', True)])
        cdc_journals = self.env['account.journal'].search([('type', '=', 'bank'), ('is_cdc', '=', True)])
        pdc_accounts = pdc_journals.pdc_check_under_collection_account_id.ids
        pdc_accounts += cdc_journals.cdc_check_under_collection_account_id.ids
        if not any(line.account_id.id in pdc_accounts for line in self):
            return super(AccountMoveLine, self).action_reconcile()
        
        # If we are here, it means we are dealing with PDC payment lines
        # and we can reconcile them directly without opening the wizard to make sure It works with PDC payment matching
        # And in memo we don't get Misc. Operations and get PDC Payment Matching
        pdc_line = self.filtered(lambda line: line.account_id.id in pdc_accounts)
        
        # Find unreconciled invoice lines (non-PDC, receivable)
        invoice_lines_to_reconcile = self.filtered(
                lambda line: line.account_id.id not in pdc_accounts and 
                line.account_id.account_type == 'asset_receivable' and not line.reconciled)
        
        if not invoice_lines_to_reconcile or not pdc_line:
            return super(AccountMoveLine, self).action_reconcile()
        
        # Reconcile PDC payment line with invoice lines
        lines_to_reconcile = pdc_line + invoice_lines_to_reconcile
        res = lines_to_reconcile.reconcile()
        return res

    def _reconcile_plan_with_sync(self, plan_list, all_amls):
        # Parameter allowing to disable the exchange journal entries on partials.
        disable_partial_exchange_diff = bool(self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))

        # ==== Prefetch the fields all at once to speedup the reconciliation ====
        # All of those fields will be cached by the orm. Since the amls are split into multiple batches, the orm is not
        # able to prefetch the data for all of them at once. For that reason, we force the orm to populate the cache
        # before doing anything.
        all_amls.move_id
        all_amls.matched_debit_ids
        all_amls.matched_credit_ids

        # ==== Track the invoice's state to call the hook when they become paid ====
        pre_hook_data = all_amls._reconcile_pre_hook()

        # ==== Collect amls data ====
        # All residual amounts are collected and updated until the creation of partials in batch.
        # This is done that way to minimize the orm time for fields invalidation/mark as recompute and
        # recomputation.
        aml_values_map = {
            aml: {
                'aml': aml,
                'amount_residual': aml.payment_amount if aml.payment_amount and 'partial_move_line_ids' in self.env.context and aml.id in self.env.context.get('partial_move_line_ids').ids else aml.amount_residual,
                'amount_residual_currency': aml.payment_amount_currency if aml.payment_amount_currency and 'partial_move_line_ids' in self.env.context and aml.id in self.env.context.get('partial_move_line_ids').ids else aml.amount_residual_currency,
            }
            for aml in all_amls
        }

        # ==== Prepare the partials ====
        partials_values_list = []
        exchange_diff_values_list = []
        exchange_diff_partial_index = []
        all_plan_results = []
        partial_index = 0
        for plan in plan_list:
            plan_results = self\
                .with_context(
                    no_exchange_difference=self._context.get('no_exchange_difference') or disable_partial_exchange_diff,
                    no_exchange_difference_no_recursive=self._context.get('no_exchange_difference_no_recursive', False),
                )\
                ._prepare_reconciliation_plan(plan, aml_values_map)
            all_plan_results.append(plan_results)
            for results in plan_results:
                partials_values_list.append(results['partial_values'])
                if results.get('exchange_values') and results['exchange_values']['move_values']['line_ids']:
                    exchange_diff_values_list.append(results['exchange_values'])
                    exchange_diff_partial_index.append(partial_index)
                    partial_index += 1

        # ==== Create the partials ====
        # Link the newly created partials to the plan. There are needed later for caba exchange entries.
        partials = self.env['account.partial.reconcile'].create(partials_values_list)
        start_range = 0
        for plan_results, plan in zip(all_plan_results, plan_list):
            size = len(plan_results)
            plan['partials'] = partials[start_range:start_range + size]
            start_range += size

        # ==== Create the partial exchange journal entries ====
        exchange_moves = self._create_exchange_difference_moves(exchange_diff_values_list)
        for index, exchange_move in zip(exchange_diff_partial_index, exchange_moves):
            partials[index].exchange_move_id = exchange_move

        # ==== Create entries for cash basis taxes ====
        def is_cash_basis_needed(amls):
            return any(amls.company_id.mapped('tax_exigibility')) \
                and amls.account_id.account_type in ('asset_receivable', 'liability_payable')

        if not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
            for plan in plan_list:
                if is_cash_basis_needed(plan['amls']):
                    plan['partials'].with_context(no_exchange_difference_no_recursive=False)._create_tax_cash_basis_moves()

        # ==== Prepare full reconcile creation ====
        # First, we need to find all sub-set of amls that are candidates for a full.

        def is_line_reconciled(aml, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            if aml.reconciled:
                return True
            if not aml.matched_debit_ids and not aml.matched_credit_ids:
                # Suppose a journal item having balance = 0 but an amount_currency like an exchange difference.
                return False
            if has_multiple_currencies:
                return aml.company_currency_id.is_zero(aml.amount_residual)
            else:
                return aml.currency_id.is_zero(aml.amount_residual_currency)

        full_batches = []
        all_aml_ids = set()
        number2lines = all_amls._reconciled_by_number()
        for plan in plan_list:
            for aml in plan['amls']:
                if 'full_batch_index' in aml_values_map[aml]:
                    continue

                involved_amls = plan['amls']._filter_reconciled_by_number(number2lines)
                all_aml_ids.update(involved_amls.ids)
                full_batch_index = len(full_batches)
                has_multiple_currencies = len(involved_amls.currency_id) > 1
                is_fully_reconciled = all(
                    is_line_reconciled(involved_aml, has_multiple_currencies)
                    for involved_aml in involved_amls
                )
                full_batches.append({
                    'amls': involved_amls,
                    'is_fully_reconciled': is_fully_reconciled,
                })
                for involved_aml in involved_amls:
                    if aml_values_map.get(involved_aml):
                        aml_values_map[involved_aml]['full_batch_index'] = full_batch_index

        # ==== Prefetch the fields all at once to speedup the reconciliation ====
        # Again, we do the same optimization for the prefetching. We need to do it again since most of the values have
        # been invalidated with the creation of the account.partial.reconcile records.
        all_amls = self.browse(list(all_aml_ids))
        all_amls.move_id
        all_amls.matched_debit_ids
        all_amls.matched_credit_ids

        # ==== Prepare the full exchange journal entries ====
        # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
        # when importing a full accounting including the reconciliation like Winbooks.

        exchange_diff_values_list = []
        exchange_diff_full_batch_index = []
        if not self._context.get('no_exchange_difference'):
            for full_batch_index, full_batch in enumerate(full_batches):
                involved_amls = full_batch['amls']
                if not full_batch['is_fully_reconciled']:
                    continue

                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for aml in involved_amls:
                    if not aml.company_currency_id.is_zero(aml.amount_residual):
                        exchange_lines_to_fix += aml
                        amounts_list.append({'amount_residual': aml.amount_residual})
                    elif not aml.currency_id.is_zero(aml.amount_residual_currency):
                        exchange_lines_to_fix += aml
                        amounts_list.append({'amount_residual_currency': aml.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, aml.date)
                exchange_diff_values = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_amls.company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                # If we are fully reversing the entry, no need to fix anything since the journal entry
                # is exactly the mirror of the source journal entry.
                caba_lines_to_reconcile = None
                if is_cash_basis_needed(involved_amls) and not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
                    caba_lines_to_reconcile = involved_amls._add_exchange_difference_cash_basis_vals(exchange_diff_values)

                # Prepare the exchange difference.
                if exchange_diff_values['move_values']['line_ids']:
                    exchange_diff_full_batch_index.append(full_batch_index)
                    exchange_diff_values_list.append(exchange_diff_values)
                    full_batch['caba_lines_to_reconcile'] = caba_lines_to_reconcile

        # ==== Create the full exchange journal entries ====
        exchange_moves = self._create_exchange_difference_moves(exchange_diff_values_list)
        for full_batch_index, exchange_move in zip(exchange_diff_full_batch_index, exchange_moves):
            full_batch = full_batches[full_batch_index]
            amls = full_batch['amls']
            full_batch['exchange_move'] = exchange_move
            exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == amls.account_id)
            full_batch['amls'] |= exchange_move_lines

        # ==== Create the full reconcile ====
        # Note we are using Command.link and not Command.set because Command.set is triggering an unlink that is
        # slowing down the assignation of the co-fields. Indeed, unlink is forcing a flush.
        full_reconcile_values_list = []
        full_reconcile_full_batch_index = []
        for full_batch_index, full_batch in enumerate(full_batches):
            amls = full_batch['amls']
            involved_partials = amls.matched_debit_ids + amls.matched_credit_ids
            if full_batch['is_fully_reconciled']:
                full_reconcile_values_list.append({
                    'exchange_move_id': full_batch.get('exchange_move') and full_batch['exchange_move'].id,
                    'partial_reconcile_ids': [Command.link(partial.id) for partial in involved_partials],
                    'reconciled_line_ids': [Command.link(aml.id) for aml in amls],
                })
                full_reconcile_full_batch_index.append(full_batch_index)

        self.env['account.full.reconcile'].create(full_reconcile_values_list)

        # === Cash basis rounding autoreconciliation ===
        # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
        # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)
        for full_batch in full_batches:
            if not full_batch.get('caba_lines_to_reconcile'):
                continue

            caba_lines_to_reconcile = full_batch['caba_lines_to_reconcile']
            exchange_move = full_batch['exchange_move']
            for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                if not account.reconcile:
                    continue

                exchange_line = exchange_move.line_ids.filtered(
                    lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                )

                (exchange_line + amls_to_reconcile)\
                    .filtered(lambda l: not l.reconciled)\
                    .reconcile()

        all_amls._reconcile_post_hook(pre_hook_data)

    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if self.env.user.has_group('gulfco_account_payment_extended.group_hide_delete_action_move_line'):
            arch = etree.XML(res['arch'])
            if view_type == 'form':
                arch.attrib['delete'] = 'false'
            if view_type == 'list':
                arch.attrib['delete'] = 'false'
            res['arch'] = etree.tostring(arch, encoding='unicode')
        return res

    # @api.model
    # def _prepare_reconciliation_single_partial(self, debit_values, credit_values, shadowed_aml_values=None):
    #     """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
    #     as parameters, each one representing an account.move.line.
    #     :param debit_values:  The values of account.move.line to consider for a debit line.
    #     :param credit_values: The values of account.move.line to consider for a credit line.
    #     :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
    #                                 This is usefull if you want to preview the reconciliation before doing some changes
    #                                 on amls like changing a date or an account.
    #     :return: A dictionary:
    #         * debit_values:     None if the line has nothing left to reconcile.
    #         * credit_values:    None if the line has nothing left to reconcile.
    #         * partial_values:   The newly computed values for the partial.
    #         * exchange_values:  The values to create an exchange difference linked to this partial.
    #     """
    #     # ==== Determine the currency in which the reconciliation will be done ====
    #     # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
    #     # currency and at which rate the reconciliation will be done.
    #     res = {
    #         'debit_values': debit_values,
    #         'credit_values': credit_values,
    #     }
    #     debit_aml = debit_values['aml']
    #     credit_aml = credit_values['aml']
    #     debit_currency = debit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
    #     credit_currency = credit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
    #     company_currency = debit_aml.company_currency_id
    #
    #     remaining_debit_amount_curr = debit_values['amount_residual_currency']
    #     remaining_credit_amount_curr = credit_values['amount_residual_currency']
    #     remaining_debit_amount = debit_values['amount_residual']
    #     remaining_credit_amount = credit_values['amount_residual']
    #
    #     debit_available_residual_amounts = self._prepare_move_line_residual_amounts(
    #         debit_values,
    #         credit_currency,
    #         shadowed_aml_values=shadowed_aml_values,
    #         other_aml_values=credit_values,
    #     )
    #     credit_available_residual_amounts = self._prepare_move_line_residual_amounts(
    #         credit_values,
    #         debit_currency,
    #         shadowed_aml_values=shadowed_aml_values,
    #         other_aml_values=debit_values,
    #     )
    #
    #     if debit_currency != company_currency \
    #             and debit_currency in debit_available_residual_amounts \
    #             and debit_currency in credit_available_residual_amounts:
    #         recon_currency = debit_currency
    #     elif credit_currency != company_currency \
    #             and credit_currency in debit_available_residual_amounts \
    #             and credit_currency in credit_available_residual_amounts:
    #         recon_currency = credit_currency
    #     else:
    #         recon_currency = company_currency
    #
    #     debit_recon_values = debit_available_residual_amounts.get(recon_currency)
    #     credit_recon_values = credit_available_residual_amounts.get(recon_currency)
    #
    #     if 'partial_move_line_ids' in self.env.context and self.env.context.get(
    #             'partial_move_line_ids') and debit_recon_values.get('payment_amount'):
    #         debit_recon_values.update({'residual': debit_recon_values.get('payment_amount')})
    #
    #     # Check if there is something left to reconcile. Move to the next loop iteration if not.
    #     skip_reconciliation = False
    #     if not debit_recon_values:
    #         res['debit_values'] = None
    #         skip_reconciliation = True
    #     if not credit_recon_values:
    #         res['credit_values'] = None
    #         skip_reconciliation = True
    #     if skip_reconciliation:
    #         return res
    #
    #     recon_debit_amount = debit_recon_values['residual']
    #     recon_credit_amount = -credit_recon_values['residual']
    #
    #     # ==== Match both lines together and compute amounts to reconcile ====
    #
    #     # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
    #     # currency but at least one has no amount in foreign currency.
    #     # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
    #     # to reduce only the amount in company currency but not the foreign one.
    #     exchange_line_mode = \
    #         recon_currency == company_currency \
    #         and debit_currency == credit_currency \
    #         and (
    #                 not debit_available_residual_amounts.get(debit_currency)
    #                 or not credit_available_residual_amounts.get(credit_currency)
    #         )
    #
    #     # Determine which line is fully matched by the other.
    #     compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
    #     min_recon_amount = min(recon_debit_amount, recon_credit_amount)
    #     debit_fully_matched = compare_amounts <= 0
    #     credit_fully_matched = compare_amounts >= 0
    #
    #     def get_amount_range_after_rate(currency_from, currency_to, amount, rate):
    #         # Suppose balance=1000, rate=12.
    #         # 1000.0 could be the result of a rounding of [999.995, 1000.0049999999999].
    #         # Let's say the target currency could be [999.995 * 12, 1000.005 * 12] = [11999.94, 12000.06]
    #         # instead of just 120000.
    #         if not rate:
    #             return 0.0, 0.0, 0.0
    #         half_rounding = currency_from.rounding / 2
    #         return (
    #             currency_to.round((amount - half_rounding) * rate),
    #             currency_to.round(amount * rate),
    #             currency_to.round((amount + half_rounding) * rate),
    #         )
    #
    #     # ==== Computation of partial amounts ====
    #     if recon_currency == company_currency:
    #         if exchange_line_mode:
    #             debit_rate = None
    #             credit_rate = None
    #         else:
    #             debit_rate = debit_available_residual_amounts.get(debit_currency, {}).get('rate')
    #             credit_rate = credit_available_residual_amounts.get(credit_currency, {}).get('rate')
    #
    #         # Compute the partial amount expressed in company currency.
    #         partial_amount = min_recon_amount
    #
    #         # Compute the partial amount expressed in foreign currency.
    #         if debit_rate:
    #             partial_debit_amount_currency = debit_currency.round(debit_rate * min_recon_amount)
    #             partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
    #         else:
    #             partial_debit_amount_currency = 0.0
    #         if credit_rate:
    #             partial_credit_amount_currency = credit_currency.round(credit_rate * min_recon_amount)
    #             partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
    #         else:
    #             partial_credit_amount_currency = 0.0
    #
    #     else:
    #         # recon_currency != company_currency
    #         if exchange_line_mode:
    #             debit_rate = None
    #             credit_rate = None
    #         else:
    #             debit_rate = debit_recon_values['rate']
    #             credit_rate = credit_recon_values['rate']
    #
    #         # Compute the partial amount expressed in foreign currency.
    #         partial_debit_amount_range = get_amount_range_after_rate(
    #             currency_from=debit_currency,
    #             currency_to=company_currency,
    #             amount=min_recon_amount,
    #             rate=(1 / debit_rate) if debit_rate else 0.0,
    #         )
    #         partial_debit_amount = partial_debit_amount_range[1]
    #         partial_debit_amount = min(partial_debit_amount, remaining_debit_amount)
    #         partial_credit_amount_range = get_amount_range_after_rate(
    #             currency_from=credit_currency,
    #             currency_to=company_currency,
    #             amount=min_recon_amount,
    #             rate=(1 / credit_rate) if credit_rate else 0.0,
    #         )
    #         partial_credit_amount = partial_credit_amount_range[1]
    #         partial_credit_amount = min(partial_credit_amount, -remaining_credit_amount)
    #         partial_amount = min(partial_debit_amount, partial_credit_amount)
    #
    #         # Prevent exchange differences if amounts are close enough to be a rounding issue
    #         # after applying the exchange rate and then, rounding amounts to store them into
    #         # the monetary fields.
    #         # Suppose 2 lines:
    #         # l1: balance=377554.0, amount_currency=20000.0
    #         # l2: balance=-5314.62, amount_currency=-281.53
    #         # ... computing min_recon_amount = min(20000.0, 281.53) = 281.53 in foreign currency to reconcile.
    #         # The equivalent of 281.53 for l1 in company currency is 5314.64 that could be the result of rounding any value
    #         # between [5314.54, 5314.7300000000005]
    #         # ... considering the rate of 0.05297255491929631 and the rounding applied to reach this value.
    #         # For l2, it will be 5314.62 in the range [5314.53, 5314.71].
    #         #
    #         # ---------
    #         # | 5314.73         ---------       <- max amount
    #         # |                 5314.71  |
    #         # |                          |
    #         # | 5314.64                  |
    #         # |                 5314.62  |      Every number between the min and the max are considered as valid to be the partial amount.
    #         # |                          |      Depending on the one we choose, we can avoid to create an exchange difference entry or
    #         # |                          |      we could also prevent to let an unnecessary open residual amount.
    #         # | 5314.54                  |
    #         # ---------         5314.53  |      <- min amount
    #         #                   ---------
    #         if (
    #                 company_currency.compare_amounts(partial_debit_amount, partial_credit_amount_range[2]) <= 0
    #                 and company_currency.compare_amounts(partial_debit_amount, partial_credit_amount_range[0]) >= 0
    #                 and company_currency.compare_amounts(partial_credit_amount, partial_debit_amount_range[2]) <= 0
    #                 and company_currency.compare_amounts(partial_credit_amount, partial_debit_amount_range[0]) >= 0
    #         ):
    #             if debit_fully_matched:
    #                 partial_amount = remaining_debit_amount
    #             else:
    #                 partial_amount = -remaining_credit_amount
    #             partial_debit_amount = partial_amount
    #             partial_credit_amount = partial_amount
    #
    #         # Compute the partial amount expressed in foreign currency.
    #         # Take care to handle the case when a line expressed in company currency is mimicking the foreign
    #         # currency of the opposite line.
    #         if debit_currency == company_currency:
    #             partial_debit_amount_currency = partial_amount
    #         else:
    #             partial_debit_amount_currency = min_recon_amount
    #         if credit_currency == company_currency:
    #             partial_credit_amount_currency = partial_amount
    #         else:
    #             partial_credit_amount_currency = min_recon_amount
    #
    #     # Computation of the partial exchange difference. You can skip this part using the
    #     # `no_exchange_difference` context key (when reconciling an exchange difference for example).
    #     if not self._context.get('no_exchange_difference') and not self._context.get(
    #             'no_exchange_difference_no_recursive'):
    #         exchange_lines_to_fix = self.env['account.move.line']
    #         amounts_list = []
    #         if recon_currency == company_currency:
    #             if debit_fully_matched:
    #                 debit_exchange_amount = remaining_debit_amount_curr - partial_debit_amount_currency
    #                 if not debit_currency.is_zero(debit_exchange_amount):
    #                     exchange_lines_to_fix += debit_aml
    #                     amounts_list.append({'amount_residual_currency': debit_exchange_amount})
    #                     remaining_debit_amount_curr -= debit_exchange_amount
    #             if credit_fully_matched:
    #                 credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
    #                 if not credit_currency.is_zero(credit_exchange_amount):
    #                     exchange_lines_to_fix += credit_aml
    #                     amounts_list.append({'amount_residual_currency': credit_exchange_amount})
    #                     remaining_credit_amount_curr += credit_exchange_amount
    #
    #         else:
    #             if debit_fully_matched:
    #                 # Create an exchange difference on the remaining amount expressed in company's currency.
    #                 debit_exchange_amount = remaining_debit_amount - partial_amount
    #                 if not company_currency.is_zero(debit_exchange_amount):
    #                     exchange_lines_to_fix += debit_aml
    #                     amounts_list.append({'amount_residual': debit_exchange_amount})
    #                     remaining_debit_amount -= debit_exchange_amount
    #                     if debit_currency == company_currency:
    #                         remaining_debit_amount_curr -= debit_exchange_amount
    #             else:
    #                 # Create an exchange difference ensuring the rate between the residual amounts expressed in
    #                 # both foreign and company's currency is still consistent regarding the rate between
    #                 # 'amount_currency' & 'balance'.
    #                 debit_exchange_amount = partial_debit_amount - partial_amount
    #                 if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
    #                     exchange_lines_to_fix += debit_aml
    #                     amounts_list.append({'amount_residual': debit_exchange_amount})
    #                     remaining_debit_amount -= debit_exchange_amount
    #                     if debit_currency == company_currency:
    #                         remaining_debit_amount_curr -= debit_exchange_amount
    #
    #             if credit_fully_matched:
    #                 # Create an exchange difference on the remaining amount expressed in company's currency.
    #                 credit_exchange_amount = remaining_credit_amount + partial_amount
    #                 if not company_currency.is_zero(credit_exchange_amount):
    #                     exchange_lines_to_fix += credit_aml
    #                     amounts_list.append({'amount_residual': credit_exchange_amount})
    #                     remaining_credit_amount -= credit_exchange_amount
    #                     if credit_currency == company_currency:
    #                         remaining_credit_amount_curr -= credit_exchange_amount
    #             else:
    #                 # Create an exchange difference ensuring the rate between the residual amounts expressed in
    #                 # both foreign and company's currency is still consistent regarding the rate between
    #                 # 'amount_currency' & 'balance'.
    #                 credit_exchange_amount = partial_amount - partial_credit_amount
    #                 if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
    #                     exchange_lines_to_fix += credit_aml
    #                     amounts_list.append({'amount_residual': credit_exchange_amount})
    #                     remaining_credit_amount -= credit_exchange_amount
    #                     if credit_currency == company_currency:
    #                         remaining_credit_amount_curr -= credit_exchange_amount
    #
    #         if exchange_lines_to_fix:
    #             res['exchange_values'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
    #                 amounts_list,
    #                 exchange_date=max(
    #                     debit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
    #                     credit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
    #                 ),
    #             )
    #
    #     # ==== Create partials ====
    #
    #     remaining_debit_amount -= partial_amount
    #     remaining_credit_amount += partial_amount
    #     remaining_debit_amount_curr -= partial_debit_amount_currency
    #     remaining_credit_amount_curr += partial_credit_amount_currency
    #
    #     res['partial_values'] = {
    #         'amount': partial_amount,
    #         'debit_amount_currency': partial_debit_amount_currency,
    #         'credit_amount_currency': partial_credit_amount_currency,
    #         'debit_move_id': debit_aml.id,
    #         'credit_move_id': credit_aml.id,
    #     }
    #
    #     debit_values['amount_residual'] = remaining_debit_amount
    #     debit_values['amount_residual_currency'] = remaining_debit_amount_curr
    #     credit_values['amount_residual'] = remaining_credit_amount
    #     credit_values['amount_residual_currency'] = remaining_credit_amount_curr
    #
    #     if debit_fully_matched:
    #         res['debit_values'] = None
    #     if credit_fully_matched:
    #         res['credit_values'] = None
    #     return res
