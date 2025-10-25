# models/custodian_payment_report.py
from odoo import models, fields, tools ,api,_
from odoo.tools import date_utils, SQL,Query
from datetime import date
from odoo.osv import expression


class CustodianPaymentReport(models.Model):
    _name = "custodian.payment.report"
    _description = "Custodian Payment Report"
    _auto = False

    custodian_code = fields.Char(string="Custodian Code")
    custodian_id = fields.Many2one('custodian',string='Custodian')
    amount = fields.Monetary("Amount")
    currency_id = fields.Many2one("res.currency", string="Currency")
    company_id = fields.Many2one("res.company", string="Company")
    payment_method_line_id = fields.Many2one("account.payment.method.line", string="Payment Method")
    aed_amount = fields.Monetary("Amount")
    gl_account = fields.Char(string="GL Account")
    employee_code = fields.Char(string="Employee Code")
    employee = fields.Many2one("res.partner", string="Employee")
    custodian_branch_id = fields.Many2one('custodian.branch',string="Branch")
    custodian_user_job_id = fields.Many2one('custodian.user.jobs',string="User Job")
    transfer_date = fields.Date(string="Transfer date")
    payment_ids_char = fields.Char()
    payment_ids = fields.Many2many('account.payment', string="Payments", compute='_compute_payment_ids')

    @api.depends('payment_ids_char')
    def _compute_payment_ids(self):
        for rec in self:
            if rec.payment_ids_char:
                rec.payment_ids = [(6, 0, rec.payment_ids_char)]
            else:
                rec.payment_ids = [(6, 0, [])]

    def action_show_payment_info(self):
        return {
            'name': _('Show Payment Info'),
            'res_model': 'pdc.cdc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_payment_ids': self.payment_ids.ids}
        }

    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     if 'show_custodian_report' in self.env.context and self.env.context.get('show_custodian_report') and self.env.user.has_group('gulfco_account_payment_extended.own_and_restriction_custodian_report'):
    #         custodian_ids = []
    #         custodian_records = self.env['custodian'].sudo().search([('responsible_custodian','=',self.env.user.partner_id.id)])
    #         if custodian_records:
    #             custodian_ids += custodian_records.ids
    #         restriction_custodian_records = custodian_records.mapped('restriction_custodian_ids')
    #         if restriction_custodian_records:
    #             custodian_ids += restriction_custodian_records.ids
    #         domain = expression.AND([domain, ['|',('custodian_id', 'in', custodian_ids)]])
    #     return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None) -> Query:
        if 'show_custodian_report' in self.env.context and self.env.context.get('show_custodian_report') and self.env.user.has_group('gulfco_account_payment_extended.own_and_restriction_custodian_report'):
            custodian_ids = []
            custodian_records = self.env['custodian'].sudo().search([('responsible_custodian','=',self.env.user.partner_id.id)])
            if custodian_records:
                payment_transfers = self.env['payments.transfer'].sudo().search([('to_custodian_id','in',custodian_records.ids)])
                if payment_transfers:
                    sendor_custodians = payment_transfers.mapped('from_custodian_id')
                    if sendor_custodians:
                        custodian_ids += sendor_custodians.ids
                custodian_ids += custodian_records.ids
            restriction_custodian_records = custodian_records.mapped('restriction_custodian_ids')
            if restriction_custodian_records:
                custodian_ids += restriction_custodian_records.ids
            domain = expression.AND([domain, [('custodian_id', 'in', custodian_ids)]])
        return super()._search(domain,offset,limit,order)

    # @property
    # def _table_query(self):
    #     return """
    #         SELECT
    #             row_number() OVER () AS id,
    #             p.id as payment_id,
    #             p.date as payment_date,
    #             p.amount as amount,
    #             p.currency_id as currency_id,
    #             p.custodian_id as custodian_id,
    #             p.payment_method_line_id as payment_method_line_id
    #         FROM account_payment p
    #         WHERE p.state in ('draft','in_process') AND p.custodian_id IS NOT NULL
    #     """
    #
    # @property
    # def _table_query(self):
    #     return """
    #         SELECT
    #             row_number() OVER () AS id,
    #             p.payment_method_line_id,
    #             p.currency_id,
    #             SUM(p.amount) AS amount
    #         FROM account_payment p
    #         WHERE p.state IN ('draft', 'in_process') AND p.custodian_id IS NOT NULL
    #         GROUP BY p.payment_method_line_id, p.currency_id
    #     """

    @property
    def _table_query(self):
        return SQL( """
                        SELECT
                    row_number() OVER () AS id,
                    p.payment_method_line_id as payment_method_line_id,
                    p.custodian_id as custodian_id,
                    custo.custodian_code as custodian_code,
                    custo.employee_code as employee_code,
                    custo.responsible_custodian as employee,
                    custo.custodian_branch_id as custodian_branch_id,
                    custo.custodian_user_job_id as custodian_user_job_id,
                    MAX(p.date) AS transfer_date,
                    string_agg(DISTINCT aj.account_code, ', ') AS gl_account,
                    %(main_company_id)s as company_id,
                    p.currency_id AS currency_id,
                    SUM(CASE WHEN p.payment_type = 'outbound' THEN -p.amount ELSE p.amount END) AS amount,
                    CASE
                        WHEN cr.rate != 0 THEN ROUND(SUM(CASE WHEN p.payment_type = 'outbound' THEN -p.amount ELSE p.amount END) / cr.rate, 2) ELSE 0.0
                    END AS aed_amount,
                    array_agg(p.id) AS payment_ids_char
                FROM account_payment p
                LEFT JOIN custodian custo ON custo.id = p.custodian_id
                LEFT JOIN account_journal aj ON aj.id = p.journal_id
                LEFT JOIN custodian_branch cb ON cb.id = custo.custodian_branch_id
                LEFT JOIN custodian_user_jobs cuj ON cuj.id = custo.custodian_user_job_id
                JOIN res_currency c ON c.id = p.currency_id
                LEFT JOIN LATERAL (
                    SELECT r.rate
                    FROM res_currency_rate r
                    WHERE r.currency_id = p.currency_id
                      AND r.name <=  %(date_to)s
                      AND r.company_id = %(main_company_id)s
                    ORDER BY r.name DESC
                    LIMIT 1
                ) cr ON true
                WHERE  p.payment_method_line_id IS NOT NULL AND p.custodian_id IS NOT NULL
                       AND (
                        (p.payment_mode = 'bank' AND p.state = 'in_process')                
                        OR (p.payment_mode = 'pdc' AND p.pdc_state IN ('registered', 'bounced'))
                        OR (p.payment_mode = 'cdc' AND p.cdc_state IN ('registered', 'bounced'))
                        OR (p.payment_mode = 'cash' AND p.state IN ('paid', 'in_process'))
                    )
                GROUP BY p.custodian_id,p.payment_method_line_id, p.currency_id,cr.rate,custodian_code,employee_code,custo.responsible_custodian,custodian_branch_id,custodian_user_job_id""",main_company_id=self.env.company.id,
            date_to=date.today())
