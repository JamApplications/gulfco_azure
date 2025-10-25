from odoo import fields, models, api, _, Command
from datetime import date
from odoo.exceptions import ValidationError,UserError
from dateutil.relativedelta import relativedelta



class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_normal_payment =fields.Boolean()

    def action_create_payments(self):
        for rec in self:
            rec.is_normal_payment = True
        self.write({"is_normal_payment": True})
        payment = super().action_create_payments()
        return payment

    def _create_payment_vals_from_wizard(self, batch_result):
        batch_result['is_normal_payment'] = True
        # 1) Let Odoo assemble its usual vals
        vals = super()._create_payment_vals_from_wizard(batch_result)
        # 2) Stamp on your flag
        vals['is_normal_payment'] = True
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        batch_result['is_normal_payment'] = True
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals['is_normal_payment'] = True
        return vals