# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# from zeep.exceptions import ValidationError
from odoo.exceptions import ValidationError
from odoo import api, fields, models,_
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('submitted', 'Submitted'),
        ('sent', 'RFQ Sent'),
        ("scm_confirm","SCM Approved"),
        ("financial_dep_approve","Financial approved"),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    po_approve_by = fields.Many2one('res.users', copy=False)

    def action_submit_po(self):
        if not self.order_line:
            raise UserError(_("Please Add Product Line."))
        self.state = 'submitted'

    def action_reject(self):
        if not self.order_line:
            raise UserError(_("Please Add Product Line."))
        if self.po_category == 'foreign':
            self.state = 'reject'
        else:
            raise ValidationError("Reject only work on FPO type order!")


    def button_confirm(self):
        if not self.order_line:
            raise UserError(_("Please Add Product Line."))
        if self.state == 'submitted':
            self.state = 'draft'
        return super(PurchaseOrder, self).button_confirm()

    def action_scm_confirm(self):
        if not self.order_line:
            raise UserError(_("Please Add Product Line."))
        self.order_line._validate_analytic_distribution()
        self.state = 'scm_confirm'
        # users = self.env.ref('account.group_account_manager').users
        # for user in users:
        #     activity_message = _("Need to Approve by Finance Approval")
        #     self.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         user_id=user.id,
        #         note=activity_message,
        #     )

    def action_finance_approve(self):
        # mail_activity = self.env['mail.activity'].search([
        #     ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        #     ('res_model_id', '=', self.env.ref('gulfco_approval_custom.model_purchase_order').id),
        #     ('res_id', '=', self.id)
        # ])
        # mail_activity.action_done()
        self.state = 'financial_dep_approve'
        # users = self.env.ref('stock_inventory_adjustment.group_director_approval').users
        # for user in users:
        #     activity_message = _("Need to Approve by Director Approval")
        #     self.activity_schedule(
        #         'mail.mail_activity_data_todo',
        #         user_id=user.id,
        #         note=activity_message,
        #     )

    def action_director_approve(self):
        # mail_activity = self.env['mail.activity'].search([
        #     ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        #     ('res_model_id', '=', self.env.ref('gulfco_approval_custom.model_purchase_order').id),
        #     ('res_id', '=', self.id)
        # ])
        # mail_activity.action_done()
        self.state = 'draft'
        if self.env.uid:
            self.po_approve_by = self.env.uid
        return self.button_confirm()




