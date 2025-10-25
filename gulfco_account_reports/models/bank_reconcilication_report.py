from datetime import date
import logging
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class BankReconciliationReportCustomHandler(models.AbstractModel):
    _inherit = 'account.bank.reconciliation.report.handler'

    def _get_last_bank_statement(self, journal, options):
        """
            Retrieve the last bank statement created using this journal.
            :param journal: The journal used.
            :param domain:  An additional domain to be applied on the account.bank.statement model.
            :return:        An account.bank.statement record or an empty recordset.
        """
        if self.env.context.get('show_all'):
            report_date = fields.Date.from_string(options['date']['date_to'])
            last_statement_domain = [('journal_id', '=', journal.id), ('statement_id', '!=', False),
                                     ('date', '<=', report_date)]
            last_st_line = self.env['account.bank.statement.line'].search(last_statement_domain,
                                                                          order='date desc, id desc')
            return last_st_line.mapped('statement_id')
        else:
            report_date = fields.Date.from_string(options['date']['date_to'])
            last_statement_domain = [('journal_id', '=', journal.id), ('statement_id', '!=', False),
                                     ('date', '<=', report_date)]
            last_st_line = self.env['account.bank.statement.line'].search(last_statement_domain,
                                                                          order='date desc, id desc', limit=1)
            return last_st_line.statement_id

    def _bank_reconciliation_report_custom_engine_common(self, options, internal_type, current_groupby, from_last_statement, unreconciled=True):
        """
            Retrieve entries for bank reconciliation based on specified parameters.
            Parameters:
            - options (dict): A dictionary containing options of the report.
            - internal_type (str): The internal type used for classification (e.g., receipt, payment). For the receipt
                                   we will query the entries with a positive amounts and for the payment
                                   the negative amounts.
                                   If the internal type is another thing that receipt or payment it will get all the
                                   entries position or negative
            - current_groupby (str): The current grouping criteria.
            - last_statement (bool, optional): If True, query entries from the last bank statement.
                                               Otherwise, query entries that are not part of the last bank
                                               statement.
            - unreconciled (bool, optional): If True, query the unreconciled entries only

        """
        journal, journal_currency, _company_currency = self._get_bank_journal_and_currencies(options)
        if not journal:
            return self._build_custom_engine_result()

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def build_result_dict(query_res_lines):
            # The query should find exactly one account move line per bank statement line
            if current_groupby == 'id':
                res = query_res_lines[0]
                foreign_currency = self.env['res.currency'].browse(res['foreign_currency_id'])
                rate = 1  # journal_currency / foreign_currency
                if foreign_currency:
                    rate = (res['amount'] / res['amount_currency']) if res['amount_currency'] else 0

                return self._build_custom_engine_result(
                    date=res['date'] if res['date'] else None,
                    label=res['payment_ref'] or res['ref'] or '/',
                    amount_currency=-res['amount_residual'] if res['foreign_currency_id'] else None,
                    amount_currency_currency_id=foreign_currency.id if res['foreign_currency_id'] else None,
                    currency=foreign_currency.display_name if res['foreign_currency_id'] else None,
                    amount=-res['amount_residual'] * rate if res['amount_residual'] else None,
                    amount_currency_id=journal_currency.id,
                )
            else:
                amount = 0
                for res in query_res_lines:
                    rate = 1  # journal_currency / foreign_currency
                    if res['foreign_currency_id']:
                        rate = (res['amount'] / res['amount_currency']) if res['amount_currency'] else 0
                    amount += -res.get('amount_residual', 0) * rate if unreconciled else res.get('amount', 0)

                return self._build_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        query = report._get_report_query(options, 'strict_range', domain=[
            ('journal_id', '=', journal.id),
            ('account_id', '=', journal.default_account_id.id),  # There should be only 1 line per move with that account
        ])

        if from_last_statement:
            if internal_type in ['receipts','payments']:
                last_statement_id = self.with_context(show_all=True)._get_last_bank_statement(journal, options)
            else:
                last_statement_id = self._get_last_bank_statement(journal, options).id
            if last_statement_id and isinstance(last_statement_id,int):
                last_statement_id_condition = SQL("st_line.statement_id = %s", last_statement_id)
            elif last_statement_id and len(last_statement_id) >1:
                last_statement_id_condition = SQL("st_line.statement_id in %s", tuple(last_statement_id.ids))
            else:
                # If there is no last statement, the last statement section must be empty and the other must have all
                # transaction
                return self._compute_result([], current_groupby, build_result_dict)
        else:
            last_statement_id_condition = SQL("st_line.statement_id IS NULL")

        if internal_type == 'receipts':
            st_line_amount_condition = SQL("AND st_line.amount > 0")
        elif internal_type == 'payments':
            st_line_amount_condition = SQL("AND st_line.amount < 0")
        else:
            # For the Transaction without statement, the internal type is 'all'
            st_line_amount_condition = SQL("")

        groupby_field_sql = self.env['account.move.line']._field_to_sql("account_move_line", current_groupby, query) if current_groupby else SQL('NULL')
        # Build query
        query = SQL(
            """
           SELECT %(select_from_groupby)s,
                  st_line.id,
                  move.name,
                  move.ref,
                  move.date,
                  st_line.payment_ref,
                  st_line.amount,
                  st_line.amount_residual,
                  st_line.amount_currency,
                  st_line.foreign_currency_id
             FROM %(table_references)s
             JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
             JOIN account_move move ON move.id = st_line.move_id
            WHERE %(search_condition)s
                  %(is_unreconciled)s
                  %(st_line_amount_condition)s
              AND %(last_statement_id_condition)s
         GROUP BY %(group_by)s,
                  st_line.id,
                  move.id
            """,
            select_from_groupby=SQL("%s AS grouping_key", groupby_field_sql),
            table_references=query.from_clause,
            search_condition=query.where_clause,
            is_receipt=SQL("st_line.amount > 0") if internal_type == "receipts" else SQL("st_line.amount < 0"),
            is_unreconciled=SQL("AND NOT st_line.is_reconciled") if unreconciled else SQL(""),
            st_line_amount_condition=st_line_amount_condition,
            last_statement_id_condition=last_statement_id_condition,
            group_by=groupby_field_sql if current_groupby else SQL('st_line.id'),  # Same key in the groupby because we can't put a null key in a group by
        )

        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        return self._compute_result(query_res_lines, current_groupby, build_result_dict)
