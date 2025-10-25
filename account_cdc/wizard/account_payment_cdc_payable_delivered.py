from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentCdcPayableDelivered(models.TransientModel):
    _name = 'account.payment.cdc.payable.delivered'
    _description = 'Account Payment CDC Payable Delivered Wizard'

    delivered_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )

    def action_delivered_cdc_payable(self):
        """ delivered cdc payable """
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        payment = self.env[active_model].browse(active_ids)
        payment.action_delivered_cdc_payable(
                delivered_date=self.delivered_date,
            )
