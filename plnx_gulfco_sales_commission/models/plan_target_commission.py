# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models, fields, exceptions, _, api


class CommissionPlanTargetCommission(models.Model):
    _inherit = 'sale.commission.plan.target.commission'

    target_rate_from = fields.Float("Target From (%)", default=1, required=True)
    target_rate_to = fields.Float("To (%)", default=1, required=True)

    # base field override default value from 1 to 0
    target_rate = fields.Float("Target completion (%)", default=0, required=True)


    @api.onchange('target_rate_from')
    def onchange_target_rate_from(self):
        if self.target_rate_from:
            self.target_rate = self.target_rate_from


class CommissionPlanTargetForecast(models.Model):
    _inherit = 'sale.commission.plan.target.forecast'

    partner_id = fields.Many2one('res.partner', "Salesperson", required=True,
                                 domain="[('contact_type', '=', 'worker')]")




class CommissionPlanUser(models.Model):
    _inherit = 'sale.commission.plan.user'

    user_id = fields.Many2one('res.users', "Salesperson", required=False, domain="[('share', '=', False)]")
    partner_id = fields.Many2one('res.partner', "Salesperson", required=True,
                                 domain="[('contact_type', '=', 'worker')]")

    _sql_constraints = [
        ('partner_uniq', 'unique (plan_id, partner_id)', "The Contact is already present in the plan"),
    ]

    @api.depends('partner_id', 'plan_id.date_from', 'plan_id.date_to', 'date_from', 'date_to')
    def _compute_other_plans(self):
        plan_ids = self.search([
            ('partner_id', 'in', self.partner_id.ids),
            ('plan_id.state', 'in', ['draft', 'approved']),
        ]).plan_id
        for pu in self:
            pu_date_from = pu.date_from or pu.plan_id.date_from
            pu_date_to = pu.date_to or pu.plan_id.date_to
            other_plans_ids = []
            for plan in (plan_ids - pu.plan_id._origin - pu.plan_id):
                if plan.date_to < pu_date_from or plan.date_from > pu_date_to:
                    # no overlap
                    continue
                other_plans_ids.append(plan.id)
            pu.other_plans = [Command.clear()] if not other_plans_ids else [Command.set(other_plans_ids)]
