from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentCdcBounce(models.TransientModel):
    _inherit = 'account.payment.cdc.bounce'

    custodian_id = fields.Many2one('custodian', string='Custodian')

    def action_bounce_cdc(self):
        super().action_bounce_cdc()
        if self.custodian_id and self.payment_ids and len(self.payment_ids) > 1:
            self.payment_ids.sudo().write({'custodian_id':self.custodian_id.id,'responsible_id':self.custodian_id.responsible_custodian.id or False})
        elif self.custodian_id and self.payment_id:
            self.payment_id.sudo().write({'custodian_id':self.custodian_id.id,'responsible_id':self.custodian_id.responsible_custodian.id or False})