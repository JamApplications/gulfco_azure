from odoo import models, fields, api, _

class RejectReason(models.TransientModel):
    _name = 'reject.reason'
    _description = 'Reject Rejection'

    reason = fields.Char(required=1)
    inventory_adjustment_id = fields.Many2one('stock.inventory.adjustment')

    def apply_action(self):
        if self.inventory_adjustment_id:
            message = 'Inventory Adjustment is reject reason is' + (self.reason or '')
            if self.env.context.get('from_director'):
                self.inventory_adjustment_id.director_reject_reason = self.reason
                self.inventory_adjustment_id.state = 'in_progress'
                self.inventory_adjustment_id.message_post(body=message, message_type='comment', subtype_xmlid='mail.mt_comment')
            elif self.env.context.get('from_finance'):
                self.inventory_adjustment_id.finance_reject_reason = self.reason
                self.inventory_adjustment_id.state = 'in_progress'
                self.inventory_adjustment_id.message_post(body=message, message_type='comment', subtype_xmlid='mail.mt_comment')
            elif self.env.context.get('from_sdm'):
                self.inventory_adjustment_id.sdm_reject_reason = self.reason
                self.inventory_adjustment_id.state = 'in_progress'
                self.inventory_adjustment_id.message_post(body=message, message_type='comment', subtype_xmlid='mail.mt_comment')