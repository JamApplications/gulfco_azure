from odoo import api, fields, models
from datetime import date


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    payment_count = fields.Integer(compute="compute_payment_count")
    payment_ids = fields.One2many('account.payment','visit_id',string="Payments")

    @api.depends('payment_ids')
    def compute_payment_count(self):
        for record in self:
            if self.payment_ids:
                record.payment_count = len(self.payment_ids)
            else:
                record.payment_count = 0

    def action_collection(self):
        # action = self.env["ir.actions.act_window"]._for_xml_id(
        #     "account.action_move_out_invoice"
        # )
        # action["domain"] = [("move_type", "=", 'out_invoice'), ('payment_state', 'in', ['not_paid', 'paid']),
        #                     ('partner_id', '=', self.customer_id.id)]
        # action['context'] = {'search_default_out_invoice': 1, 'default_move_type': 'out_invoice', 'from_visit': 1,
        #                      'visit_id': self.id}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [("move_type", "=", 'out_invoice'),('state','=','posted'),('payment_state', 'in', ['paid','not_paid']),
                            ('partner_id', '=', self.customer_id.id)],
            'context': {'search_default_out_invoice': 1, 'default_move_type': 'out_invoice', 'from_visit': 1,
                             'visit_id': self.id}
        }
        # return action

    def action_outstanding(self):
        memo = 'Outstanding payment by ' + (self.person_id_partner.name or '') + ' ' + date.today().strftime('%Y-%m-%d')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_ids': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_partner_id': self.customer_id.id or False,
                        'default_exchange_office_id': self.person_id_partner.id or False,
                        'default_payment_type': 'inbound', 'default_memo': memo,'default_visit_id': self.id}
        }

    def action_view_payments(self):
        action =  self.env["ir.actions.act_window"]._for_xml_id("account_pdc.action_account_payments")
        action["domain"] = [("visit_id", "=", self.id)]
        return action



