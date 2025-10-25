# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, _


class SaleCommissionReport(models.Model):
    _inherit = "sale.commission.report"

    kpi_type = fields.Selection(related='plan_id.kpi_type', store=True)

    partner_id = fields.Many2one('res.partner', "Salesperson", required=True,
                                 domain="[('contact_type', '=', 'worker')]")

    target_plan = fields.Integer("Target Plan", default=0, required=True)
    achieved_plan = fields.Integer("Achieved Plan", default=0, readonly=True, )

    def action_achievement_detail(self):
        self.ensure_one()
        print("inside oveeride achivement action:", self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.commission.achievement.report",
            "name": _('Commission Detail: %(name)s', name=self.target_id.name),
            "views": [[self.env.ref('sale_commission.sale_achievement_report_view_list').id, "list"]],
            "context": {'commission_partner_ids': self.partner_id.ids, 'commission_team_ids': self.team_id.ids},
            "domain": [('plan_id', '=', self.plan_id.id)],  # FP TODO: add date filter based on context
        }

    def write(self, values):
        # /!\ Do not call super as the table doesn't exist
        if 'forecast' in values:
            amount = values['forecast']
            for line in self:
                if line.forecast_id:
                    line.sudo().forecast_id.amount = amount
                else:
                    line.forecast_id = self.env['sale.commission.plan.target.forecast'].sudo().create({
                        'target_id': line.target_id.id,
                        'amount': amount,
                        'plan_id': line.plan_id.id,
                        'user_id': line.user_id.id,
                        'partner_id': line.partner_id.id,
                    })
            # Update the field's cache otherwise the field reset to the original value on the field
            self.env.cache._set_field_cache(self, self._fields.get('forecast')).update(dict.fromkeys(self.ids, amount))
        return True



    def _query(self):
        users = self.env.context.get('commission_user_ids', [])
        partners = self.env.context.get('commission_partner_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
            partners = self.env['res.partner'].browse(partners).exists()
            partners = partners.ids
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()

        return f"""
        WITH {self.env['sale.commission.achievement.report']._commission_lines_query(partners=partners, users=users, teams=teams)},
        achievement AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY MAX(era.date_to) DESC, u.user_id) AS id,
                era.id AS target_id,
                era.plan_id AS plan_id,
                u.user_id AS user_id,
                u.partner_id AS partner_id,
                MIN(cl.team_id) AS team_id,
                cl.company_id AS company_id,
                SUM(achieved) AS achieved,
                SUM(achieved_plan) AS achieved_plan,
                CASE
                    WHEN MAX(era.amount) > 0 THEN GREATEST(SUM(achieved), 0) / MAX(era.amount)
                    ELSE 0
                END AS achieved_rate,
                cl.currency_id AS currency_id,
                MAX(era.amount) AS amount,
                MAX(era.target_plan) AS target_plan,
                MAX(era.date_to) AS payment_date,
                MAX(scpf.id) AS forecast_id,
                MAX(scpf.amount) AS forecast
            FROM sale_commission_plan_target era
            LEFT JOIN sale_commission_plan_user u
                ON u.plan_id = era.plan_id
                AND COALESCE(u.date_from, era.date_from) < era.date_to
                AND COALESCE(u.date_to, era.date_to) > era.date_from
            LEFT JOIN commission_lines cl
                ON cl.plan_id = era.plan_id
                AND cl.date >= era.date_from
                AND cl.date <= era.date_to
                AND cl.partner_id = u.partner_id
            LEFT JOIN sale_commission_plan_target_forecast scpf
                ON (scpf.target_id = era.id AND u.user_id = scpf.user_id)
            GROUP BY
                era.id,
                era.plan_id,
                u.user_id,
                u.partner_id,
                cl.company_id,
                cl.currency_id
        ),
        target_com AS (
            SELECT
                amount,
                target_rate_from,
                target_rate_to,
                plan_id
            FROM sale_commission_plan_target_commission scpta
            JOIN sale_commission_plan scp ON scp.id = scpta.plan_id
            WHERE scp.type = 'target'
        ),
        achievement_target AS (
            SELECT
                MIN(a.id) AS id,
                MIN(a.target_id) AS target_id,
                a.plan_id,
                a.user_id,
                a.partner_id,
                a.team_id,
                a.company_id,
                a.currency_id,
                MIN(a.forecast_id) AS forecast_id,
                {self._get_date_range()} AS payment_date,
                SUM(a.achieved) AS achieved,
                SUM(a.achieved_plan) AS achieved_plan,
                CASE 
                    WHEN SUM(a.amount) > 0 THEN SUM(a.achieved) / SUM(a.amount)
                    WHEN SUM(a.target_plan) > 0 THEN SUM(a.achieved_plan) / SUM(a.target_plan)
                    ELSE NULL
                 END AS achieved_rate,
                SUM(a.amount) AS target_amount,
                SUM(a.target_plan) AS target_plan,
                SUM(a.forecast) AS forecast,
                COUNT(1) AS ct
            FROM achievement a
            GROUP BY
                a.plan_id, a.user_id,a.partner_id, a.team_id, a.company_id, a.currency_id, {self._get_date_range()}
        )
        SELECT
            a.*,
            scp.kpi_type,
             ROUND(
        CASE
            WHEN scp.kpi_type = 'sale_target' THEN tc.amount * a.ct
            WHEN scp.kpi_type = 'collection' AND a.achieved_rate > 1 THEN scp.commission_amount
            WHEN scp.kpi_type = 'collection' THEN scp.commission_amount * a.achieved_rate * a.ct
            WHEN scp.kpi_type = 'journal_plan' THEN scp.commission_amount * a.achieved_rate * a.ct
            ELSE 0
        END
    )::INTEGER AS commission
           
        FROM achievement_target a
        LEFT JOIN sale_commission_plan scp ON scp.id = a.plan_id
        LEFT JOIN target_com tc ON (
            tc.plan_id = a.plan_id AND
            a.achieved_rate >= tc.target_rate_from AND
            a.achieved_rate < tc.target_rate_to
        )
        WHERE (
            scp.kpi_type IS NULL OR
            scp.kpi_type != 'msl_availability'
        )
        """
