# -*- coding: utf-8 -*-
from collections import Counter
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ChequeBook(models.Model):
    _name = "cheque.book"
    _description = "Cheque Book"
    _order = "issue_date desc, id desc"

    bank_id = fields.Many2one("res.bank", string="Bank", required=False)
    journal_id = fields.Many2one(
        "account.journal",
        string="Bank Journal",
        required=True,
        domain="[('type','=','bank')]",
    )
    start_number = fields.Char(string="Start Cheque Number", required=True)
    end_number = fields.Char(string="End Cheque Number", required=True)
    issue_date = fields.Date(string="Issue Date", required=True)
    cheque_lines_ids = fields.One2many(
        "cheque.book.line", "cheque_book_id", string="Cheque Lines"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_use", "In Use"),
            ("used_up", "Used Up"),
        ],
        default="draft",
        string="Status",
        required=True,
        compute="_compute_state",
        store=True,
    )
    available_cheques_count = fields.Integer(
        string="Available Cheques",
        compute="_compute_cheques_count",
        store=True,
        help="Count of cheques that are available for use.",
    )
    issued_cheques_count = fields.Integer(
        string="Issued Cheques",
        compute="_compute_cheques_count",
        store=True,
        help="Count of cheques that have been issued.",
    )
    bounced_cheques_count = fields.Integer(
        string="Bounced Cheques",
        compute="_compute_cheques_count",
        store=True,
        help="Count of cheques that have bounced.",
    )
    cancelled_cheques_count = fields.Integer(
        string="Cancelled Cheques",
        compute="_compute_cheques_count",
        store=True,
        help="Count of cheques that have been cancelled.",
    )
    cleared_cheques_count = fields.Integer(
        string="Cleared Cheques",
        compute="_compute_cheques_count",
    )    
    draft_cheques_count = fields.Integer(
        string="Draft Cheques",
        compute="_compute_cheques_count",
        store=True,
        help="Count of cheques that are still in draft state.",
    )
    name = fields.Char(string="Name", required=True)

    @api.constrains("start_number", "end_number")
    def _check_sequential_range(self):
        for rec in self:
            if (
                rec.start_number
                and rec.end_number
                and int(rec.start_number) >= int(rec.end_number)
            ):
                raise ValidationError(_("Start number must be less than end number."))

    def action_generate_cheques(self):
        for rec in self:
            if rec.cheque_lines_ids:
                raise ValidationError(_("Cheque lines already generated."))
            start = int(rec.start_number)
            end = int(rec.end_number)

            # Bulk create cheque lines
            cheque_vals_list = []
            for num in range(start, end + 1):
                cheque_vals_list.append(
                    {
                        "cheque_number_numeric": num,
                        "cheque_number": str(num),
                        "cheque_book_id": rec.id,
                        "bank_id": rec.bank_id.id if rec.bank_id else False,
                        "journal_id": rec.journal_id.id,
                        "state": "available",
                    }
                )
            self.env["cheque.book.line"].create(cheque_vals_list)
            rec.state = "in_use"

    @api.depends("cheque_lines_ids.state")
    def _compute_state(self):
        for rec in self:
            if not rec.cheque_lines_ids:
                # No cheque lines generated yet
                rec.state = "draft"
                continue

            issued_cheques_count = rec.issued_cheques_count
            bounced_cheques_count = rec.bounced_cheques_count
            cancelled_cheques_count = rec.cancelled_cheques_count
            cleared_cheques_count = rec.cleared_cheques_count

            total_cheques = len(rec.cheque_lines_ids)

            # Define final states (cheques that cannot be used anymore)
            final_states = (
                cleared_cheques_count
                + cancelled_cheques_count
                + bounced_cheques_count
            )

            # State computation logic:
            if final_states == total_cheques:
                # All cheques are in final states (cleared/cancelled/bounced)
                rec.state = "used_up"
            elif (
                issued_cheques_count > 0
                or cleared_cheques_count > 0
                or cancelled_cheques_count > 0
                or bounced_cheques_count > 0
            ):
                # At least one cheque has been issued or is in a post-issue state
                rec.state = "in_use"
            else:
                # All cheques are still in draft/available state
                rec.state = "draft"

    @api.depends("cheque_lines_ids.state")
    def _compute_cheques_count(self):
        for rec in self:
            states = rec.cheque_lines_ids.mapped("state")
            counts = Counter(states)

            rec.available_cheques_count = counts.get("available", 0)
            rec.issued_cheques_count = counts.get("issued", 0)
            rec.bounced_cheques_count = counts.get("bounced", 0)
            rec.cancelled_cheques_count = counts.get("cancelled", 0)
            rec.cleared_cheques_count = counts.get("cleared", 0)
            rec.draft_cheques_count = counts.get("draft", 0)

    def unlink(self):
        for rec in self:
            # Check if any cheque line is beyond the available state
            if any(
                line.state not in ("draft", "available")
                for line in rec.cheque_lines_ids
            ):
                raise ValidationError(
                    _(
                        "Cannot delete cheque book with issued/cleared/cancelled/bounced cheques."
                    )
                )
        return super().unlink()

    def action_view_available_cheques(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Available Cheques"),
            "res_model": "cheque.book.line",
            "view_mode": "list,form",
            "domain": [("cheque_book_id", "=", self.id), ("state", "=", "available")],
            "context": dict(self.env.context),
        }

    def action_view_issued_cheques(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Issued Cheques"),
            "res_model": "cheque.book.line",
            "view_mode": "list,form",
            "domain": [("cheque_book_id", "=", self.id), ("state", "=", "issued")],
            "context": dict(self.env.context),
        }

    def action_view_bounced_cheques(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Bounced Cheques",
            "res_model": "cheque.book.line",
            "view_mode": "list,form",
            "domain": [("cheque_book_id", "=", self.id), ("state", "=", "bounced")],
            "context": dict(self.env.context),
        }

    def action_view_cancelled_cheques(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Cancelled Cheques",
            "res_model": "cheque.book.line",
            "view_mode": "list,form",
            "domain": [("cheque_book_id", "=", self.id), ("state", "=", "cancelled")],
            "context": dict(self.env.context),
        }

    def action_view_cleared_cheques(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cleared Cheques"),
            "res_model": "cheque.book.line",
            "view_mode": "list,form",
            "domain": [("cheque_book_id", "=", self.id), ("state", "=", "cleared")],
            "context": dict(self.env.context),
        }
