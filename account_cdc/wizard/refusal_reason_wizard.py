from odoo import models, fields, _
from odoo.exceptions import ValidationError


class ChequeRefusalWizard(models.TransientModel):
    
    _name = 'cheque.refusal.wizard'
    
    cancel_id = fields.Many2one('cheque.cancel.reason', string="Cancel Reason")

    def action_refuse(self):
        order = self.env['account.payment'].browse(self.env.context['active_id'])
        msg = _('The Order could not be Approved for the following reason: %s'%self.cancel_id.name)
        order.message_post(body=msg)
        order._action_cancel_cdc(self.cancel_id)
        