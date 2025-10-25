from odoo import fields, models, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields):
        defaults = super(AccountPaymentRegister, self).default_get(fields)
        if self.env.context.get('from_visit'):
            if 'line_ids' in defaults and defaults['line_ids'] and len(defaults['line_ids']) > 0 and len(
                    defaults['line_ids'][0][2]) > 1:
                defaults['group_payment'] = True
        return defaults

    def action_create_payments(self):
        if self.env.context.get('visit_id'):
            visit_record = self.env['fsm.order'].browse(int(self.env.context.get('visit_id')))
            visit_record.sudo().write({'invoice_lines': self.line_ids})
        return super().action_create_payments()

    def _create_payments(self):
        if self.line_ids:
            invoice_ids = self.line_ids.mapped('move_id')
            payemnts = super(AccountPaymentRegister,self.with_context(invoice_bill_move_ids=invoice_ids))._create_payments()
        else:
            payemnts = super(AccountPaymentRegister,self)._create_payments()

        if self.env.context.get('visit_id'):
            payemnts.sudo().write({'visit_id': int(self.env.context.get('visit_id'))})
        return payemnts
