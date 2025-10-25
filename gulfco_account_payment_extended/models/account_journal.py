from odoo import fields, models, api
from collections import defaultdict
import ast

def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals['journal_id']].append(vals)
    return res

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_code = fields.Char(related="default_account_id.code",string="GL Account Code",store=True)
    generate_entry_on_draft_payment = fields.Boolean(
        string="Generate Entry on Draft Payment",
        help="If enabled, a journal entry will be created immediately once a payment is created in draft state. "
             "This is useful for payments where entries needs to be modified before it is posted.",
        default=False,
        copy=False
    )
    
    def _get_journal_dashboard_outstanding_payments_received_issued(self):
        self.env.cr.execute("""
            SELECT payment.journal_id AS journal_id,
                payment.company_id AS company_id,
                payment.currency_id AS currency,
                payment.payment_type AS payment_type,
                SUM(payment.amount) AS amount_total,
                SUM(amount_company_currency_signed) AS amount_total_company
            FROM account_payment payment
            JOIN account_move move ON move.origin_payment_id = payment.id
            WHERE (NOT payment.is_matched OR payment.is_matched IS NULL)
            AND move.state = 'posted'
            AND payment.journal_id = ANY(%s)
            AND payment.company_id = ANY(%s)
        GROUP BY payment.company_id, payment.journal_id, payment.currency_id, payment.payment_type
        """, [self.ids, self.env.companies.ids])

        query_result = group_by_journal(self.env.cr.dictfetchall())

        result_received = {}
        result_issued = {}

        for journal in self:
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)

            # Initialize empty for each journal
            result_received[journal.id] = self._count_results_and_sum_amounts(
                [r for r in query_result[journal.id] if r.get("payment_type") == "inbound"],
                currency
            )

            result_issued[journal.id] = self._count_results_and_sum_amounts(
                [r for r in query_result[journal.id] if r.get("payment_type") == "outbound"],
                currency
            )

        return result_received, result_issued

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        bank_cash_journals = self.filtered(lambda journal: journal.type in ('bank', 'cash', 'credit'))
        if not bank_cash_journals:
            return
        
        outstanding_pay_account_balances_received, outstanding_pay_account_balances_issued = bank_cash_journals._get_journal_dashboard_outstanding_payments_received_issued()

        for journal in bank_cash_journals:
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            accessible = journal.company_id.id in journal.company_id._accessible_branches().ids
            has_outstanding_received, outstanding_pay_account_balance_received = outstanding_pay_account_balances_received[journal.id]
            has_outstanding_issued, outstanding_pay_account_balance_issued = outstanding_pay_account_balances_issued[journal.id]

            domain = [
                ("display_type", "not in", ("line_section", "line_note")),
                ("company_id", "in", self.env.company.ids),
                ("date", "<=", fields.Date.today()),
                ("parent_state", "=", "posted"),
            ]
            balance_gl = journal._get_journal_bank_account_balance(domain=domain)[0]

            dashboard_data[journal.id].update({
                'has_balance_gl': balance_gl != 0,
                'balance_gl': currency.format(balance_gl),
                'nb_lines_outstanding_pay_account_balance_received': has_outstanding_received,
                'nb_lines_outstanding_pay_account_balance_issued': has_outstanding_issued,
                'outstanding_pay_account_balance_received': currency.format(abs(outstanding_pay_account_balance_received)),
                'outstanding_pay_account_balance_issued': currency.format(abs(outstanding_pay_account_balance_issued)),
            })
    
    def action_open_balance_gl(self):
        ''' Show the balance inside the General Ledger report.
        :return: An action opening the General Ledger.
        '''
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_general_ledger")

        action['context'] = dict(ast.literal_eval(action['context']))

        return action
