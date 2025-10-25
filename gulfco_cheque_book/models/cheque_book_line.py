# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ChequeBookLine(models.Model):
    _name = "cheque.book.line"
    _description = "Cheque Book Line"
    _order = "cheque_number_numeric asc"
    _rec_name = "cheque_number"

    cheque_number = fields.Char(
        string="Cheque Number", required=True, copy=False, default="/"
    )
    cheque_book_id = fields.Many2one(
        "cheque.book", string="Cheque Book", required=True, ondelete="cascade"
    )
    bank_id = fields.Many2one("res.bank", string="Bank", required=False)
    journal_id = fields.Many2one(
        "account.journal", string="Bank Journal", required=True
    )
    issue_date = fields.Date(string="Issue Date")
    due_date = fields.Date(string="Due Date")
    partner_id = fields.Many2one("res.partner", string="Partner")
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: (
            self.journal_id.currency_id.id
            if self.journal_id
            else self.env.company.currency_id.id
        ),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("available", "Available"),
            ("issued", "Issued"),
            ("cleared", "Cleared"),
            ("cancelled", "Cancelled"),
            ("bounced", "Bounced"),
        ],
        default="draft",
        string="Status",
        required=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Linked Payment",
        domain="[('payment_mode', '=', 'pdc'), ('payment_type', '=', 'outbound'), ('partner_id', '=', partner_id), ('journal_id', '=', journal_id), ('pdc_state', 'in', ['draft', 'registered'])]",
        copy=False,
    )
    payment_mode = fields.Selection(related="payment_id.payment_mode", store=True)
    notes = fields.Text(string="Notes/Memo")
    cheque_number_numeric = fields.Integer(string="Cheque Number (Numeric)", copy=False)

    _sql_constraints = [
        (
            "unique_cheque_number_per_book_journal",
            "unique(cheque_number, cheque_book_id, journal_id)",
            "Cheque number must be unique within the same cheque book and journal!"
        ),
    ]

    @api.constrains("state", "partner_id", "amount", "due_date")
    def _check_issued_cheque_data(self):
        """Ensure issued cheques have required data"""
        for rec in self:
            if rec.state in ["issued", "cleared"]:
                if not rec.partner_id:
                    raise ValidationError(_("Partner is required to issue a cheque."))
                if not rec.amount:
                    raise ValidationError(_("Amount is required to issue a cheque."))
                if not rec.due_date:
                    raise ValidationError(_("Due Date is required to issue a cheque."))

            if rec.state == "cleared" and not rec.issue_date:
                raise ValidationError(_("Issue Date is required to clear the cheque."))

    @api.onchange("payment_id")
    def _onchange_payment_id(self):
        if self.payment_id:
            self.payment_id.cheque_book_line_id = self.id

    def button_validate(self):
        """Validate the cheque, changing its state to available."""
        for rec in self:
            if rec.state != "draft":
                raise ValidationError(_("Only draft cheques can be validated."))
            rec.state = "available"

    def action_set_issued(self):
        """Set the cheque as issued, creating a linked payment if necessary."""
        for rec in self:
            if rec.state != "available":
                raise ValidationError(_("Only available cheques can be issued."))
            if not rec.partner_id or not rec.amount or not rec.due_date:
                raise ValidationError(_("Partner, Amount, and Due Date are required."))
            # Create a new payment record if not already linked
            pdc_payment_method_line_id = self.env["account.payment.method.line"].search(
                [
                    ("payment_method_id.is_pdc_method", "=", True),
                    ("journal_id", "=", rec.journal_id.id),
                    ("payment_type", "=", "outbound"),
                ],
                limit=1,
            )
            if not rec.payment_id:
                # Create a new payment record
                payment_vals = {
                    "payment_type": "outbound",
                    "partner_type": "supplier",
                    "is_pdc_payable": True,
                    "partner_id": rec.partner_id.id,
                    "amount": rec.amount,
                    "date": rec.issue_date or fields.Date.today(),
                    "due_date": rec.due_date,
                    "journal_id": rec.journal_id.id,
                    "cheque_book_line_id": rec.id,
                    "payment_method_line_id": (
                        pdc_payment_method_line_id.id
                        if pdc_payment_method_line_id
                        else False
                    ),
                }
                payment = self.env["account.payment"].create(payment_vals)
                payment.action_post()
                rec.payment_id = payment.id
            else:
                # If already linked, ensure the payment details match
                if (
                    rec.payment_id.amount
                    and rec.payment_id.amount != rec.amount
                    or rec.payment_id.due_date
                    and rec.payment_id.due_date != rec.due_date
                    or rec.payment_id.partner_id
                    and rec.payment_id.partner_id != rec.partner_id
                ):
                    raise ValidationError(
                        _(
                            "Payment details like amount, due_date, partner must match cheque details."
                        )
                    )
                if (
                    rec.payment_id.cheque_book_line_id
                    and rec.payment_id.cheque_book_line_id != rec
                ):
                    raise ValidationError(
                        _("Selected payment is already linked to another cheque.")
                    )
                if not rec.issue_date:
                    rec.issue_date = fields.Date.today()
                # Update the payment with cheque details
                # This will also set the payment_id on the cheque book line
                # to link the payment with the cheque
                rec.payment_id.write(
                    {
                        "amount": rec.amount,
                        "due_date": rec.due_date,
                        "partner_id": rec.partner_id.id,
                        "date": rec.issue_date or fields.Date.today(),
                        "cheque_book_line_id": rec.id,
                    }
                )
                # Confirm the payment, this will generate the journal entries
                if payment.pdc_state in ['draft', 'registered'] or payment.cdc_state in ['draft', 'registered']:
                    rec.payment_id.action_post()
            rec.state = "issued"
            rec.issue_date = fields.Date.today()

    def action_set_cleared(self):
        for rec in self:
            if rec.state != "issued":
                raise ValidationError(_("Only issued cheques can be cleared."))
            # Clear the PDC payable
            if not rec._context.get("cleared_from_payment", False):
                rec.payment_id.with_context(
                    action_from_cheque=True
                ).action_clear_pdc_payable(clear_date=fields.Date.today())
            rec.state = "cleared"

    def action_set_bounced(self):
        for rec in self:
            if rec.state not in ["issued", "cleared"]:
                raise ValidationError(_("Only issued cheques can be bounced."))
            # Bounce the PDC payable
            if not self._context.get("action_from_payment", False):
                rec.payment_id.with_context(
                    bounced_from_cheque=True
                ).action_pdc_payable_bounce_cancel()
            rec.state = "bounced"

    def action_set_cancelled(self):
        for rec in self:
            if rec.state not in ("available", "issued"):
                raise ValidationError(
                    _("Only available or issued cheques can be cancelled.")
                )
            if rec.payment_id and not self._context.get("action_from_payment", False):
                # Bounce the PDC payable
                rec.payment_id.with_context(
                    bounced_from_cheque=True
                ).action_pdc_payable_bounce_cancel()
            rec.state = "cancelled"

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "available"):
                raise ValidationError(
                    _("Cannot delete cheque that is not in draft or available state.")
                )
        return super().unlink()

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.payment_id:
                if (
                    rec.payment_id.cheque_book_line_id
                    and rec.payment_id.cheque_book_line_id != rec
                ):
                    rec.payment_id.cheque_book_line_id = rec.id
                elif not rec.payment_id.cheque_book_line_id:
                    rec.payment_id.cheque_book_line_id = rec.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle cheque creation with proper naming"""
        # Generate names for all records
        for vals in vals_list:
            if vals.get("cheque_number", _("New")) != _("New"):
                vals["cheque_number"] = self._generate_cheque_line_name(vals)

        records = super().create(vals_list)
        for rec in records:
            if rec.payment_id:
                if (
                    rec.payment_id.cheque_book_line_id
                    and rec.payment_id.cheque_book_line_id != rec
                ):
                    rec.payment_id.cheque_book_line_id = rec.id
                elif not rec.payment_id.cheque_book_line_id:
                    rec.payment_id.cheque_book_line_id = rec.id
        return records

    def _generate_cheque_line_name(self, vals=None):
        """Generate a 6-digit padded cheque number as name"""
        if vals is None:
            vals = {}

        cheque_number = vals.get("cheque_number", self.cheque_number if self else "")

        if cheque_number:
            try:
                return str(int(cheque_number)).zfill(6)
            except Exception:
                return cheque_number  # fallback if not numeric

        return ""
    
        # """Generate a meaningful name for the cheque line"""
        # if vals is None:
        #     vals = {}

        # # Get required info
        # cheque_number = vals.get("cheque_number", self.cheque_number if self else "")
        # bank_id = vals.get("bank_id", self.bank_id.id if self else False)
        # journal_id = vals.get("journal_id", self.journal_id.id if self else False)
        # cheque_book_id = vals.get(
        #     "cheque_book_id", self.cheque_book_id.id if self else False
        # )

        # name_parts = ["CHQ"]

        # # Add current month and year
        # month_year = fields.Date.today().strftime("%Y")
        # name_parts.append(month_year)

        # # Add bank code
        # if bank_id:
        #     bank = self.env["res.bank"].browse(bank_id)
        #     if bank.exists():
        #         bank_code = bank.bic[:3] if bank.bic else bank.name[:3].upper()
        #         name_parts.append(bank_code)

        # # Add journal code
        # if journal_id:
        #     journal = self.env["account.journal"].browse(journal_id)
        #     if journal.exists():
        #         name_parts.append(journal.code)

        # # Add cheque number
        # # Zero-padding logic for cheque number
        # pad_length = 2
        # if cheque_book_id:
        #     cheque_book = self.env["cheque.book"].browse(cheque_book_id)
        #     try:
        #         total = int(cheque_book.end_number) - int(cheque_book.start_number) + 1
        #         pad_length = len(str(total))
        #     except Exception:
        #         pad_length = 2
        # # Add cheque number, zero-padded
        # if cheque_number:
        #     try:
        #         num = int(cheque_number)
        #         name_parts.append(str(num).zfill(pad_length))
        #     except Exception:
        #         name_parts.append(cheque_number)

        # return "/".join(name_parts)

    @api.depends("cheque_number")
    def _compute_cheque_number_numeric(self):
        for rec in self:
            # Extract the last segment after the last slash and convert to int if possible
            try:
                rec.cheque_number_numeric = int(str(rec.cheque_number).split("/")[-1])
            except Exception:
                rec.cheque_number_numeric = 0

    def name_get(self):
        """Override name_get to show more meaningful names in dropdowns"""
        result = []
        for rec in self:
            name = rec.display_name or rec.cheque_number or _("New Cheque")
            result.append((rec.id, name))
        return result

    # @api.constrains("payment_id", "amount", "due_date", "partner_id", "issue_date")
    # def _check_payment_link_consistency(self):
    #     for rec in self:
    #         if rec.payment_id:
    #             if rec.amount != rec.payment_id.amount:
    #                 raise ValidationError(
    #                     _("Cheque amount and linked payment amount must match.")
    #                 )
    #             if (
    #                 rec.due_date
    #                 and rec.payment_id.due_date
    #                 and rec.due_date != rec.payment_id.due_date
    #             ):
    #                 raise ValidationError(
    #                     _("Cheque due date and linked payment due date must match.")
    #                 )
    #             if (
    #                 rec.partner_id
    #                 and rec.payment_id.partner_id
    #                 and rec.partner_id != rec.payment_id.partner_id
    #             ):
    #                 raise ValidationError(
    #                     _("Cheque partner and linked payment partner must match.")
    #                 )
    #             if (
    #                 rec.issue_date
    #                 and rec.payment_id.date
    #                 and rec.issue_date != rec.payment_id.date
    #             ):
    #                 raise ValidationError(
    #                     _("Cheque issue date and linked payment date must match.")
    #                 )

    def action_open_related_payment(self):
        self.ensure_one()
        if not self.payment_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Payment"),
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_related_journal_entries(self):
        self.ensure_one()
        if not self.payment_id:
            return False
        # Use the payment's built-in method to open journal entries
        return self.payment_id.button_open_journal_entry()

    @api.model
    def auto_clear_due_cheques(self):
        today = fields.Date.today()
        cheques = self.search(
            [
                ("state", "=", "issued"),
                ("due_date", "!=", False),
                ("due_date", "=", today),
                ("payment_id", "!=", False),
                ("payment_mode", '!=', 'cdc')
            ]
        )
        for cheque in cheques:
            try:
                cheque.action_set_cleared()
            except Exception as e:
                # Optionally log or handle errors
                _logger.info(
                    f"Failed to auto-clear cheque {cheque.cheque_number}: {str(e)}"
                )
