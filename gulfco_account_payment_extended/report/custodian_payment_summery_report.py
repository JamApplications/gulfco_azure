from odoo import models, fields, tools ,api,_
from odoo.tools import date_utils, SQL,Query
from datetime import date
from odoo.osv import expression


class CustodianPaymentSummeryReport(models.Model):
    _name = "custodian.payment.summery.report"
    _description = "Custodian Payment Summery Report"
    _auto = False

    custodian_code = fields.Char(string="Custodian Code")
    custodian_id = fields.Many2one('custodian',string='Custodian')
    employee = fields.Many2one("res.partner", string="Employee")
    amount = fields.Monetary("Amount")
    currency_id = fields.Many2one("res.currency", string="Currency")
    company_id = fields.Many2one("res.company", string="Company")
    payment_method_line_id = fields.Many2one("account.payment.method.line", string="Payment Method")
    aed_amount = fields.Monetary("Amount")
    gl_account = fields.Char(string="GL Account")
    employee_code = fields.Char(string="Employee Code")
    custodian_branch_id = fields.Many2one('custodian.branch',string="Branch")
    custodian_user_job_id = fields.Many2one('custodian.user.jobs',string="User Job")
    transfer_date = fields.Date(string="Transfer date")
    payment_ids_char = fields.Char()
    payment_ids = fields.Many2many('account.payment', string="Payments", compute='_compute_payment_ids')
    media_type = fields.Char(string="Media Type")

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

    @property
    def _table_query(self):
        return SQL("""
            SELECT
                row_number() OVER () AS id,
                CASE WHEN p.payment_mode = 'cash' THEN Null
                ELSE p.payment_method_line_id END AS payment_method_line_id,
                CASE WHEN p.payment_mode = 'cash' THEN 'Cash'
                ELSE apml.name END AS media_type, 
                p.custodian_id AS custodian_id,
                custo.custodian_code AS custodian_code,
                custo.employee_code AS employee_code,
                custo.responsible_custodian AS employee,
                custo.custodian_branch_id AS custodian_branch_id,
                custo.custodian_user_job_id AS custodian_user_job_id,
                MAX(p.date) AS transfer_date,
                string_agg(DISTINCT aj.account_code, ', ') AS gl_account,
                %(main_company_id)s AS company_id,
                p.currency_id AS currency_id,
                SUM(
                    CASE 
                        WHEN p.payment_type = 'outbound' THEN -p.amount 
                        ELSE p.amount 
                    END
                ) AS amount,
                CASE
                    WHEN cr.rate != 0 
                    THEN ROUND(
                        SUM(
                            CASE 
                                WHEN p.payment_type = 'outbound' THEN -p.amount 
                                ELSE p.amount 
                            END
                        ) / cr.rate, 2
                    )
                    ELSE 0.0
                END AS aed_amount,
                array_agg(p.id) AS payment_ids_char
            FROM account_payment p
            LEFT JOIN custodian custo ON custo.id = p.custodian_id
            LEFT JOIN account_journal aj ON aj.id = p.journal_id
            LEFT JOIN custodian_branch cb ON cb.id = custo.custodian_branch_id
            LEFT JOIN custodian_user_jobs cuj ON cuj.id = custo.custodian_user_job_id
            LEFT JOIN account_payment_method_line apml ON apml.id = p.payment_method_line_id
            JOIN res_currency c ON c.id = p.currency_id
            LEFT JOIN LATERAL (
                SELECT r.rate
                FROM res_currency_rate r
                WHERE r.currency_id = p.currency_id
                  AND r.name <= %(date_to)s
                  AND r.company_id = %(main_company_id)s
                ORDER BY r.name DESC
                LIMIT 1
            ) cr ON true
            WHERE p.payment_method_line_id IS NOT NULL 
              AND p.custodian_id IS NOT NULL
              AND (
                (p.payment_mode = 'bank' AND p.state = 'in_process')                
                OR (p.payment_mode = 'pdc' AND p.pdc_state IN ('registered', 'bounced'))
                OR (p.payment_mode = 'cdc' AND p.cdc_state IN ('registered', 'bounced'))
                OR (p.payment_mode = 'cash' AND p.state IN ('paid', 'in_process'))
              )
            GROUP BY 
                p.custodian_id,
                p.currency_id,
                cr.rate,
                apml.name,
                p.payment_mode,
                custo.custodian_code,
                custo.employee_code,
                custo.responsible_custodian,
                custo.custodian_branch_id,
                custo.custodian_user_job_id,
                CASE 
                    WHEN p.payment_mode = 'cash' THEN NULL 
                    ELSE p.payment_method_line_id 
                END
        """,
                   main_company_id=self.env.company.id,
                   date_to=date.today())
