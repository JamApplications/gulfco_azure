from odoo import api, fields, models, _
from odoo.exceptions import UserError

_STATES = [
    ("draft", "Draft"),
    ("division_head_confirm","Division Head Confirm"),
    ("scm_approve","SCM approve"),
    ("financial_dep_approve","Financial Dep approve"),
    ("scd_approve","SCD Approve"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]

class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    pr_line_category = fields.Selection([('foreign', 'FPO'), ('local', 'LPO')], string='PR Category',compute="compute_pr_line_category",store=True,readonly=False)
    to_approve_allowed = fields.Boolean(compute="_compute_to_approve_allowed")
    scd_approver_id = fields.Many2one('res.users',string="SCD Approver")
    is_sdm_manager = fields.Boolean(compute="compute_is_sdm_manager")
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )

    @api.depends("state", "product_qty", "cancelled")
    def _compute_to_approve_allowed(self):
        for rec in self:
            rec.to_approve_allowed = rec.state == "draft" and not rec.cancelled and rec.product_qty

    def to_approve_allowed_check(self):
        for rec in self:
            if not rec.to_approve_allowed:
                raise UserError(_(
                        "You can't request an approval for a purchase request "
                        "which is empty"
                    ))

    @api.depends('supplier_id')
    def compute_pr_line_category(self):
        for record in self:
            if record.supplier_id and record.supplier_id.supplier_type:
                record.pr_line_category = record.supplier_id.supplier_type
            else:
                record.pr_line_category = False

    def button_to_approve(self):
        self.to_approve_allowed_check()
        self.write({"state": "to_approve"})

    @api.depends_context('uid')
    def compute_is_sdm_manager(self):
        for record in self:
            if record.scd_approver_id and record.scd_approver_id.employee_id and record.scd_approver_id.employee_id.parent_id == self.env.user.employee_id:
                record.is_sdm_manager = True
            else:
                record.is_sdm_manager = False

    def action_division_head_confirm(self):
        self.state = 'division_head_confirm'

    def action_scm_approve(self):
        self.state = 'scm_approve'

    def action_finance_approve(self):
        self.state = 'financial_dep_approve'

    def action_scd_approve(self):
        self.state = 'scd_approve'
        self.scd_approver_id = self.env.user.id

    def button_approved(self):
        is_line_manager = self.env.user.has_group('gulfco_contact_registration_custom.group_line_manager')
        for record in self:
            if record.request_id.request_type != 'order_analysis' and is_line_manager:
                record.state = 'approved'
            elif record.request_id.request_type == 'order_analysis' and record.is_sdm_manager:
                record.state = 'approved'

    def button_rejected(self):
        self.state = 'rejected'
        self.do_cancel()

    def button_draft(self):
        self.do_uncancel()
        self.write({"state": "draft"})

    def button_done(self):
        return self.write({"state": "done"})