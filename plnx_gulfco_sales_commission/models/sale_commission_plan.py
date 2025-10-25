import json
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError


class SalesCommissionPlan(models.Model):
    _inherit = "sale.commission.plan"

    @api.depends('commission_amount', 'type')
    def _compute_target_commission_ids(self):
        for plan in self:
            if plan.type != 'target':
                continue
            elif not plan.target_commission_ids:
                plan.target_commission_ids = [Command.create({
                    'plan_id': plan.id,
                    'target_rate': 0,
                    'target_rate_from':0,
                    'target_rate_to':0,
                    'amount': 0,
                }), Command.create({
                    'plan_id': plan.id,
                    'target_rate': 1,
                    'target_rate_from': 1,
                    'target_rate_to': 1,
                    'amount': plan.commission_amount or 1,
                    'amount_rate': 1,
                })]
            else:
                for target in plan.target_commission_ids:
                    target.amount = target.amount_rate * plan.commission_amount

    job_position_id = fields.Many2one('hr.job')
    commission_kpi_id = fields.Many2one('commission.kpi', required=True)
    kpi_type = fields.Selection(related='commission_kpi_id.kpi_type', store=True)
    msl_commission_report_ids = fields.One2many('msl.commission.report', 'plan_id',)


    def write(self, vals):
        res = super(SalesCommissionPlan, self).write(vals)
        if 'user_ids' in vals and self.kpi_type == 'msl_availability':
            self.generate_msl_commission_line()
        return res


    # method to generate MSl commission
    def generate_msl_commission_line(self):
        current_partner_ids = set(self.user_ids.mapped('partner_id').ids)
        existing_partner_ids = set(self.msl_commission_report_ids.mapped('partner_id').ids)

        # Users to remove
        to_remove = self.msl_commission_report_ids.filtered(lambda r: r.partner_id.id not in current_partner_ids)
        to_remove.unlink()

        # Users to add
        to_add_ids = list(current_partner_ids - existing_partner_ids)

        msl_commission_ref = self.env['msl.commission.report']
        for rec in self.target_ids:
            for part in self.env['res.partner'].search([('id', 'in', to_add_ids)]):
                msl_vals = {
                    'plan_id': self.id,
                    'target_id': rec.id,
                    'target_percentage': rec.amount_percentage,
                    'partner_id': part.id or None,
                    'team_id': self.team_id.id or None,
                    'payment_date': rec.date_to,

                }
                msl_commission_ref.create(msl_vals)

    def action_approve(self):
        res = super(SalesCommissionPlan, self).action_approve()
        self.generate_msl_commission_line()

        if self.kpi_type == 'journal_plan':
            for rec in self.target_ids:
                plan_count = self.env['fsm.order'].search_count([('scheduled_date_start', '>=', rec.date_from),
                                                           ('scheduled_date_start', '<=', rec.date_to),
                                                           ('person_id_partner', 'in', self.user_ids.mapped('partner_id').ids)])
                rec.target_plan = plan_count


        return res

    def action_draft(self):
        res = super(SalesCommissionPlan, self).action_draft()
        self.ensure_one()
        self.env['msl.commission.report'].search([('plan_id', '=', self.id)]).unlink()
        return res

    def action_open_msl_commission(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "msl.commission.report",
            "name": _("MSL commissions"),
            "views": [[self.env.ref('plnx_gulfco_sales_commission.msl_commission_list_view').id, "list"]],
            "domain": [('plan_id', '=', self.id)],
        }

    def action_open_commission(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.commission.report",
            "name": _("Related commissions"),
            "views": [[self.env.ref('sale_commission.sale_commission_report_view_list').id, "list"]],
            "domain": [('plan_id', '=', self.id)],
        }



class CommissionPlanAchievement(models.Model):
    _inherit = 'sale.commission.plan.achievement'

    rate = fields.Float("Rate", default=1, required=True)

    type = fields.Selection( selection_add=[('collection', 'Collection'), ('journey_plan', 'Journey Plan')],
        ondelete={'collection': 'cascade', 'journey_plan':'cascade'})

