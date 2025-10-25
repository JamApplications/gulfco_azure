from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    advance_reconcile_journal_entry = fields.Boolean('Advance Reconcile Journal Entry')


    def _compute_payments_widget_to_reconcile_info(self):
        # 1. Find all bounced PDC/CDC payments (only once)
        bounced_cheque_payments = self.env['account.payment'].search([
            '|', ('pdc_state', '=', 'bounced'),
            ('cdc_state', '=', 'bounced')
        ])        
        # 2. Gather all move_ids from those payments
        bounced_move_ids = (
            bounced_cheque_payments.mapped('move_id') |
            bounced_cheque_payments.mapped('deposit_move_id') |
            bounced_cheque_payments.mapped('bounced_move_id') |
            bounced_cheque_payments.mapped('collect_payment_id.move_id') |
            bounced_cheque_payments.mapped('cheque_move_ids') |
            bounced_cheque_payments.mapped('cash_payment_id.move_id') |
            bounced_cheque_payments.mapped('write_off_payment_id') |
            bounced_cheque_payments.mapped('collection_fees_payment_id.move_id') |
            bounced_cheque_payments.mapped('recycled_payment_id.move_id') |
            bounced_cheque_payments.mapped('cleared_cdc_payable_move_id') |
            bounced_cheque_payments.mapped('delivered_cdc_payable_move_id') |
            bounced_cheque_payments.mapped('related_move_ids')
        ).ids
        
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != "posted" or move.payment_state not in ("not_paid", "partial") or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids.filtered(lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable"))
            
            # Add outstanding PDC payments to the payments widget for payment matching and reconciliation even before PDC payment is cleared.
            pdc_journals = self.env['account.journal'].search([('type', '=', 'bank'), ('is_pdc', '=', True)])
            pdc_accounts = pdc_journals.pdc_check_under_collection_account_id            
            
            cdc_journals = self.env['account.journal'].search([('type', '=', 'bank'), ('is_cdc', '=', True)])
            cdc_accounts = cdc_journals.cdc_check_under_collection_account_id
            
            # Default domain accounts
            account_ids = pay_term_lines.account_id.ids
            
            # Add advance accounts if they exist
            if move.partner_id.advance_account_receivable_id:
                account_ids.append(move.partner_id.advance_account_receivable_id.id)
            if move.partner_id.advance_account_payable_id:
                account_ids.append(move.partner_id.advance_account_payable_id.id)
                
            advance_type = 'purchase' if move.move_type in ('in_invoice', 'in_refund') else 'sale'
            advance_payments = self.env['account.payment'].search([
                ('partner_id', '=', move.commercial_partner_id.id),
                ('payment_type', 'in', ['outbound', 'inbound']),
                ('advance_sale_purchase', '=', advance_type),
                ('is_internal_transfer', '=', False),
            ])
            
            # Add PDC accounts
            if pdc_accounts:
                account_ids += pdc_accounts.ids            
            
            # Add CDC accounts
            if cdc_accounts:
                account_ids += cdc_accounts.ids
            
            domain = [
                ("account_id", "in", account_ids),
                ("parent_state", "=", "posted"),
                ("move_id.advance_reconcile_journal_entry", "=", False),
                ("partner_id", "=", move.commercial_partner_id.id),
                ("reconciled", "=", False),
                "|",
                ("amount_residual", "!=", 0.0), ("amount_residual_currency", "!=", 0.0),
            ]
            
            extra_lines = self.env['account.move.line']
            for payment in advance_payments:
                direction = -1 if move.is_inbound() else 1  # inbound: credit (balance < 0), outbound: debit (balance > 0)

                lines = payment.move_id.line_ids.filtered(
                    lambda l: (
                        not l.reconciled
                        and l.account_id.id not in account_ids
                        and l.parent_state == "posted"
                        and l.balance * direction > 0
                        and (l.amount_residual != 0 or l.amount_residual_currency != 0)
                    )
                )

                extra_lines |= lines

            payments_widget_vals = {"outstanding": True, "content": [], "move_id": move.id}

            if move.is_inbound():
                domain.append(("balance", "<", 0.0))
                payments_widget_vals["title"] = _("Outstanding credits")
            else:
                domain.append(("balance", ">", 0.0))
                payments_widget_vals["title"] = _("Outstanding debits")
                
            for line in self.env["account.move.line"].search(domain) | extra_lines:
                # Skip if cheque payment is bounced
                payment = line.payment_id
                if payment and (payment.pdc_state == 'bounced' or payment.cdc_state == 'bounced'):
                    continue                            

                if line.move_id.id in bounced_move_ids:
                    continue    

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals["content"].append(
                    {
                        "journal_name": line.ref or line.move_id.name,
                        "amount": amount,
                        "currency_id": move.currency_id.id,
                        "id": line.id,
                        "move_id": line.move_id.id,
                        "date": fields.Date.to_string(line.date),
                        "account_payment_id": line.payment_id.id,
                    }
                )

            if not payments_widget_vals["content"]:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True

    def js_assign_outstanding_line(self, line_id):
        """Called by the 'payment' widget to reconcile a suggested journal item to the present
        invoice.

        :param line_id: The id of the line to reconcile with the current invoice.
        """
        self.ensure_one()
        lines = self.env["account.move.line"].browse(line_id)
        is_advance_payment_reconcile = lines[0].move_id.is_advanced_payment or bool(lines[0].payment_id and lines[0].payment_id.advance_sale_purchase)
        adv_line_id = lines
        adv_line_amount_residual = sum(lines.mapped('amount_residual'))
        # lines += self.line_ids.filtered(lambda line: line.account_id.account_type == lines[0].account_id.account_type and not line.reconciled)

        # if not is_advance_payment_reconcile:
        if self.move_type == 'in_invoice':
            lines_reconciled_amt = sum(self.line_ids.filtered(
                lambda line: line.account_id.account_type == 'liability_payable' and not line.reconciled and line.credit > 0).mapped('amount_residual'))
            lines += self.line_ids.filtered(
                lambda line: line.account_id.account_type == 'liability_payable' and not line.reconciled and line.credit > 0)
        elif self.move_type == 'out_invoice':
            lines_reconciled_amt = sum(self.line_ids.filtered(
                lambda line: line.account_id.account_type == 'asset_receivable' and not line.reconciled).mapped('amount_residual'))
            lines += self.line_ids.filtered(
                lambda line: line.account_id.account_type == 'asset_receivable' and not line.reconciled)
        else:
            lines_reconciled_amt = sum(self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled).mapped('amount_residual'))
            lines += self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
        # if is_advance_payment_reconcile:
        #     lines_reconciled_amt = sum(self.line_ids.filtered(
        #             lambda line: line.account_id.account_type == lines[0].account_id.account_type and not line.reconciled).mapped('amount_residual'))
        #     lines += self.line_ids.filtered(
        #         lambda line: line.account_id.account_type == lines[0].account_id.account_type and not line.reconciled)
        res = lines.reconcile()


        receivable_account_id = self.partner_id.property_account_receivable_id
        payable_account_id = self.partner_id.property_account_payable_id



        advance_payment_id = adv_line_id.payment_id
        sale_advance_payment_journal = self.env["account.journal"].search([("is_advance_sale", "=", True), ("company_id", "=", self.company_id.id)],limit=1)
        purchase_advance_payment_journal = self.env["account.journal"].search([("is_advance_purchase", "=", True), ("company_id", "=", self.company_id.id)],limit=1)


        if advance_payment_id and advance_payment_id.advance_sale_purchase == 'sale' and sale_advance_payment_journal:
            label_name = self.line_ids.sale_line_ids.order_id.name if self.line_ids.sale_line_ids else None
            receivable_line_ids = self.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
            amount_reconciled = 0
            if abs(adv_line_amount_residual) < abs(lines_reconciled_amt):
                amount_reconciled = adv_line_amount_residual
            else:
                amount_reconciled = abs(lines_reconciled_amt)

            adv_receivable_account = advance_payment_id.partner_id.advance_account_receivable_id

            line_ids = [
                (
                    0,
                    0,
                    {
                        "name": f"Advance Payment: {advance_payment_id.name}",
                        "display_type": "product",
                        "account_id": adv_receivable_account.id,
                        "quantity": 1,
                        "currency_id": self.currency_id.id,
                        "debit": abs(amount_reconciled),
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": f"Advance Payment: {self[0].name}",
                        "display_type": "product",
                        "account_id": receivable_account_id.id,
                        "quantity": 1,
                        "currency_id": self.currency_id.id,
                        "credit": abs(amount_reconciled),
                    },
                ),
            ]

            if line_ids:
                move_vals = {
                    "date": fields.Date.today(),
                    "invoice_date": fields.Date.today(),
                    "move_type": "entry",
                    "advance_reconcile_journal_entry": True,
                    "partner_id": self.partner_id.id,
                    'ref': label_name,
                    "journal_id": sale_advance_payment_journal.id,
                    "line_ids": line_ids,
                }
                move_id = self.env["account.move"].create(move_vals)
                move_id.action_post()

        if advance_payment_id and advance_payment_id.advance_sale_purchase == 'purchase' and purchase_advance_payment_journal:
            label_name = self.line_ids.purchase_line_id.order_id.name if self.line_ids.purchase_line_id else None
            payable_line_ids = self.line_ids.filtered(lambda x: x.account_id.account_type == 'liability_payable')
            amount_reconciled = 0
            if abs(adv_line_amount_residual) < abs(lines_reconciled_amt):
                amount_reconciled = adv_line_amount_residual
            else:
                amount_reconciled = abs(lines_reconciled_amt)
            adv_payable_account = advance_payment_id.partner_id.advance_account_payable_id
            
            # Find the reconciled line in the advance payment move that was matched
            adv_payable_account = adv_line_id.account_id
            
            line_ids = [
                (
                    0,
                    0,
                    {
                        "name": f"Advance Payment: {adv_payable_account.name}",
                        "display_type": "product",
                        "account_id": adv_payable_account.id,
                        "quantity": 1,
                        "currency_id": self.currency_id.id,
                        "credit": abs(amount_reconciled),
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": f"Advance Payment: {self[0].name}",
                        "display_type": "product",
                        "account_id": payable_account_id.id,
                        "quantity": 1,
                        "currency_id": self.currency_id.id,
                        "debit": abs(amount_reconciled),
                    },
                ),
            ]

            if line_ids:
                move_vals = {
                    "date": fields.Date.today(),
                    "invoice_date": fields.Date.today(),
                    "move_type": "entry",
                    "advance_reconcile_journal_entry": True,
                    "partner_id": self.partner_id.id,
                    'ref': label_name,
                    "journal_id": purchase_advance_payment_journal.id,
                    "line_ids": line_ids,
                }
                move_id = self.env["account.move"].create(move_vals)
                move_id.action_post()

        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _check_amls_exigibility_for_reconciliation(self, shadowed_aml_values=None):
        """ Ensure the current journal items are eligible to be reconciled together.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        """
        if not self:
            return

        if any(aml.reconciled for aml in self):
            raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
        if any(aml.parent_state != 'posted' for aml in self):
            raise UserError(_("You can only reconcile posted entries."))
        accounts = self.mapped(lambda x: x._get_reconciliation_aml_field_value('account_id', shadowed_aml_values))
        # if len(accounts) > 1:
        # if len(set(accounts.mapped('account_type'))) > 1:
        if (
            len(accounts) > 1
            and not any(self.mapped("move_id.is_advanced_payment"))
            and not any(self.mapped("move_id.is_pdc_receivable_entry"))
            and not any(
                payment.payment_mode in ("cdc", "pdc")
                and payment.payment_type == "outbound"
                and payment.partner_type == "supplier"
                for payment in self.move_id.cheque_payment_id
            )
        ):
            raise UserError(
                _(
                    "Entries are not from the same account: %s",
                    ", ".join(accounts.mapped("display_name")),
                )
            )
        if len(self.company_id.root_id) > 1:
            raise UserError(_(
                "Entries don't belong to the same company: %s",
                ", ".join(self.company_id.mapped('display_name')),
            ))
        # if not accounts.reconcile and accounts.account_type not in ('asset_cash', 'liability_credit_card'):
        if not set(accounts.mapped('reconcile')) and set(accounts.mapped('account_type')) not in ('asset_cash', 'liability_credit_card'):
            raise UserError(_(
                "Account %s does not allow reconciliation. First change the configuration of this account "
                "to allow it.",
                accounts.display_name,
            ))
