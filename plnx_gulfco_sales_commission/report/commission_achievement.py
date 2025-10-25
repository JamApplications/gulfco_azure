from odoo import models, fields,api


class SaleAchievementReportInherit(models.Model):
    _inherit = "sale.commission.achievement.report"

    partner_id = fields.Many2one('res.partner', "Salesperson", required=True,
                                 domain="[('contact_type', '=', 'worker')]")
    achieved_plan = fields.Integer("Achieved Plan", default=0, readonly=True,)

    # kpi_type = fields.Selection(related='plan_id.kpi_type', store=True)

    @property
    def _table_query(self):
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
    WITH {self._commission_lines_query(partners=partners, users=users, teams=teams)}
    SELECT
        ROW_NUMBER() OVER (ORDER BY era.date_from DESC, era.id) AS id,
        era.id AS target_id,
        cl.user_id AS user_id,
        cl.partner_id AS partner_id,
        cl.team_id AS team_id,
        cl.achieved AS achieved,
        cl.achieved_plan AS achieved_plan,
        cl.currency_id AS currency_id,
        cl.company_id AS company_id,
        cl.plan_id,
        cl.related_res_model,
        cl.related_res_id,
        cl.date AS date
    FROM commission_lines cl
    JOIN sale_commission_plan_target era
        ON cl.plan_id = era.plan_id
        AND cl.date >= era.date_from
        AND cl.date <= era.date_to
    """

    def _achievement_lines(self, partners=None, users=None, teams=None):
        return f"""
    achievement_commission_lines AS (
        SELECT
            sca.user_id,
            sca.partner_id,
            sca.team_id,
            scp.id AS plan_id,
            sca.currency_rate * sca.amount * scpa.rate AS achieved,
            sca.amount * scpa.rate AS achieved_plan,
            scp.currency_id,
            sca.date,
            scp.company_id,
            sca.id AS related_res_id,
            'sale.commission.achievement' AS related_res_model
        FROM sale_commission_achievement sca
        JOIN sale_commission_plan scp ON scp.company_id = sca.company_id
        JOIN sale_commission_plan_achievement scpa ON scpa.plan_id = scp.id
        JOIN sale_commission_plan_user scpu ON scpu.plan_id = scp.id
        WHERE scp.active
          AND scp.state = 'approved'
          AND sca.type = scpa.type
          AND CASE
                WHEN scp.user_type = 'person' THEN sca.partner_id = scpu.partner_id
                ELSE sca.team_id = scp.team_id
          END
        {'AND sca.partner_id in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
        {'AND sca.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
        {'AND sca.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
    )""", 'achievement_commission_lines'

    @api.model
    def _select_invoices(self):
        return f"""
             MAX(rules.user_id),
             MAX(rules.partner_id),
             MAX(am.team_id),
             rules.plan_id,
             SUM({self._get_invoice_rates_product()}) AS achieved,
             SUM({self._get_invoice_rates_product()}) AS achieved_plan,
             MAX(rules.currency_id),
             MAX(am.date) AS date,
             MAX(rules.company_id),
             am.id AS related_res_id
           """

    def _invoices_lines(self, partners=None, users=None, teams=None):
        return f"""
    invoices_rules AS (
        SELECT
            COALESCE(scpu.date_from, scp.date_from) AS date_from,
            COALESCE(scpu.date_to, scp.date_to) AS date_to,
            scpu.user_id AS user_id,
            scpu.partner_id AS partner_id,
            scp.team_id AS team_id,
            scp.id AS plan_id,
            scpa.product_id,
            scpa.product_categ_id,
            scp.company_id,
            scp.currency_id,
            scp.user_type = 'team' AS team_rule,
            {self._rate_to_case(self._get_invoices_rates())}
            {self._select_rules()}
        FROM sale_commission_plan_achievement scpa
        JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
        JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
        WHERE scp.active
          AND scp.state = 'approved'
          AND scpa.type IN ({','.join("'%s'" % r for r in self._get_invoices_rates())})
        {'AND scpu.partner_id in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
        {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    ), invoice_commission_lines_team AS (
        SELECT
            {self._select_invoices()}
        FROM invoices_rules rules
             {self._join_invoices()}
        WHERE {self._where_invoices()}
          AND rules.team_rule
          AND am.team_id = rules.team_id
          AND am.partner_id = rules.partner_id
        {'AND am.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
          AND am.date BETWEEN rules.date_from AND rules.date_to
          AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
          AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
        GROUP BY
            am.id,
            rules.plan_id
    ), invoice_commission_lines_user AS (
        SELECT
              {self._select_invoices()}
        FROM invoices_rules rules
             {self._join_invoices()}
        WHERE {self._where_invoices()}
          AND NOT rules.team_rule
          AND am.assign_to = rules.partner_id
        {'AND am.invoice_user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
          AND am.date BETWEEN rules.date_from AND rules.date_to
          AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
          AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
        GROUP BY
            am.id,
            rules.plan_id
    ), invoice_commission_lines AS (
        (SELECT *, 'account.move' AS related_res_model FROM invoice_commission_lines_team)
        UNION ALL
        (SELECT *, 'account.move' AS related_res_model FROM invoice_commission_lines_user)
    )""", 'invoice_commission_lines'

    @api.model
    def _where_invoices(self):
        return f"""
             aml.display_type = 'product'
             AND am.move_type in ('out_invoice', 'out_refund')
             AND am.state not in ('cancel', 'draft')
             {self._get_company_condition('am')}
           """

    @api.model
    def _get_company_condition(self, company_table):
        company_count = len(self.env.companies.ids)
        if company_count == 1:
            return f"AND \"{company_table}\".company_id = {self.env.companies.id}"
        else:
            return f"AND \"{company_table}\".company_id IN {tuple(self.env.companies.ids)}"

    def _sale_lines(self, partners=None, users=None, teams=None):
        return f"""
    sale_rules AS (
        SELECT
            COALESCE(scpu.date_from, scp.date_from) AS date_from,
            COALESCE(scpu.date_to, scp.date_to) AS date_to,
            scpu.user_id AS user_id,
            scpu.partner_id AS partner_id,
            scp.team_id AS team_id,
            scp.id AS plan_id,
            scpa.product_id,
            scpa.product_categ_id,
            scp.company_id,
            scp.currency_id,
            scp.user_type = 'team' AS team_rule,
            {self._rate_to_case(self._get_sale_rates())}
            {self._select_rules()}
        FROM sale_commission_plan_achievement scpa
        JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
        JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
        WHERE scp.active
          AND scp.state = 'approved'
          {self._get_company_condition('scp')}
          AND scpa.type IN ({','.join("'%s'" % r for r in self._get_sale_rates())})
        {'AND scpu.partner_id in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
        {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    ), sale_commission_lines_team AS (
        SELECT
            MAX(rules.user_id),
            MAX(rules.partner_id),
            MAX(rules.team_id),
            rules.plan_id,
            SUM({self._get_sale_rates_product()}) AS achieved,
            SUM({self._get_sale_rates_product()}) AS achieved_plan,
            MAX(rules.currency_id),
            MAX(so.date_order) AS date,
            MAX(rules.company_id),
            {self._select_sales()}
        FROM sale_rules rules
        {self._join_sales()}
        JOIN product_product pp
          ON sol.product_id = pp.id
        JOIN product_template pt
          ON pp.product_tmpl_id = pt.id
        WHERE rules.team_rule
          AND so.team_id = rules.team_id
        {'AND so.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
        {self._where_sales()}
        GROUP BY
            so.id,
            rules.plan_id
    ), sale_commission_lines_user AS (
        SELECT
            MAX(rules.user_id),
            MAX(rules.partner_id),
            MAX(so.team_id),
            rules.plan_id,
            SUM({self._get_sale_rates_product()}) AS achieved,
            SUM({self._get_sale_rates_product()}) AS achieved_plan,
            MAX(rules.currency_id),
            MAX(so.date_order) AS date,
            MAX(rules.company_id),
            {self._select_sales()}
        FROM sale_rules rules
        {self._join_sales()}
        JOIN product_product pp
          ON sol.product_id = pp.id
        JOIN product_template pt
          ON pp.product_tmpl_id = pt.id
        WHERE NOT rules.team_rule
          AND so.partner_id = rules.partner_id
        {'AND so.partner_id in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
        {'AND so.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
          {self._where_sales()}
        GROUP BY
            so.id,
            rules.plan_id
    ), sale_commission_lines AS (
        (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_team)
        UNION ALL
        (SELECT *, 'sale.order' AS related_res_model FROM sale_commission_lines_user)
    )""", 'sale_commission_lines'



    def _commission_lines_cte(self, partners=None, users=None, teams=None):
        return [self._achievement_lines(partners, users, teams), self._sale_lines(partners, users, teams),
                self._invoices_lines(partners, users, teams), self._payment_lines(partners, users, teams), 
                self._journey_plan_lines(partners, users, teams)]

    def _commission_lines_query(self, partners=None, users=None, teams=None):
        ctes = self._commission_lines_cte(partners, users, teams)
        queries = [x[0] for x in ctes]
        table_names = [x[1] for x in ctes]
        return f"""
      {','.join(queries)},
      commission_lines AS (
          {' UNION ALL '.join(f'(SELECT * FROM {name})' for name in table_names)}
      )
      """



    # Payment Collection achievement type
    def _payment_lines(self, partners=None, users=None, teams=None):
        return f"""
    payments_rules AS (
        SELECT
            COALESCE(scpu.date_from, scp.date_from) AS date_from,
            COALESCE(scpu.date_to, scp.date_to) AS date_to,
            scpu.user_id AS user_id,
            scpu.partner_id AS partner_id,
            scp.team_id AS team_id,
            scp.id AS plan_id,
            scpa.product_id,
            scpa.product_categ_id,
            scp.company_id,
            scp.currency_id,
            scp.user_type = 'team' AS team_rule,
            {self._rate_to_case(self._get_payment_rates())}
            {self._select_rules()}
        FROM sale_commission_plan_achievement scpa
        JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
        JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
        WHERE scp.active
          AND scp.state = 'approved'
          AND scpa.type IN ({','.join("'%s'" % r for r in self._get_payment_rates())})
        {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    ), payment_commission_lines_team AS (
        SELECT
            {self._select_payments()}
        FROM payments_rules rules
             {self._join_payments()}
        WHERE {self._where_payments()}
          AND rules.team_rule
          AND ap.team_id = rules.team_id
        {'AND ap.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
          AND ap.date BETWEEN rules.date_from AND rules.date_to
        GROUP BY
            ap.id,
            rules.plan_id
    ), payment_commission_lines_user AS (
        SELECT
              {self._select_payments()}
        FROM payments_rules rules
             {self._join_payments()}
        WHERE {self._where_payments()}
          AND NOT rules.team_rule
          AND ap.responsible_id = rules.partner_id
        {'AND ap.responsible_id in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
          AND ap.date BETWEEN rules.date_from AND rules.date_to
        GROUP BY
            ap.id,
            rules.plan_id
    ), payment_commission_lines AS (
        (SELECT *, 'account.payment' AS related_res_model FROM payment_commission_lines_team)
        UNION ALL
        (SELECT *, 'account.payment' AS related_res_model FROM payment_commission_lines_user)
    )""", 'payment_commission_lines'


    @api.model
    def _get_payment_rates(self):
        return ['collection']

    @api.model
    def _select_payments(self):
        return f"""
          MAX(rules.user_id),
          MAX(rules.partner_id),
          MAX(ap.team_id),
          rules.plan_id,
          SUM({self._get_payment_rates_product()}) AS achieved,
          SUM({self._get_payment_rates_product()}) AS achieved_plan,
          MAX(rules.currency_id),
          MAX(ap.date) AS date,
          MAX(rules.company_id),
          ap.id AS related_res_id
        """

    @api.model
    def _join_payments(self):
        return """
          JOIN account_payment ap
            ON ap.company_id = rules.company_id
        """

    @api.model
    def _get_payment_rates_product(self):
        return """
            rules.collection_rate * ap.amount 
        """

    @api.model
    def _where_payments(self):
        query = f"""
          ap.payment_type in ('inbound', 'out_refund')
          AND ap.state in ('in_process','paid')
          AND
          (ap.pdc_state in ('collected') OR ap.cdc_state in ('collected'))
         
        """
        return query




    # Journey Plan achievement type
    def _journey_plan_lines(self, partners=None, users=None, teams=None):
        return f"""
       journey_plan_rules AS (
           SELECT
               COALESCE(scpu.date_from, scp.date_from) AS date_from,
               COALESCE(scpu.date_to, scp.date_to) AS date_to,
               scpu.user_id AS user_id,
               scpu.partner_id AS partner_id,
               scp.team_id AS team_id,
               scp.id AS plan_id,
               scpa.product_id,
               scpa.product_categ_id,
               scp.company_id,
               scp.currency_id,
               scp.user_type = 'team' AS team_rule,
               {self._rate_to_case(self._get_journey_plan_rates())}
               {self._select_rules()}
           FROM sale_commission_plan_achievement scpa
           JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
           JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
           WHERE scp.active
             AND scp.state = 'approved'
             AND scpa.type IN ({','.join("'%s'" % r for r in self._get_journey_plan_rates())})
           {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
           {'AND scpu.partner_id in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
       ), journey_plan_lines_team AS (
           SELECT
               {self._select_journey_plan()}
           FROM journey_plan_rules rules
                {self._join_journey_plan()}
           WHERE {self._where_journey_plan()}
             AND rules.team_rule
             AND jp.team_id = rules.team_id
           {'AND jp.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
             AND jp.scheduled_date_start BETWEEN rules.date_from AND rules.date_to
           GROUP BY
               jp.id,
               rules.plan_id
       ), journey_plan_lines_user AS (
           SELECT
                 {self._select_journey_plan()}
           FROM journey_plan_rules rules
                {self._join_journey_plan()}
           WHERE {self._where_journey_plan()}
             AND NOT rules.team_rule
             AND jp.person_id_partner = rules.partner_id
           {'AND jp.person_id_partner in (%s)' % ','.join(str(i) for i in partners) if partners else ''}
             AND jp.scheduled_date_start BETWEEN rules.date_from AND rules.date_to
           GROUP BY
               jp.id,
               rules.plan_id
       ), journey_plan_lines AS (
           (SELECT *, 'fsm.order' AS related_res_model FROM journey_plan_lines_team)
           UNION ALL
           (SELECT *, 'fsm.order' AS related_res_model FROM journey_plan_lines_user)
       )""", 'journey_plan_lines'

    @api.model
    def _get_journey_plan_rates(self):
        return ['journey_plan']

    @api.model
    def _select_journey_plan(self):
        return f"""
             MAX(rules.user_id),
             MAX(rules.partner_id),
             MAX(jp.team_id),
             rules.plan_id,
             SUM({self._get_journey_plan_rates_product()}) AS achieved,
             SUM({self._get_journey_plan_rates_product()}) AS achieved_plan,
             MAX(rules.currency_id),
             MAX(jp.scheduled_date_start) AS date,
             MAX(rules.company_id),
             jp.id AS related_res_id
           """

    @api.model
    def _join_journey_plan(self):
        return """
             JOIN fsm_order jp
               ON jp.company_id = rules.company_id
           """

    @api.model
    def _get_journey_plan_rates_product(self):
        return """
               rules.journey_plan_rate * 1
           """

    @api.model
    def _where_journey_plan(self):
        stage = self.env['fsm.stage']

        # Fetch the actual stage IDs dynamically
        completed_stage = stage.search([('name', '=', 'Completed'), ('is_closed', '=', True)], limit=1).id
        cancelled_stage = stage.search([('name', '=', 'Cancelled')], limit=1).id

        return f"""
            jp.stage_id = {completed_stage}
            AND jp.stage_id != {cancelled_stage}
        """


