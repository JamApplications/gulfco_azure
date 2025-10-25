from odoo import models, fields, api
from odoo.exceptions import UserError



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    amount_local = fields.Monetary(currency_field='local_currency_id', compute='_compute_local_amount')
    local_currency_id = fields.Many2one('res.currency',  default=lambda self: self.env.company.currency_id.id)


    @api.depends('amount','currency_id', 'company_id','rate' ,'local_currency_id', 'date')
    def _compute_local_amount(self):
        for payment in self:
            default_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=payment.currency_id,
                to_currency=payment.local_currency_id,
                company=payment.company_id,
                date=payment.date,
            )
            if payment.is_exchange and payment.rate:
                payment.amount_local = payment.amount * payment.rate

            else:
                payment.amount_local = payment.amount * default_rate



