from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MSLCommissionReport(models.Model):
    _name = "msl.commission.report"
    _description = "MSL Commission Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id'

    target_id = fields.Many2one('sale.commission.plan.target', "Period", readonly=True)
    target_amount = fields.Monetary("Target Amount", readonly=True, currency_field='currency_id')
    target_percentage = fields.Monetary("Target (%)", readonly=True, currency_field='currency_id')
    plan_id = fields.Many2one('sale.commission.plan', "Commission Plan", readonly=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', "Sales Person", readonly=True)
    partner_id = fields.Many2one('res.partner', "Sales Person", readonly=True)
    team_id = fields.Many2one('crm.team', "Sales Team", readonly=True)
    achieved = fields.Monetary("Achieved", currency_field='currency_id')
    achieved_rate = fields.Float("Achieved Rate", readonly=True, aggregator='avg', compute="_compute_achieved_rate", store=True)
    commission = fields.Monetary("Commission", readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', "Currency", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    forecast_id = fields.Many2one('sale.commission.plan.target.forecast', 'fc')
    payment_date = fields.Date("Payment Date", readonly=True)
    forecast = fields.Monetary("Forecast", readonly=True, currency_field='currency_id')
    date_to = fields.Date(related='target_id.date_to')


    @api.depends('achieved')
    def _compute_achieved_rate(self):
        for rec in self:
            rec.achieved_rate = 0
            if rec.target_percentage and rec.achieved:
                ach = rec.achieved/rec.target_percentage
                rec.achieved_rate = round(ach, 2) or 0.0
                rec.commission = int((rec.plan_id.commission_amount * rec.achieved_rate))
