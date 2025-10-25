from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentPdcBounce(models.TransientModel):
    _inherit = 'account.payment.pdc.bounce'

    custodian_id = fields.Many2one('custodian', string='Custodian')

    def action_bounce_pdc(self):
        super().action_bounce_pdc()
        if self.custodian_id and self.payment_id:
            self.payment_id.sudo().write({'custodian_id':self.custodian_id.id,'responsible_id':self.custodian_id.responsible_custodian.id or False})