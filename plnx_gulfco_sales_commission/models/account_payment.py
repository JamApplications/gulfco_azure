# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    responsible_id = fields.Many2one('res.partner', domain="[('contact_type', '=', 'worker')]",default=lambda self: self.env.user.partner_id.id)
    team_id = fields.Many2one(
        'crm.team', string='Sales Team',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def action_post(self):
        super(AccountPayment, self).action_post()
        if not self.responsible_id:
            self.responsible_id = self.env.user.partner_id.id

    @api.model
    def default_get(self, default_fields):
        rec = super(AccountPayment, self).default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda move: move.is_invoice(include_receipts=True))

        if (len(invoices) == 1):
            rec.update({
                'responsible_id': invoices.assign_to.id,
            })
        return rec


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    responsible_id = fields.Many2one('res.partner', domain="[('contact_type', '=', 'worker')]",default=lambda self: self.env.user.partner_id.id)

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super(AccountPaymentRegister, self).default_get(fields_list)


        # Retrieve moves to pay from the context.

        if self._context.get('active_model') == 'account.move':
            lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids

        elif self._context.get('active_model') == 'account.move.line':
            lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
        else:
            raise UserError(_(
                "The register payment wizard should only be called on account.move or account.move.line records."
            ))
        move = lines.mapped('move_id')
        for rec in move:
            res['responsible_id'] = rec.assign_to.id

        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        """ inherit to add other fields """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['responsible_id'] = self.responsible_id.id
        return payment_vals



    def _create_payment_vals_from_batch(self, batch_result):
        """ inherit to add other fields """
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals['responsible_id'] = self.responsible_id.id
        return payment_vals


    def action_create_payments(self):
        if self.responsible_id:
            self.write({'responsible_id': self.responsible_id.id})
        return super(AccountPaymentRegister, self).action_create_payments()



