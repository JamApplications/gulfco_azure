# Part of Odoo. See LICENSE file for full copyright and licensing details.
from decorator import append

from odoo import models, fields, api, osv, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.tools import SQL, Query
from odoo.tools.misc import file_path, format_date, formatLang, split_every, xlsxwriter
import io
import re
from odoo.http import request
import xlsxwriter
import base64
import logging
from datetime import date
from datetime import datetime
from itertools import groupby
import markupsafe
from copy import deepcopy
from collections import defaultdict
import io
from datetime import date
from markupsafe import Markup

_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError, ValidationError



class CustomerStatementCustomHandler(models.AbstractModel):
    _inherit = 'account.customer.statement.report.handler'

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        rslt = {partner_id: [] for partner_id in partner_ids}

        partner_ids_wo_none = [x for x in partner_ids if x]
        directly_linked_aml_partner_clauses = []
        indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IS NOT NULL')
        if None in partner_ids:
            directly_linked_aml_partner_clauses.append(SQL('account_move_line.partner_id IS NULL'))
        if partner_ids_wo_none:
            directly_linked_aml_partner_clauses.append(SQL('account_move_line.partner_id IN %s', tuple(partner_ids_wo_none)))
            indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IN %s', tuple(partner_ids_wo_none))
        directly_linked_aml_partner_clause = SQL('(%s)', SQL(' OR ').join(directly_linked_aml_partner_clauses))

        queries = []
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
        report = self.env.ref('account_reports.partner_ledger_report')
        additional_columns = self._get_additional_column_aml_values()
        order_by = self._get_order_by_aml_values()
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(group_options, 'strict_range')
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')

            # For the move lines directly linked to this partner
            # ruff: noqa: FURB113
            queries.append(SQL(
                '''
                SELECT
                    account_move_line.id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    %(additional_columns)s
                    COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                    %(debit_select)s                                                 AS debit,
                    %(credit_select)s                                                AS credit,
                    %(balance_select)s                                               AS amount,
                    %(balance_select)s                                               AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    %(account_code)s                                                 AS account_code,
                    %(account_name)s                                                 AS account_name,
                    journal.code                                                     AS journal_code,
                    %(journal_name)s                                                 AS journal_name,
                    %(column_group_key)s                                             AS column_group_key,
                    'directly_linked_aml'                                            AS key,
                    0                                                                AS partial_id,
                    account_move.purchase_order_ref                                  AS po_number,
                    company.name                                                     AS company_name,
                    company.division_code                                            AS company_code,
                    account_move.amount_residual                                     AS remaining_amount,
                    account_move.amount_residual_signed                              AS remaining_amount_signed,
                    account_move.due_date_upload                                     AS due_date_upload
                FROM %(table_references)s
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN purchase_order_line pol ON pol.id = account_move_line.purchase_line_id
                LEFT JOIN purchase_order po ON po.id = pol.order_id
                %(currency_table_join)s
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                WHERE %(search_condition)s AND %(directly_linked_aml_partner_clause)s
                ORDER BY %(order_by)s
                ''',
                additional_columns=additional_columns,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                account_code=account_code,
                account_name=account_name,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                search_condition=query.where_clause,
                directly_linked_aml_partner_clause=directly_linked_aml_partner_clause,
                order_by=order_by,
            ))

            # For the move lines linked to no partner, but reconciled with this partner. They will appear in grey in the report
            queries.append(SQL(
                '''
                SELECT
                    account_move_line.id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    aml_with_partner.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.matching_number,
                    %(additional_columns)s
                    COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                    %(debit_select)s                                                 AS debit,
                    %(credit_select)s                                                AS credit,
                    %(balance_select)s                                               AS amount,
                    %(balance_select)s                                               AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    %(account_code)s                                                 AS account_code,
                    %(account_name)s                                                 AS account_name,
                    journal.code                                                     AS journal_code,
                    %(journal_name)s                                                 AS journal_name,
                    %(column_group_key)s                                             AS column_group_key,
                    'indirectly_linked_aml'                                          AS key,
                    partial.id                                                       AS partial_id,
                    account_move.purchase_order_ref                                  AS po_number,
                    company.name                                                     AS company_name,
                    company.division_code                                            AS company_code,
                    account_move.amount_residual                                     AS remaining_amount,
                    account_move.amount_residual_signed                              AS remaining_amount_signed,
                    account_move.due_date_upload                                     AS due_date_upload
                FROM %(table_references)s
                    %(currency_table_join)s
                    JOIN account_partial_reconcile partial ON TRUE
                    JOIN account_move ON account_move.id = account_move_line.move_id
                    JOIN account_move_line aml_with_partner ON (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    JOIN account_journal journal ON journal.id = account_move_line.journal_id
                    LEFT JOIN res_company company ON company.id = account_move_line.company_id
                    LEFT JOIN purchase_order_line pol ON pol.id = account_move_line.purchase_line_id
                    LEFT JOIN purchase_order po ON po.id = pol.order_id
                WHERE
                    (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                    AND account_move_line.partner_id IS NULL
                    AND account_move.id = account_move_line.move_id
                    AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND %(indirectly_linked_aml_partner_clause)s
                    AND journal.id = account_move_line.journal_id
                    AND %(account_alias)s.id = account_move_line.account_id
                    AND %(search_condition)s
                    AND partial.max_date BETWEEN %(date_from)s AND %(date_to)s
                ORDER BY %(order_by)s
                ''',
                additional_columns=additional_columns,
                debit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END")),
                credit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END")),
                balance_select=report._currency_table_apply_rate(SQL("-SIGN(aml_with_partner.balance) * partial.amount")),
                account_code=account_code,
                account_name=account_name,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                indirectly_linked_aml_partner_clause=indirectly_linked_aml_partner_clause,
                account_alias=SQL.identifier(account_alias),
                search_condition=query.where_clause,
                date_from=group_options['date']['date_from'],
                date_to=group_options['date']['date_to'],
                order_by=order_by,
            ))

        query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

        if offset:
            query = SQL('%s OFFSET %s ', query, offset)

        if limit:
            query = SQL('%s LIMIT %s ', query, limit)

        self._cr.execute(query)
        for aml_result in self._cr.dictfetchall():
            if aml_result['key'] == 'indirectly_linked_aml':

                # Append the line to the partner found through the reconciliation.
                if aml_result['partner_id'] in rslt:
                    rslt[aml_result['partner_id']].append(aml_result)

                # Balance it with an additional line in the Unknown Partner section but having reversed amounts.
                if None in rslt:
                    rslt[None].append({
                        **aml_result,
                        'debit': aml_result['credit'],
                        'credit': aml_result['debit'],
                        'amount': aml_result['credit'] - aml_result['debit'],
                        'balance': -aml_result['balance'],
                    })
            else:
                rslt[aml_result['partner_id']].append(aml_result)

        return rslt

    def _get_aml_values_customer_statement(self, options, partner_ids, offset=0, limit=None):
        if self.env.context.get('from_supplier_soa'):
            # Initialize result structure: {partner_id: {currency_name: [list_of_data]}}
            rslt = {partner_id: {} for partner_id in partner_ids}

            # Get all currencies in advance to minimize queries
            currency_query = """SELECT id, name FROM res_currency"""
            self._cr.execute(currency_query)
            currency_names = {row[0]: row[1] for row in self._cr.fetchall()}
            company_currency = self.env.company.currency_id.name

            partner_ids_wo_none = [x for x in partner_ids if x]
            directly_linked_aml_partner_clauses = []
            indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IS NOT NULL')
            if None in partner_ids:
                directly_linked_aml_partner_clauses.append(SQL('account_move_line.partner_id IS NULL'))
            if partner_ids_wo_none:
                directly_linked_aml_partner_clauses.append(
                    SQL('account_move_line.partner_id IN %s', tuple(partner_ids_wo_none)))
                indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IN %s',
                                                           tuple(partner_ids_wo_none))
            # if self.env.context.get('from_supplier_soa'):
            #     directly_linked_aml_partner_clauses.append(SQL('account_move.move_type IN %s', tuple('in_invoice')))
            #     indirectly_linked_aml_partner_clause = SQL('account_move.move_type IN %s', tuple('in_invoice'))
            directly_linked_aml_partner_clause = SQL('(%s)', SQL(' OR ').join(directly_linked_aml_partner_clauses))

            queries = []
            journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
            report = self.env.ref('account_reports.partner_ledger_report')
            additional_columns = self._get_additional_column_aml_values()
            order_by = self._get_order_by_aml_values()
            for column_group_key, group_options in report._split_options_per_column_group(options).items():
                query = report._get_report_query(group_options, 'strict_range')
                account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id',
                                                rhs_table='account_account', rhs_column='id', link='account_id')
                account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
                account_name = self.env['account.account']._field_to_sql(account_alias, 'name')

                # For the move lines directly linked to this partner
                queries.append(SQL(
                    '''
                    SELECT
                        account_move_line.id,
                        COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                        account_move_line.name,
                        account_move_line.ref,
                        account_move_line.company_id,
                        account_move_line.account_id,
                        account_move_line.payment_id,
                        account_move_line.partner_id,
                        account_move_line.currency_id,
                        account_move_line.amount_currency,
                        account_move_line.matching_number,
                        %(additional_columns)s
                        COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                        %(debit_select)s                                                 AS debit,
                        %(credit_select)s                                                AS credit,
                        %(balance_select)s                                               AS amount,
                        %(balance_select)s                                               AS balance,
                        account_move.name                                                AS move_name,
                        account_move.id                                                  AS move_id,
                        account_move.move_type                                           AS move_type,
                        %(account_code)s                                                 AS account_code,
                        account_move.amount_residual                                     AS remaining_amount,
                        account_move.amount_residual_signed                              AS remaining_amount_signed,
                        account_move.due_date_upload                                     AS due_date_upload,
                        %(account_name)s                                                 AS account_name,
                        journal.code                                                     AS journal_code,
                        %(journal_name)s                                                 AS journal_name,
                        %(column_group_key)s                                             AS column_group_key,
                        'directly_linked_aml'                                            AS key,
                        0                                                                AS partial_id
                    FROM %(table_references)s
                    JOIN account_move ON account_move.id = account_move_line.move_id
                    %(currency_table_join)s
                    LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                    LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                    LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                    WHERE %(search_condition)s AND %(directly_linked_aml_partner_clause)s
                    ORDER BY %(order_by)s
                    ''',
                    additional_columns=additional_columns,
                    debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                    credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                    balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                    account_code=account_code,
                    account_name=account_name,
                    journal_name=journal_name,
                    column_group_key=column_group_key,
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(group_options),
                    search_condition=query.where_clause,
                    directly_linked_aml_partner_clause=directly_linked_aml_partner_clause,
                    order_by=order_by,
                ))

                # For the move lines linked to no partner, but reconciled with this partner
                queries.append(SQL(
                    '''
                    SELECT
                        account_move_line.id,
                        COALESCE(account_move_line.date_maturity, account_move_line.date) AS date_maturity,
                        account_move_line.name,
                        account_move_line.ref,
                        account_move_line.company_id,
                        account_move_line.account_id,
                        account_move_line.payment_id,
                        aml_with_partner.partner_id,
                        account_move_line.currency_id,
                        account_move_line.amount_currency,
                        account_move_line.matching_number,
                        %(additional_columns)s
                        COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                        %(debit_select)s                                                 AS debit,
                        %(credit_select)s                                                AS credit,
                        %(balance_select)s                                               AS amount,
                        %(balance_select)s                                               AS balance,
                        account_move.name                                                AS move_name,
                        account_move.id                                                  AS move_id,
                        account_move.move_type                                           AS move_type,
                        %(account_code)s                                                 AS account_code,
                        account_move.amount_residual                                     AS remaining_amount,
                        account_move.amount_residual_signed                              AS remaining_amount_signed,
                        account_move.due_date_upload                                     AS due_date_upload,
                        %(account_name)s                                                 AS account_name,
                        journal.code                                                     AS journal_code,
                        %(journal_name)s                                                 AS journal_name,
                        %(column_group_key)s                                             AS column_group_key,
                        'indirectly_linked_aml'                                          AS key,
                        partial.id                                                       AS partial_id
                    FROM %(table_references)s
                        %(currency_table_join)s,
                        account_partial_reconcile partial,
                        account_move,
                        account_move_line aml_with_partner,
                        account_journal journal
                    WHERE
                        (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                        AND account_move_line.partner_id IS NULL
                        AND account_move.id = account_move_line.move_id
                        AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                        AND %(indirectly_linked_aml_partner_clause)s
                        AND journal.id = account_move_line.journal_id
                        AND %(account_alias)s.id = account_move_line.account_id
                        AND %(search_condition)s
                        AND partial.max_date BETWEEN %(date_from)s AND %(date_to)s
                    ORDER BY %(order_by)s
                    ''',
                    additional_columns=additional_columns,
                    debit_select=report._currency_table_apply_rate(
                        SQL("CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END")),
                    credit_select=report._currency_table_apply_rate(
                        SQL("CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END")),
                    balance_select=report._currency_table_apply_rate(
                        SQL("-SIGN(aml_with_partner.balance) * partial.amount")),
                    account_code=account_code,
                    account_name=account_name,
                    journal_name=journal_name,
                    column_group_key=column_group_key,
                    table_references=query.from_clause,
                    currency_table_join=report._currency_table_aml_join(group_options),
                    indirectly_linked_aml_partner_clause=indirectly_linked_aml_partner_clause,
                    account_alias=SQL.identifier(account_alias),
                    search_condition=query.where_clause,
                    date_from=group_options['date']['date_from'],
                    date_to=group_options['date']['date_to'],
                    order_by=order_by,
                ))

            query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

            if offset:
                query = SQL('%s OFFSET %s ', query, offset)

            if limit:
                query = SQL('%s LIMIT %s ', query, limit)

            self._cr.execute(query)
            for aml_result in self._cr.dictfetchall():
                partner_id = aml_result['partner_id']
                currency_id = aml_result['currency_id']

                # Get currency name or fall back to company currency
                currency_name = currency_names.get(currency_id, company_currency)

                if aml_result['key'] == 'indirectly_linked_aml':
                    # Append the line to the partner found through the reconciliation
                    if partner_id in rslt:
                        if currency_name not in rslt[partner_id]:
                            rslt[partner_id][currency_name] = []
                        rslt[partner_id][currency_name].append(aml_result)

                    # Balance it with an additional line in the Unknown Partner section but having reversed amounts
                    if None in rslt:
                        reversed_aml = {
                            **aml_result,
                            'debit': aml_result['credit'],
                            'credit': aml_result['debit'],
                            'amount': aml_result['credit'] - aml_result['debit'],
                            'balance': -aml_result['balance'],
                        }
                        if currency_name not in rslt[None]:
                            rslt[None][currency_name] = []
                        rslt[None][currency_name].append(reversed_aml)
                else:
                    if partner_id in rslt:  # Ensure partner_id exists (should always be true)
                        if currency_name not in rslt[partner_id]:
                            rslt[partner_id][currency_name] = []
                        rslt[partner_id][currency_name].append(aml_result)

            return rslt

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['buttons'].append({
            'name': _('Supplier SOA XLSX'),
            'action': 'export_file',
            'action_param': 'export_to_xlsx_supplier_soa',
            'sequence': 90,
            'always_show': True,
        })
        options['buttons'].append(
                     {'name': _('Supplier SOA PDF'), 'sequence': 90, 'action': 'export_file',
                      'action_param': 'supplier_soa_pdf_export',
                      'file_export_type': _('PDF'), 'branch_allowed': True, 'always_show': True}, )

    # def supplier_soa_pdf_export(self, options):
    #     report = self.env['account.report'].browse(options['report_id'])
    #     company_currency = self.env.company.currency_id
    #
    #     partner_lines, totals_by_column_group = self.env[report.custom_handler_model_name]._build_partner_lines(report,
    #                                                                                                             options)
    #
    #     doc_list = []
    #     for partner_line in partner_lines:
    #         _, record_id = report._get_model_info_from_id(partner_line['id'])
    #         data = self.with_context(from_supplier_soa=True)._get_aml_values_customer_statement(
    #             options, partner_ids=[record_id], offset=0, limit=None
    #         )
    #
    #         partner = self.env['res.partner'].browse(record_id)
    #         lines = []
    #         total_amount = 0
    #
    #         for currency_data in data.values():
    #             for lines_by_currency in currency_data.values():
    #                 for line in lines_by_currency:
    #                     move = self.env['account.move'].browse(line['move_id'])
    #                     lines.append({
    #                         'date': move.invoice_date,
    #                         'journal': move.journal_id.name,
    #                         'name': move.name,
    #                         'ref': move.ref,
    #                         'due_date': move.invoice_date_due,
    #                         'currency': move.currency_id.name,
    #                         'amount': "{:,.2f}".format(line['amount']),
    #                         'payment_term': move.invoice_payment_term_id.name or '',
    #                     })
    #                     total_amount += line['amount'] or 0
    #
    #         doc_list.append({
    #             'partner': partner,
    #             'lines': lines,
    #             'total': "{:,.2f}".format(total_amount),
    #         })
    #
    #     pdf_content, _ =self.env["ir.actions.report"].sudo()._render_qweb_pdf(
    #             'gulfco_account_reports.action_supplier_soa_pdf',
    #             None, data={'docs': doc_list}
    #
    #         )
    #
    #     return {
    #         'type': 'ir.actions.report',
    #         'report_type': 'qweb-pdf',
    #         'data': {
    #             'report_name': 'gulfco_account_reports.action_supplier_soa_pdf',
    #             'report_type': 'qweb-pdf',
    #             'file_content': pdf_content,
    #             'context': {'docs': doc_list},
    #         }
    #     }

    def supplier_soa_pdf_export(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        company_currency = self.env.company.currency_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')

        files_stream = []
        doc_list = []
        partner_lines, totals_by_column_group = self.env[report.custom_handler_model_name]._build_partner_lines(report,
                                                                                                                options)


        for partner_line in partner_lines:
            _, record_id = report._get_model_info_from_id(partner_line['id'])

            data = self.with_context(from_supplier_soa=True)._get_aml_values_customer_statement(
                options, partner_ids=[record_id], offset=0, limit=None
            )

            partner = self.env['res.partner'].browse(record_id)
            lines = []
            total_amount = 0
            total_balance = 0.0
            for currency_data in data.values():
                for lines_by_currency in currency_data.values():
                    for line in lines_by_currency:
                        move = self.env['account.move'].browse(line['move_id'])
                        purchase_order = move.line_ids.mapped('purchase_line_id.order_id')
                        po_rev = ''
                        if purchase_order:
                            po_rev = ','.join(purchase_order.mapped('name'))
                        if move.due_date_upload:
                            due_date = move.due_date_upload
                        else:
                            due_date = move.invoice_date_due
                        if move.move_type == 'in_invoice':
                            balance = abs(line['amount_currency']) or 0.0
                            balance_aed = abs(line['amount']) or 0.0
                            original_remaining_aed = abs(line['remaining_amount_signed']) or 0.0
                        elif move.move_type == 'in_refund':
                            balance = -(line['amount_currency'])
                            balance_aed = -(line['amount'])
                            original_remaining_aed = -(line['remaining_amount_signed'])
                        else:
                            balance = line['amount_currency']
                            balance_aed = line['amount']
                            original_remaining_aed = line['remaining_amount_signed']
                        lines.append({
                            'date': move.invoice_date,
                            'journal': move.journal_id.name,
                            'name': move.name,
                            'ref': move.ref,
                            'due_date': due_date,
                            'currency': move.currency_id.name,
                            'amount': "{:,.2f}".format(line['amount']),
                            'payment_term': move.invoice_payment_term_id.name or '',
                            'receipt_date':move.receipt_date or '',
                            'po_rev':po_rev,
                            'pay_group': move.company_id.name,
                            'balance' : "{:,.2f}".format(balance) ,
                            'balance_aed':"{:,.2f}".format(balance_aed),
                            'original_remaining':"{:,.2f}".format(line['remaining_amount']) or 0,
                            'original_remaining_aed': "{:,.2f}".format(original_remaining_aed),
                            'division_code':move.company_id.division_code or ''
                        })
                        total_amount += line['amount'] or 0
                        total_balance += line['amount_currency'] or 0
            pdc_payments = self.env['account.payment'].sudo().search([('payment_type','=','outbound'),('partner_id','=',partner.id),('payment_mode','=','pdc'),('state','in',['in_process','paid']),('pdc_state','in',['registered','deposit'])])
            advance_payments = self.env['account.payment'].sudo().search([('purchase_id', '!=', False),('advance_sale_purchase', '=', 'purchase'),('payment_type','=','outbound'),('partner_type','=','supplier'),('partner_id','=',partner.id),('state','not in',['paid','canceled','rejected'])])
            pdc_amount = sum(pdc_payments.mapped('amount_company_currency_signed'))
            prepayment_amount = sum(advance_payments.mapped('amount_company_currency_signed'))
            doc_list.append({
                'partner': partner,
                'lines': lines,
                'total': "{:,.2f}".format(abs(total_amount)),
                'date_from':options['date']['date_from'],
                'date_to': options['date']['date_to'],
                'company' : self.env.company.name,
                'pdc_amount':"{:,.2f}".format(pdc_amount),
                'prepayment_amount':"{:,.2f}".format(prepayment_amount),
                'total_balance':"{:,.2f}".format(abs(total_balance))
            })

        # Prepare footer for report layout (optional but good for polished PDF)
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        action_report = self.env['ir.actions.report']
        footer = action_report._render_template("account_reports.internal_layout", values=rcontext)
        # footer = action_report._render_template("web.minimal_layout",
        #                                         values=dict(rcontext, subst=True, body=Markup(footer.decode())))

        # Render the PDF
        # body = self.env.ref('gulfco_account_reports.report_supplier_soa_pdf')._render({
        #     'docs': doc_list,
        #     'base_url': base_url
        # })[0]

        try:
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                'gulfco_account_reports.report_supplier_soa_pdf',
                data={'docs': doc_list}
            )

        except Exception as e:
            _logger.exception("Failed to render Supplier SOA PDF: %s", e)
            raise UserError("An error occurred while generating the PDF: %s" % str(e))
        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})
        render_values = {
            'docs':doc_list,
            'print_options': print_options,
            'base_url': base_url,
        }
        bodies = self.env['ir.qweb']._render('gulfco_account_reports.report_supplier_soa_pdf', render_values)
        files_stream.append(
            io.BytesIO(action_report._run_wkhtmltopdf(
            [bodies],
            footer=footer.decode(),
            landscape=True,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
            }
            )
            )
        )
        result = files_stream[0].read()



        return {
            'file_name': 'Supplier_SOA_Report.pdf',
            'file_content': result,
            'file_type': 'pdf',
        }

    def export_to_xlsx_supplier_soa(self, options, response=None, **kwargs):
        report = self.env['account.report'].browse(options['report_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': True,
        })

        company_currency = self.env.company.currency_id
        worksheet = workbook.add_worksheet(f"Supplier Statement")

        report_info_format = workbook.add_format({
            "bold": True, "align": "left", "valign": "vcenter", "font_size": 16,
        })
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        header_format = workbook.add_format({"bold": True, "border": 1, 'text_wrap': True})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        date_format = workbook.add_format({
            'num_format': 'mm/dd/yyyy',
            'align': 'left',
            'valign': 'vcenter',
        })
        text_format = workbook.add_format({
            'font_name': 'Calibri',
            'font_size': 11,
            'align': 'left',
            'valign': 'top'
        })

        headers = [
            "Name", "Transaction Date", "Trx Type", "Invoice No", "Receipt Date", "Doc Number",
            "Po Rev", "Due Date", "Balance", "Currency", "Balance AED","Original Remaining","Remaining in AED", "Payment Terms", "Div Code"
        ]
        headers_foreign_curr = [
            "Name", "Transaction Date", "Trx Type", "Invoice No", "Receipt Date", "Doc Number",
            "Po Rev", "Due Date", "Original Currency", "Original Amount",
            "Balance", "Currency", "Balance AED","Original Remaining","Remaining in AED", "Payment Terms", "Div Code"
        ]

        print_options = report.get_options(previous_options={**options, 'export_mode': 'print'})
        reports_options = [r.get_options(previous_options={**print_options, 'selected_section_id': r.id}) for r in
                           report]

        partner_lines, totals_by_column_group = self.env[report.custom_handler_model_name]._build_partner_lines(report,
                                                                                                                options)

        has_foreign_currency = False
        for partner_line in partner_lines:
            _, record_id = report._get_model_info_from_id(partner_line['id'])
            data = self.with_context(from_supplier_soa=True)._get_aml_values_customer_statement(
                options, partner_ids=[record_id], offset=0, limit=None)
            if any(currency_name != company_currency.name for partner_data in data.values() for currency_name in
                   partner_data):
                has_foreign_currency = True
                break

        active_headers = headers_foreign_curr if has_foreign_currency else headers
        # for col_num, header in enumerate(active_headers):
        #     worksheet.write(0, col_num, header, header_format)

        row = 0
        for partner_line in partner_lines:
            _, record_id = report._get_model_info_from_id(partner_line['id'])
            data = self.with_context(from_supplier_soa=True)._get_aml_values_customer_statement(
                options, partner_ids=[record_id], offset=0, limit=None)

            partner_id = self.env['res.partner'].browse(record_id)
            worksheet.write(row, 0, "Supplier Name", header_format)
            worksheet.write(row, 1, partner_id.name if partner_id else '', text_format)

            worksheet.write(row + 1, 0, "Supplier Number", header_format)
            worksheet.write(row + 1, 1, partner_id.vendor_code if partner_id else '', text_format)

            worksheet.write(row + 2, 0, "Address", header_format)
            worksheet.write(row + 2, 1, partner_id.contact_address if partner_id else '', text_format)

            worksheet.write(row + 3, 0, "Telephone", header_format)
            worksheet.write(row + 3, 1, partner_id.phone if partner_id else '', text_format)

            # Right Column (D–E)
            worksheet.write(row, 3, "Payment Term", header_format)
            worksheet.write(row, 4,
                            partner_id.property_supplier_payment_term_id.name if partner_id and partner_id.property_supplier_payment_term_id else '',
                            text_format)

            worksheet.write(row + 1, 3, "System Date", header_format)
            worksheet.write(row + 1, 4, date_from if date_from else '', date_format)

            worksheet.write(row + 2, 3, "As Of Date", header_format)
            worksheet.write(row + 2, 4, date_to if date_to else '', date_format)

            worksheet.write(row + 3, 3, "Legal Entity", header_format)
            worksheet.write(row + 3, 4, self.env.company.name, text_format)
            row += 5
            for col_num, header in enumerate(active_headers):
                worksheet.write(row, col_num, header, header_format)
            row += 1
            # Accumulators per vendor
            company_currency_accumulative = 0
            foreign_currency_accumulative = 0
            last_foreign_currency = None

            for partner_id_key, currency_data in data.items():
                for currency_name, lines in currency_data.items():
                    for line in lines:
                        move_id = self.env['account.move'].browse(line['move_id'])
                        purchase_order = move_id.line_ids.mapped('purchase_line_id.order_id')
                        po_rev = ''
                        if purchase_order:
                            po_rev = ','.join(purchase_order.mapped('name'))
                        if move_id.due_date_upload:
                            due_date = move_id.due_date_upload
                        else:
                            due_date = move_id.invoice_date_due
                        worksheet.write(row, 0, partner_id.name or '')
                        worksheet.write(row, 1, move_id.invoice_date or '', date_format)
                        worksheet.write(row, 2, move_id.journal_id.name or '', text_format)
                        worksheet.write(row, 3, move_id.name or '', text_format)
                        worksheet.write(row, 4, move_id.receipt_date or '', date_format)
                        worksheet.write(row, 5, move_id.ref or '', text_format)
                        worksheet.write(row, 6, po_rev, text_format)
                        worksheet.write(row, 7, due_date or '', date_format)
                        # worksheet.write(row, 8, move_id.company_id.name or '', text_format)

                        is_foreign_line = (currency_name != company_currency.name)
                        if is_foreign_line:
                            last_foreign_currency = currency_name

                        if move_id.move_type == 'in_invoice':
                            amount_currency = abs(line['amount_currency']) or 0.0
                            balance = abs(line['balance']) or 0.0
                            amount = abs(line['amount']) or 0.0
                            remaining_amount = abs(line['remaining_amount']) or 0.0
                            remaining_amount_signed = abs(line['remaining_amount_signed']) or 0.0
                        elif move_id.move_type == 'in_refund':
                            amount_currency = -(line['amount_currency'])
                            balance = -(line['balance'])
                            amount = -(line['amount'])
                            remaining_amount = -(line['remaining_amount'])
                            remaining_amount_signed = -(line['remaining_amount_signed'])
                        else:
                            amount_currency = line['amount_currency']
                            balance = line['balance']
                            amount = line['amount']
                            remaining_amount = line['remaining_amount']
                            remaining_amount_signed = line['remaining_amount_signed']


                        if has_foreign_currency:
                            worksheet.write(row, 8, move_id.currency_id.name if is_foreign_line else '-', text_format)
                            worksheet.write(row, 9, amount_currency if is_foreign_line else '-',
                                            number_format if is_foreign_line else text_format)
                            worksheet.write(row, 10, balance or 0, number_format)
                            worksheet.write(row, 11, company_currency.name or '', text_format)
                            worksheet.write(row, 12, amount or 0, number_format)
                            worksheet.write(row, 13, remaining_amount or 0, number_format)
                            worksheet.write(row, 14, remaining_amount_signed or 0, number_format)
                            worksheet.write(row, 15, move_id.invoice_payment_term_id.name or '', text_format)
                            worksheet.write(row, 16, move_id.company_id.division_code or '', text_format)
                        else:
                            worksheet.write(row, 8, balance or 0, number_format)
                            worksheet.write(row, 9, company_currency.name or '', text_format)
                            worksheet.write(row, 10, amount or 0, number_format)
                            worksheet.write(row, 11, remaining_amount or 0, number_format)
                            worksheet.write(row, 12, remaining_amount_signed or 0, number_format)
                            worksheet.write(row, 13, move_id.invoice_payment_term_id.name or '', text_format)
                            worksheet.write(row, 14, move_id.company_id.division_code or '', text_format)

                        # Add to accumulators
                        company_currency_accumulative += line['amount'] or 0
                        if is_foreign_line:
                            foreign_currency_accumulative += line['amount_currency'] or 0
                        row += 1

            # Totals per partner
            total_label_format = workbook.add_format({'bold': True, 'top': 1})
            if has_foreign_currency and foreign_currency_accumulative and last_foreign_currency:
                worksheet.write(row, 0, f"Total balance For: {last_foreign_currency}", total_label_format)
                worksheet.write(row, 1, foreign_currency_accumulative, total_label_format)
                row += 1

            if company_currency_accumulative:
                worksheet.write(row, 0, f"Total Balance Supplier: {company_currency.name}", total_label_format)
                worksheet.write(row, 1, company_currency_accumulative, total_label_format)
                row += 3

            advance_payments = self.env['account.payment'].sudo().search([('purchase_id', '!=', False),('advance_sale_purchase', '=', 'purchase'),('payment_type','=','outbound'),('partner_type','=','supplier'),('partner_id','=',partner_id.id),('state','not in',['paid','canceled','rejected'])])
            if has_foreign_currency and foreign_currency_accumulative and last_foreign_currency:
                worksheet.write(row, 0, f"Total Outstanding : {last_foreign_currency}", total_label_format)
                worksheet.write(row, 1, foreign_currency_accumulative, total_label_format)
                if advance_payments:
                    row += 1
                else:
                    row += 3
            if advance_payments:
                advance_payment_amount = sum(advance_payments.mapped('amount_company_currency_signed'))
                worksheet.write(row, 0, f"Total Prepayments (AED)", total_label_format)
                worksheet.write(row, 1, abs(advance_payment_amount), number_format)
                row += 3
        # Set column widths
        worksheet.set_column(0, 1, 23)
        worksheet.set_column(1, len(active_headers), 18)
        
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': 'Supplier_SOA.xlsx',
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

