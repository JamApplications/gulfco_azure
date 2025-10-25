from odoo import models, fields

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.rule'

    customer_ids = fields.Many2many(
        'res.partner',
        string='Customers',
        help='Customers eligible for this loyalty program.'
    )

    def open_manage_customer_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.rule.customer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loyalty_rule_id': self.id,
            }
        }
    def action_view_customers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customers',
            'view_mode': 'list,form',
            'res_model': 'res.partner',
            'domain': [('id', 'in', self.customer_ids.ids)],
            'target': 'new',
        }


