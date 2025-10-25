# -*- coding: utf-8 -*-

from odoo import api, models,fields


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    is_pdc_method = fields.Boolean(string="Is PDC Method")
    is_cdc_method = fields.Boolean(string="Is CDC Method")
    is_monthly_pdc = fields.Boolean(string="Is Monthly PDC")
    type = fields.Selection([('bank','Bank'),('cash','Cash'),('credit','Credit')],default="bank",string="Type")
    is_pay_by_link = fields.Boolean(string="Is PayByLink")

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        existing_payment_method_code_list = []
        if isinstance(res, dict):
            existing_payment_method_code_list = list(res.keys())
        else:
            res = {}
        payment_methods = self.env['account.payment.method'].sudo().search([('code','not in',existing_payment_method_code_list)])
        if payment_methods:
            payment_method_codes = set(payment_methods.mapped('code'))
            for code in payment_method_codes:
                types = payment_methods.filtered(lambda s:s.code == code).mapped('type')
                for type in types:
                    res[code] = {'mode': 'multi','type': (type,)}
        return res