from odoo import fields, models, _, api

class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('division_head_confirm','Division Head Confirm'),
            ('scm_approve','SCM approve'),
            ('finance_approve','Financial Dep approve'),
            ('confirmed', 'Confirmed'),
            ('done', 'Closed'),
            ('cancel', 'Cancelled')
        ],
        string='Status', tracking=True, required=True,
        copy=False, default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        records =  super().create(vals_list)
        for record in records:
            if record.requisition_type == 'blanket_order':
                users = self.env.ref('gulfco_contact_registration_custom.group_div_head_approval').users
                # for user in users:
                #     activity_message = _("Rental Order is created please confirm")
                #     record.activity_schedule(
                #         'gulfco_approval_custom.mail_act_purchase_requisition',
                #         user_id=user.id,
                #         note=activity_message,
                #     )
        return records

    def action_division_head_confirm(self):
        # mail_activity = self.env['mail.activity'].search([
        #     ('activity_type_id', '=', self.env.ref('gulfco_approval_custom.mail_act_purchase_requisition').id),
        #     ('res_model_id', '=', self.env.ref('gulfco_approval_custom.model_purchase_requisition').id),
        #     ('res_id', '=', self.id)
        # ])
        # mail_activity.action_done()
        self.state = 'division_head_confirm'
        # users = self.env.ref('gulfco_contact_registration_custom.group_scm_approval').users
        # for user in users:
        #     activity_message = _("Need to Approve by SCM Approval")
        #     self.activity_schedule(
        #         'gulfco_approval_custom.mail_act_purchase_requisition',
        #         user_id=user.id,
        #         note=activity_message,
        #     )


    def action_scm_approve(self):
        # mail_activity = self.env['mail.activity'].search([
        #     ('activity_type_id', '=', self.env.ref('gulfco_approval_custom.mail_act_purchase_requisition').id),
        #     ('res_model_id', '=', self.env.ref('gulfco_approval_custom.model_purchase_requisition').id),
        #     ('res_id', '=', self.id)
        # ])
        # mail_activity.action_done()
        self.state = 'scm_approve'
        # users = self.env.ref('account.group_account_manager').users
        # for user in users:
        #     activity_message = _("Need to Approve by Finance Approval")
        #     self.activity_schedule(
        #         'gulfco_approval_custom.mail_act_purchase_requisition',
        #         user_id=user.id,
        #         note=activity_message,
        #     )

    def action_finance_approve(self):
        # mail_activity = self.env['mail.activity'].search([
        #     ('activity_type_id', '=', self.env.ref('gulfco_approval_custom.mail_act_purchase_requisition').id),
        #     ('res_model_id', '=', self.env.ref('gulfco_approval_custom.model_purchase_requisition').id),
        #     ('res_id', '=', self.id)
        # ])
        # mail_activity.action_done()
        self.state = 'finance_approve'
