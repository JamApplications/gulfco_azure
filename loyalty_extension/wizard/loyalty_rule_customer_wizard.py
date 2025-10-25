from odoo import models, fields, api

class LoyaltyRuleCustomerWizard(models.TransientModel):
    _name = 'loyalty.rule.customer.wizard'
    _description = 'Loyalty Rule Customer Filter wizard'

    loyalty_rule_id = fields.Many2one('loyalty.rule', string='Loyalty Rule', required=True)

    customer_ids = fields.Many2many(
        'res.partner',
        'loyalty_rule_wizard_rel', 'wizard_id', 'partner_id',
        string='Customers'
    )

    @api.depends('loyalty_rule_id')
    def _compute_initial_customer_ids(self):
        for wizard in self:
            wizard.initial_customer_ids = wizard.loyalty_rule_id.customer_ids

    def action_remove_selected_customers(self):
        self.ensure_one()
        self.loyalty_rule_id.customer_ids = [(3, cid) for cid in self.customer_ids.ids]

    def action_add_selected_customers(self):
        self.ensure_one()
        self.loyalty_rule_id.customer_ids = [(4, cid) for cid in self.customer_ids.ids]
