from odoo import api, fields, models, _, Command


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != "posted" or move.payment_state not in ("not_paid", "partial") or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids.filtered(lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable"))

            domain = [
                "|",
                ("account_id", "in", pay_term_lines.account_id.ids),
                "|",
                ("account_id", "=", move.partner_id.advance_account_receivable_id.id),
                ("account_id", "=", move.partner_id.advance_account_payable_id.id),
                ("parent_state", "=", "posted"),
                ("partner_id", "=", move.commercial_partner_id.id),
                ("reconciled", "=", False),
                "|",
                ("amount_residual", "!=", 0.0),
                ("amount_residual_currency", "!=", 0.0),
            ]

            payments_widget_vals = {"outstanding": True, "content": [], "move_id": move.id}

            if move.is_inbound():
                domain.append(("balance", "<", 0.0))
                payments_widget_vals["title"] = _("Outstanding credits")
            else:
                domain.append(("balance", ">", 0.0))
                payments_widget_vals["title"] = _("Outstanding debits")

            for line in self.env["account.move.line"].search(domain):

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
        adv_line_id = lines

        lines += self.line_ids.filtered(lambda line: line.account_id.account_type == lines[0].account_id.account_type and not line.reconciled)

        res = lines.reconcile()

        receivable_line_ids = self.line_ids
        receivable_account_id = self.partner_id.property_account_receivable_id

        amount_reconciled = sum(receivable_line_ids.mapped("balance")) - sum(receivable_line_ids.mapped("amount_residual"))

        advance_payment_id = adv_line_id.payment_id
        advance_payment_journal = self.env["account.journal"].search([("code", "=", "ADVP"), ("company_id", "=", self.company_id.id)])

        if advance_payment_id and advance_payment_id.advance_sale_purchase and advance_payment_journal:

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
                    # 'ref': label_name,
                    "journal_id": advance_payment_journal.id,
                    "line_ids": line_ids,
                }
                move_id = self.env["account.move"].create(move_vals)
                move_id.action_post()

        return res
