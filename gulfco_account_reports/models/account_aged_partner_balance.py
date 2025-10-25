import datetime

from odoo import models, fields, _
from odoo.tools import SQL
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain

class AgedPartnerBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.aged.partner.balance.report.handler'


    def _custom_options_initializer(self, report, options, previous_options):
        # Call the base method first
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Then update the column names for all 10 periods (0 through 9)
        interval = options['aging_interval']
        for column in options['columns']:
            if column['expression_label'].startswith('period'):
                try:
                    period_number = int(column['expression_label'].replace('period', '')) - 1
                    if 0 <= period_number < 3:
                        start_day = interval * period_number + 1
                        end_day = interval * (period_number + 1)
                        column['name'] = f'{start_day}-{end_day}'

                    elif period_number == 3:
                        start_day = interval * period_number + 1
                        end_day = interval * (period_number + 1) + (interval*2)
                        column['name'] = f'{start_day}-{end_day}'

                    if 5 <= period_number < 6:
                        start_day = (interval * period_number + 1) + (interval)
                        end_day = (interval*2) * (period_number + 1)
                        column['name'] = f'{start_day}-{end_day}'


                    elif period_number == 4:
                        column['name'] =f'Older {interval * 4 * 3 } +'

                    # if period_number == 6:
                    #     column['name'] = f'Greater {interval * period_number * 2 } +'
                    # elif period_number == 7:
                    #     column['name'] = f'Over {interval * 3 } +'
                except ValueError:
                    continue

    def _common_custom_unfold_all_batch_data_generator(self, internal_type, report, options,
                                                       lines_to_expand_by_function):
        rslt = {}  # In the form {full_sub_groupby_key: all_column_group_expression_totals for this groupby computation}
        report_periods = 7  # The report has 6 periods

        for expand_function_name, lines_to_expand in lines_to_expand_by_function.items():
            for line_to_expand in lines_to_expand:  # In standard, this loop will execute only once
                if expand_function_name == '_report_expand_unfoldable_line_with_groupby':
                    report_line_id = report._get_res_id_from_line_id(line_to_expand['id'], 'account.report.line')
                    expressions_to_evaluate = report.line_ids.expression_ids.filtered(
                        lambda x: x.report_line_id.id == report_line_id and x.engine == 'custom')

                    if not expressions_to_evaluate:
                        continue

                    for column_group_key, column_group_options in report._split_options_per_column_group(
                            options).items():
                        # Get all aml results by partner
                        aml_data_by_partner = {}
                        for aml_id, aml_result in self._aged_partner_report_custom_engine_common(column_group_options,
                                                                                                 internal_type, 'id',
                                                                                                 None):
                            aml_result['aml_id'] = aml_id
                            aml_data_by_partner.setdefault(aml_result['partner_id'], []).append(aml_result)

                        # Iterate on results by partner to generate the content of the column group
                        partner_expression_totals = rslt.setdefault(f"[{report_line_id}]=>partner_id", {}) \
                            .setdefault(column_group_key,
                                        {expression: {'value': []} for expression in expressions_to_evaluate})
                        for partner_id, aml_data_list in aml_data_by_partner.items():
                            partner_values = self._prepare_partner_values()
                            for i in range(report_periods):
                                partner_values[f'period{i}'] = 0

                            # Build expression totals under the right key
                            partner_aml_expression_totals = rslt.setdefault(
                                f"[{report_line_id}]partner_id:{partner_id}=>id", {}) \
                                .setdefault(column_group_key,
                                            {expression: {'value': []} for expression in expressions_to_evaluate})
                            for aml_data in aml_data_list:
                                for i in range(report_periods):
                                    period_value = aml_data[f'period{i}']
                                    partner_values[f'period{i}'] += period_value
                                    partner_values['total'] += period_value

                                for expression in expressions_to_evaluate:
                                    partner_aml_expression_totals[expression]['value'].append(
                                        (aml_data['aml_id'], aml_data[expression.subformula])
                                    )

                            for expression in expressions_to_evaluate:
                                partner_expression_totals[expression]['value'].append(
                                    (partner_id, partner_values[expression.subformula])
                                )

        return rslt

    def _aged_partner_report_custom_engine_common(self, options, internal_type, current_groupby, next_groupby, offset=0, limit=None):
        if internal_type == 'liability_payable':
            report = self.env['account.report'].browse(options['report_id'])
            report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))
    
            def minus_days(date_obj, days):
                return fields.Date.to_string(date_obj - relativedelta(days=days))
    
            aging_date_field = SQL.identifier('invoice_date') if options['aging_based_on'] == 'base_on_invoice_date' else SQL.identifier('date_maturity')
            date_to = fields.Date.from_string(options['date']['date_to'])
            interval = options['aging_interval']
            periods = [(False, fields.Date.to_string(date_to))]
            # Since we added the first period in the list we have to do one less iteration
            nb_periods = len([column for column in options['columns'] if column['expression_label'].startswith('period')]) - 1
            for i in range(nb_periods):
                if 0 <= i < 3:
                    start_date = minus_days(date_to, (interval * i) + 1)
                    # The last element of the list will have False for the end date
                    end_date = minus_days(date_to, interval * (i + 1)) if i < nb_periods - 1 else False
                    periods.append((start_date, end_date))

                elif i == 3:

                    start_date = minus_days(date_to, (interval * i) + 1)
                    # The last element of the list will have False for the end date
                    end_date = minus_days(date_to,
                                          interval * (i + 1) + (interval * 2)) if i < nb_periods - 1 else False
                    periods.append((start_date, end_date))

                if 5 <= i < 6:
                    start_date = minus_days(date_to, (interval * i) + (interval) + 1)
                    # The last element of the list will have False for the end date
                    # end_date = minus_days(date_to, (interval * 2) * (i + 1)) if i < nb_periods - 1 else False
                    end_date = minus_days(date_to, (interval * 2) * (i + 1))
                    periods.append((start_date, end_date))

                # if i == 6:
                #     start_date = minus_days(date_to, (interval * i * 2))
                #     # The last element of the list will have False for the end date
                #     end_date = False
                #     periods.append((start_date, end_date))
                #
                # elif i == 7:
                #     start_date = minus_days(date_to, (interval * 3))
                #     # The last element of the list will have False for the end date
                #     end_date = False
                #     periods.append((start_date, end_date))

                elif i == 4:
                    start_date = minus_days(date_to, (interval * i * 3) + 1 )
                    # The last element of the list will have False for the end date
                    end_date = False
                    periods.append((start_date, end_date))
    
            def build_result_dict(report, query_res_lines):
                rslt = {f'period{i}': 0 for i in range(len(periods))}
    
                for query_res in query_res_lines:
                    for i in range(len(periods)):
                        period_key = f'period{i}'
                        rslt[period_key] += query_res[period_key]
    
                if current_groupby == 'id':
                    query_res = query_res_lines[0] # We're grouping by id, so there is only 1 element in query_res_lines anyway
                    currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(query_res['currency_id']) == 1 else None
                    rslt.update({
                        'invoice_date': query_res['invoice_date'][0] if len(query_res['invoice_date']) == 1 else None,
                        'invoice_received_date': query_res['invoice_received_date'][0] if len(query_res['invoice_received_date']) == 1 else None,
                        'date': query_res['date'][0] if len(query_res['date']) == 1 else None,
                        'due_date': query_res['due_date'][0] if len(query_res['due_date']) == 1 else None,
                        'amount_currency': query_res['amount_currency'],
                        'partner_name': query_res['partner_name'][0] if query_res['partner_name'] else None,
                        'local_balance' : query_res['local_balance'] if query_res['local_balance'] else None,
                        'payment_term_name' : query_res['payment_term_name'] if query_res['payment_term_name'] else None,
                        'payment_method_name' : query_res['payment_method_name'] if query_res['payment_method_name'] else None,
                        'payment_state' : query_res['payment_state'][0] if query_res['payment_state'] else None,
                        'currency_rate' : query_res['currency_rate'][0] if query_res['currency_rate'] else None,
                        'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                        'currency': currency.display_name if currency else None,
                        'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                        'chart_account_name': query_res['chart_account_name'][0] if len(query_res['chart_account_name']) == 1 else None,
                        'total': None,
                        'has_sublines': query_res['aml_count'] > 0,
    
                        # Needed by the custom_unfold_all_batch_data_generator, to speed-up unfold_all
                        'partner_id': query_res['partner_id'][0] if query_res['partner_id'] else None,
                        'supplier_type' : query_res['supplier_type'][0] if query_res['supplier_type'] else None,
                        'division_name' : query_res['division_name'][0] if query_res['division_name'] else None,
                        'division_code' : query_res['division_code'][0] if query_res['division_code'] else None,
                        'vendor_number' : query_res['vendor_number'][0] if query_res['vendor_number'] else None,
                        'move_ref' : query_res['move_ref'][0] if query_res['move_ref'] else None,
                        'journal_name' : query_res['journal_name'][0] if query_res['journal_name'] else None,
                        'cost_center_name' : query_res['cost_center_name'][0] if query_res['cost_center_name'] else None,
                        'move_name': query_res['move_name'][0] if query_res['move_name'] else None,
                        'payment_reference' : query_res['payment_reference'][0] if query_res['payment_reference'] else None
                    })
                else:
                    rslt.update({
                        'invoice_date': None,
                        'invoice_received_date':None,
                        'due_date': None,
                        'amount_currency': None,
                        'currency_id': None,
                        'currency': None,
                        'account_name': None,
                        'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                        'has_sublines': False,
                    })
    
                return rslt
    
            # Build period table
            period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for period in periods))
            params = list(chain.from_iterable(
                (period[0] or None, period[1] or None, i)
                for i, period in enumerate(periods)
            ))
            period_table = SQL(period_table_format, *params)
    
            # Build query
            query = report._get_report_query(options, 'strict_range', domain=[('account_id.account_type', '=', internal_type)])
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id', rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            chart_account_name = self.env['account.account']._field_to_sql(account_alias, 'name', query)

            always_present_groupby = SQL("period_table.period_index")
            if current_groupby:
                select_from_groupby = SQL("%s AS grouping_key,", SQL.identifier("account_move_line", current_groupby))
                groupby_clause = SQL("%s, %s", SQL.identifier("account_move_line", current_groupby), always_present_groupby)
            else:
                select_from_groupby = SQL()
                groupby_clause = always_present_groupby
            multiplicator = -1 if internal_type == 'liability_payable' else 1
            select_period_query = SQL(',').join(
                SQL("""
                    CASE WHEN period_table.period_index = %(period_index)s
                    THEN %(multiplicator)s * SUM(%(balance_select)s)
                    ELSE 0 END AS %(column_name)s
                    """,
                    period_index=i,
                    multiplicator=multiplicator,
                    column_name=SQL.identifier(f"period{i}"),
                    balance_select=report._currency_table_apply_rate(SQL(
                        "account_move_line.balance - COALESCE(part_debit.amount, 0) + COALESCE(part_credit.amount, 0)"
                    )),
                )
                for i in range(len(periods))
            )
    
            tail_query = report._get_engine_query_tail(offset, limit)
            query = SQL(
                """
                WITH period_table(date_start, date_stop, period_index) AS (%(period_table)s)
    
                SELECT
                    %(select_from_groupby)s
                    %(multiplicator)s * (
                        SUM(account_move_line.amount_currency)
                        - COALESCE(SUM(part_debit.debit_amount_currency), 0)
                        + COALESCE(SUM(part_credit.credit_amount_currency), 0)
                    ) AS amount_currency,
                    %(multiplicator)s * (SUM(account_move_line.balance)) AS local_balance,
                    ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                    ARRAY_AGG(DISTINCT account_payment_term.name -> 'en_US') AS payment_term_name,
                    ARRAY_AGG(DISTINCT account_payment_method_line.name) AS payment_method_name,
                    ARRAY_AGG(DISTINCT move.invoice_currency_rate) AS currency_rate,
                    ARRAY_AGG(DISTINCT move.ref) AS move_ref,
                    ARRAY_AGG(DISTINCT partner.supplier_type) AS supplier_type,
                    ARRAY_AGG(DISTINCT partner.name) AS partner_name,
                    ARRAY_AGG(DISTINCT partner.vendor_code) AS vendor_number,
                    ARRAY_AGG(DISTINCT journal.name -> 'en_US') AS journal_name,
                    ARRAY_AGG(DISTINCT company.name) AS division_name,
                    ARRAY_AGG(DISTINCT company.division_code) AS division_code,
                    ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                    ARRAY_AGG(account_move_line.cost_center_name) AS cost_center_name,
                    ARRAY_AGG(DISTINCT move.invoice_date) AS invoice_date,
                    ARRAY_AGG(DISTINCT move.receipt_date) AS invoice_received_date,
                    ARRAY_AGG(DISTINCT move.date) AS date,
                    ARRAY_AGG(DISTINCT move.name) AS move_name,
                    ARRAY_AGG(DISTINCT move.payment_state) AS payment_state,
                    ARRAY_AGG(DISTINCT move.payment_reference) AS payment_reference,
                    ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS report_date,
                    ARRAY_AGG(DISTINCT %(account_code)s) AS account_name,
                    ARRAY_AGG(DISTINCT %(chart_account_name)s) AS chart_account_name,
                    ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS due_date,
                    ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                    COUNT(account_move_line.id) AS aml_count,
                    ARRAY_AGG(%(account_code)s) AS account_code,
                    %(select_period_query)s
    
                FROM %(table_references)s
    
                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_move move ON move.id = account_move_line.move_id
                LEFT JOIN res_partner partner ON partner.id =  account_move_line.partner_id
                LEFT JOIN res_company company ON company.id =  move.company_id
                LEFT JOIN account_payment_term ON account_payment_term.id = move.invoice_payment_term_id
                LEFT JOIN account_payment_method_line ON account_payment_method_line.id = move.preferred_payment_method_line_id
                %(currency_table_join)s
    
                LEFT JOIN LATERAL (
                    SELECT
                        SUM(part.amount) AS amount,
                        SUM(part.debit_amount_currency) AS debit_amount_currency,
                        part.debit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date_to)s AND part.debit_move_id = account_move_line.id
                    GROUP BY part.debit_move_id
                ) part_debit ON TRUE
    
                LEFT JOIN LATERAL (
                    SELECT
                        SUM(part.amount) AS amount,
                        SUM(part.credit_amount_currency) AS credit_amount_currency,
                        part.credit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date_to)s AND part.credit_move_id = account_move_line.id
                    GROUP BY part.credit_move_id
                ) part_credit ON TRUE
    
                JOIN period_table ON
                    (
                        period_table.date_start IS NULL
                        OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) <= DATE(period_table.date_start)
                    )
                    AND
                    (
                        period_table.date_stop IS NULL
                        OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) >= DATE(period_table.date_stop)
                    )
    
                WHERE %(search_condition)s
    
                GROUP BY %(groupby_clause)s
    
                HAVING
                    ROUND(SUM(%(having_debit)s), %(currency_precision)s) != 0
                    OR ROUND(SUM(%(having_credit)s), %(currency_precision)s) != 0
    
                ORDER BY %(groupby_clause)s
    
                %(tail_query)s
                """,
                account_code=account_code,
                chart_account_name=chart_account_name,
                period_table=period_table,
                select_from_groupby=select_from_groupby,
                select_period_query=select_period_query,
                multiplicator=multiplicator,
                aging_date_field=aging_date_field,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options),
                date_to=date_to,
                search_condition=query.where_clause,
                groupby_clause=groupby_clause,
                having_debit=report._currency_table_apply_rate(SQL("CASE WHEN account_move_line.balance > 0  THEN account_move_line.balance else 0 END - COALESCE(part_debit.amount, 0)")),
                having_credit=report._currency_table_apply_rate(SQL("CASE WHEN account_move_line.balance < 0  THEN -account_move_line.balance else 0 END - COALESCE(part_credit.amount, 0)")),
                currency_precision=self.env.company.currency_id.decimal_places,
                tail_query=tail_query,
            )
    
            self._cr.execute(query)
            query_res_lines = self._cr.dictfetchall()
    
            if not current_groupby:
                return build_result_dict(report, query_res_lines)
            else:
                rslt = []
    
                all_res_per_grouping_key = {}
                for query_res in query_res_lines:
                    grouping_key = query_res['grouping_key']
                    all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)
    
                for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                    rslt.append((grouping_key, build_result_dict(report, query_res_lines)))
    
                return rslt

        elif internal_type == 'asset_receivable':
            report = self.env['account.report'].browse(options['report_id'])
            report._check_groupby_fields(
                (next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

            def minus_days(date_obj, days):
                return fields.Date.to_string(date_obj - relativedelta(days=days))

            aging_date_field = SQL.identifier('invoice_date') if options[
                                                                     'aging_based_on'] == 'base_on_invoice_date' else SQL.identifier(
                'date_maturity')
            date_to = fields.Date.from_string(options['date']['date_to'])
            interval = options['aging_interval']
            periods = [(False, fields.Date.to_string(date_to))]
            # Since we added the first period in the list we have to do one less iteration
            nb_periods = len(
                [column for column in options['columns'] if column['expression_label'].startswith('period')]) - 1
            for i in range(nb_periods):
                if 0 <= i < 3:
                    start_date = minus_days(date_to, (interval * i) + 1)
                    # The last element of the list will have False for the end date
                    end_date = minus_days(date_to, interval * (i + 1)) if i < nb_periods - 1 else False
                    periods.append((start_date, end_date))

                elif i == 3:

                    start_date = minus_days(date_to, (interval * i) + 1)
                    # The last element of the list will have False for the end date
                    end_date = minus_days(date_to,
                                          interval * (i + 1) + (interval * 2)) if i < nb_periods - 1 else False
                    periods.append((start_date, end_date))

                if 5 <= i < 6:
                    start_date = minus_days(date_to, (interval * i) + (interval) + 1)
                    # The last element of the list will have False for the end date
                    # end_date = minus_days(date_to, (interval * 2) * (i + 1)) if i < nb_periods - 1 else False
                    end_date = minus_days(date_to, (interval * 2) * (i + 1))
                    periods.append((start_date, end_date))

                # if i == 6:
                #     start_date = minus_days(date_to, (interval * i * 2))
                #     # The last element of the list will have False for the end date
                #     end_date = False
                #     periods.append((start_date, end_date))
                #
                # elif i == 7:
                #     start_date = minus_days(date_to, (interval * 3))
                #     # The last element of the list will have False for the end date
                #     end_date = False
                #     periods.append((start_date, end_date))

                elif i == 4:
                    start_date = minus_days(date_to, (interval * i * 3) + 1)
                    # The last element of the list will have False for the end date
                    end_date = False
                    periods.append((start_date, end_date))

            def build_result_dict(report, query_res_lines):
                rslt = {f'period{i}': 0 for i in range(len(periods))}

                for query_res in query_res_lines:
                    for i in range(len(periods)):
                        period_key = f'period{i}'
                        rslt[period_key] += query_res[period_key]

                if current_groupby == 'id':
                    query_res = query_res_lines[
                        0]  # We're grouping by id, so there is only 1 element in query_res_lines anyway
                    currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(
                        query_res['currency_id']) == 1 else None
                    rslt.update({
                        'invoice_date': query_res['invoice_date'][0] if len(query_res['invoice_date']) == 1 else None,
                        'invoice_received_date': query_res['invoice_received_date'][0] if len(query_res['invoice_received_date']) == 1 else None,
                        'date': query_res['date'][0] if len(query_res['date']) == 1 else None,
                        'due_date': query_res['due_date'][0] if len(query_res['due_date']) == 1 else None,
                        'amount_currency': query_res['amount_currency'],
                        'partner_id_record': query_res['partner_id_record'][0] if query_res['partner_id_record'] else None,
                        'partner_name': query_res['partner_name'][0] if query_res['partner_name'] else None,
                        'partner_code': query_res['partner_code'][0] if query_res['partner_code'] else None,
                        'customer_class': query_res['customer_class'][0] if query_res['customer_class'] else None,
                        'customer_category': query_res['customer_category'][0] if query_res['customer_category'] else None,
                        'partner_state': query_res['partner_state'][0] if query_res['partner_state'] else None,
                        'currency_rate': query_res['currency_rate'][0] if query_res['currency_rate'] else None,
                        'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                        'currency': currency.display_name if currency else None,
                        'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                        'payment_term_name': query_res['payment_term_name'] if query_res['payment_term_name'] else None,
                        'payment_method_name': query_res['payment_method_name'] if query_res['payment_method_name'] else None,
                        'chart_account_name': query_res['chart_account_name'][0] if len(
                            query_res['chart_account_name']) == 1 else None,
                        'total': None,
                        'has_sublines': query_res['aml_count'] > 0,

                        # Needed by the custom_unfold_all_batch_data_generator, to speed-up unfold_all
                        'partner_id': query_res['partner_id'][0] if query_res['partner_id'] else None,
                        'supplier_type': query_res['supplier_type'][0] if query_res['supplier_type'] else None,
                        'division_name': query_res['division_name'][0] if query_res['division_name'] else None,
                        'division_code': query_res['division_code'][0] if query_res['division_code'] else None,
                        'cost_center_name': query_res['cost_center_name'][0] if query_res['cost_center_name'] else None,
                        'move_name': query_res['move_name'][0] if query_res['move_name'] else None,
                        'payment_reference': query_res['payment_reference'][0] if query_res[
                            'payment_reference'] else None
                    })
                else:
                    rslt.update({
                        'invoice_date': None,
                        'invoice_received_date' : None,
                        'due_date': None,
                        'amount_currency': None,
                        'currency_id': None,
                        'currency': None,
                        'account_name': None,
                        'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                        'has_sublines': False,
                    })

                return rslt

            # Build period table
            period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for period in periods))
            params = list(chain.from_iterable(
                (period[0] or None, period[1] or None, i)
                for i, period in enumerate(periods)
            ))
            period_table = SQL(period_table_format, *params)

            # Build query
            query = report._get_report_query(options, 'strict_range',
                                             domain=[('account_id.account_type', '=', internal_type)])
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id',
                                            rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            chart_account_name = self.env['account.account']._field_to_sql(account_alias, 'name', query)

            always_present_groupby = SQL("period_table.period_index")
            if current_groupby:
                select_from_groupby = SQL("%s AS grouping_key,", SQL.identifier("account_move_line", current_groupby))
                groupby_clause = SQL("%s, %s", SQL.identifier("account_move_line", current_groupby),
                                     always_present_groupby)
            else:
                select_from_groupby = SQL()
                groupby_clause = always_present_groupby
            multiplicator = -1 if internal_type == 'liability_payable' else 1
            select_period_query = SQL(',').join(
                SQL("""
                    CASE WHEN period_table.period_index = %(period_index)s
                    THEN %(multiplicator)s * SUM(%(balance_select)s)
                    ELSE 0 END AS %(column_name)s
                    """,
                    period_index=i,
                    multiplicator=multiplicator,
                    column_name=SQL.identifier(f"period{i}"),
                    balance_select=report._currency_table_apply_rate(SQL(
                        "account_move_line.balance - COALESCE(part_debit.amount, 0) + COALESCE(part_credit.amount, 0)"
                    )),
                    )
                for i in range(len(periods))
            )

            tail_query = report._get_engine_query_tail(offset, limit)
            query = SQL(
                """
                WITH period_table(date_start, date_stop, period_index) AS (%(period_table)s)

                SELECT
                    %(select_from_groupby)s
                    %(multiplicator)s * (
                        SUM(account_move_line.amount_currency)
                        - COALESCE(SUM(part_debit.debit_amount_currency), 0)
                        + COALESCE(SUM(part_credit.credit_amount_currency), 0)
                    ) AS amount_currency,
                    %(multiplicator)s * (SUM(account_move_line.balance)) AS local_balance,
                    ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                    ARRAY_AGG(DISTINCT move.invoice_currency_rate) AS currency_rate,
                    ARRAY_AGG(DISTINCT partner.supplier_type) AS supplier_type,
                    ARRAY_AGG(DISTINCT partner.id) AS partner_id_record,
                    ARRAY_AGG(DISTINCT partner.name) AS partner_name,
                    ARRAY_AGG(DISTINCT partner.customer_code) AS partner_code,
                    ARRAY_AGG(DISTINCT customer_group.name) AS customer_class,
                    ARRAY_AGG(DISTINCT account_payment_term.name -> 'en_US') payment_term_name,
                    ARRAY_AGG(DISTINCT account_payment_method_line.name) AS payment_method_name,
                    ARRAY_AGG(DISTINCT partner.category) AS customer_category,
                    ARRAY_AGG(DISTINCT state.name) AS partner_state,
                    ARRAY_AGG(DISTINCT company.name) AS division_name,
                    ARRAY_AGG(DISTINCT company.division_code) AS division_code,
                    ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                    ARRAY_AGG(account_move_line.cost_center_name) AS cost_center_name,
                    ARRAY_AGG(DISTINCT move.invoice_date) AS invoice_date,
                    ARRAY_AGG(DISTINCT move.receipt_date) AS invoice_received_date,
                    ARRAY_AGG(DISTINCT move.date) AS date,
                    ARRAY_AGG(DISTINCT move.name) AS move_name,
                    ARRAY_AGG(DISTINCT move.payment_state) AS payment_state,
                    ARRAY_AGG(DISTINCT move.payment_reference) AS payment_reference,
                    ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS report_date,
                    ARRAY_AGG(DISTINCT %(account_code)s) AS account_name,
                    ARRAY_AGG(DISTINCT %(chart_account_name)s) AS chart_account_name,
                    ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS due_date,
                    ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                    COUNT(account_move_line.id) AS aml_count,
                    ARRAY_AGG(%(account_code)s) AS account_code,
                    %(select_period_query)s

                FROM %(table_references)s

                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_move move ON move.id = account_move_line.move_id
                LEFT JOIN res_partner partner ON partner.id =  account_move_line.partner_id
                LEFT JOIN res_country_state state ON state.id = partner.state_id
                LEFT JOIN res_company company ON company.id =  move.company_id
                LEFT JOIN customer_group ON customer_group.id = partner.customer_group_id
                LEFT JOIN account_payment_term ON account_payment_term.id = move.invoice_payment_term_id
                LEFT JOIN account_payment_method_line ON account_payment_method_line.id = move.preferred_payment_method_line_id
                %(currency_table_join)s

                LEFT JOIN LATERAL (
                    SELECT
                        SUM(part.amount) AS amount,
                        SUM(part.debit_amount_currency) AS debit_amount_currency,
                        part.debit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date_to)s AND part.debit_move_id = account_move_line.id
                    GROUP BY part.debit_move_id
                ) part_debit ON TRUE

                LEFT JOIN LATERAL (
                    SELECT
                        SUM(part.amount) AS amount,
                        SUM(part.credit_amount_currency) AS credit_amount_currency,
                        part.credit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date_to)s AND part.credit_move_id = account_move_line.id
                    GROUP BY part.credit_move_id
                ) part_credit ON TRUE

                JOIN period_table ON
                    (
                        period_table.date_start IS NULL
                        OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) <= DATE(period_table.date_start)
                    )
                    AND
                    (
                        period_table.date_stop IS NULL
                        OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) >= DATE(period_table.date_stop)
                    )

                WHERE %(search_condition)s

                GROUP BY %(groupby_clause)s

                HAVING
                    ROUND(SUM(%(having_debit)s), %(currency_precision)s) != 0
                    OR ROUND(SUM(%(having_credit)s), %(currency_precision)s) != 0

                ORDER BY %(groupby_clause)s

                %(tail_query)s
                """,
                account_code=account_code,
                chart_account_name=chart_account_name,
                period_table=period_table,
                select_from_groupby=select_from_groupby,
                select_period_query=select_period_query,
                multiplicator=multiplicator,
                aging_date_field=aging_date_field,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options),
                date_to=date_to,
                search_condition=query.where_clause,
                groupby_clause=groupby_clause,
                having_debit=report._currency_table_apply_rate(
                    SQL("CASE WHEN account_move_line.balance > 0  THEN account_move_line.balance else 0 END - COALESCE(part_debit.amount, 0)")),
                having_credit=report._currency_table_apply_rate(
                    SQL("CASE WHEN account_move_line.balance < 0  THEN -account_move_line.balance else 0 END - COALESCE(part_credit.amount, 0)")),
                currency_precision=self.env.company.currency_id.decimal_places,
                tail_query=tail_query,
            )

            self._cr.execute(query)
            query_res_lines = self._cr.dictfetchall()

            if not current_groupby:
                return build_result_dict(report, query_res_lines)
            else:
                rslt = []

                all_res_per_grouping_key = {}
                for query_res in query_res_lines:
                    grouping_key = query_res['grouping_key']
                    all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

                for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                    rslt.append((grouping_key, build_result_dict(report, query_res_lines)))

                return rslt
        else:
            report = self.env['account.report'].browse(options['report_id'])
            report._check_groupby_fields(
                (next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

            def minus_days(date_obj, days):
                return fields.Date.to_string(date_obj - relativedelta(days=days))

            aging_date_field = SQL.identifier('invoice_date') if options[
                                                                     'aging_based_on'] == 'base_on_invoice_date' else SQL.identifier(
                'date_maturity')
            date_to = fields.Date.from_string(options['date']['date_to'])
            interval = options['aging_interval']
            periods = [(False, fields.Date.to_string(date_to))]
            # Since we added the first period in the list we have to do one less iteration
            nb_periods = len(
                [column for column in options['columns'] if column['expression_label'].startswith('period')]) - 1
            for i in range(nb_periods):
                if 0 <= i < 3:
                    start_date = minus_days(date_to, (interval * i) + 1)
                    # The last element of the list will have False for the end date
                    end_date = minus_days(date_to, interval * (i + 1)) if i < nb_periods - 1 else False
                    periods.append((start_date, end_date))

                elif i == 3:

                    start_date = minus_days(date_to, (interval * i) + 1)
                    # The last element of the list will have False for the end date
                    end_date = minus_days(date_to,
                                          interval * (i + 1) + (interval * 2)) if i < nb_periods - 1 else False
                    periods.append((start_date, end_date))

                if 5 <= i < 6:
                    start_date = minus_days(date_to, (interval * i) + (interval) + 1)
                    # The last element of the list will have False for the end date
                    # end_date = minus_days(date_to, (interval * 2) * (i + 1)) if i < nb_periods - 1 else False
                    end_date = minus_days(date_to, (interval * 2) * (i + 1))
                    periods.append((start_date, end_date))

                # if i == 6:
                #     start_date = minus_days(date_to, (interval * i * 2))
                #     # The last element of the list will have False for the end date
                #     end_date = False
                #     periods.append((start_date, end_date))
                #
                # elif i == 7:
                #     start_date = minus_days(date_to, (interval * 3))
                #     # The last element of the list will have False for the end date
                #     end_date = False
                #     periods.append((start_date, end_date))

                elif i == 4:
                    start_date = minus_days(date_to, (interval * i *3) + 1)
                    # The last element of the list will have False for the end date
                    end_date = False
                    periods.append((start_date, end_date))

            def build_result_dict(report, query_res_lines):
                rslt = {f'period{i}': 0 for i in range(len(periods))}

                for query_res in query_res_lines:
                    for i in range(len(periods)):
                        period_key = f'period{i}'
                        rslt[period_key] += query_res[period_key]

                if current_groupby == 'id':
                    query_res = query_res_lines[
                        0]  # We're grouping by id, so there is only 1 element in query_res_lines anyway
                    currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(
                        query_res['currency_id']) == 1 else None
                    rslt.update({
                        'invoice_date': query_res['invoice_date'][0] if len(query_res['invoice_date']) == 1 else None,
                        'invoice_received_date': query_res['invoice_received_date'][0] if len(query_res['invoice_received_date']) == 1 else None,
                        'due_date': query_res['due_date'][0] if len(query_res['due_date']) == 1 else None,
                        'amount_currency': query_res['amount_currency'],
                        'currency_id': query_res['currency_id'][0] if len(query_res['currency_id']) == 1 else None,
                        'currency': currency.display_name if currency else None,
                        'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                        'total': None,
                        'has_sublines': query_res['aml_count'] > 0,

                        # Needed by the custom_unfold_all_batch_data_generator, to speed-up unfold_all
                        'partner_id': query_res['partner_id'][0] if query_res['partner_id'] else None,
                    })
                else:
                    rslt.update({
                        'invoice_date': None,
                        'invoice_received_date':None,
                        'due_date': None,
                        'amount_currency': None,
                        'currency_id': None,
                        'currency': None,
                        'account_name': None,
                        'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                        'has_sublines': False,
                    })

                return rslt

            # Build period table
            period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for period in periods))
            params = list(chain.from_iterable(
                (period[0] or None, period[1] or None, i)
                for i, period in enumerate(periods)
            ))
            period_table = SQL(period_table_format, *params)

            # Build query
            query = report._get_report_query(options, 'strict_range',
                                             domain=[('account_id.account_type', '=', internal_type)])
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id',
                                            rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)

            always_present_groupby = SQL("period_table.period_index")
            if current_groupby:
                select_from_groupby = SQL("%s AS grouping_key,", SQL.identifier("account_move_line", current_groupby))
                groupby_clause = SQL("%s, %s", SQL.identifier("account_move_line", current_groupby),
                                     always_present_groupby)
            else:
                select_from_groupby = SQL()
                groupby_clause = always_present_groupby
            multiplicator = -1 if internal_type == 'liability_payable' else 1
            select_period_query = SQL(',').join(
                SQL("""
                            CASE WHEN period_table.period_index = %(period_index)s
                            THEN %(multiplicator)s * SUM(%(balance_select)s)
                            ELSE 0 END AS %(column_name)s
                            """,
                    period_index=i,
                    multiplicator=multiplicator,
                    column_name=SQL.identifier(f"period{i}"),
                    balance_select=report._currency_table_apply_rate(SQL(
                        "account_move_line.balance - COALESCE(part_debit.amount, 0) + COALESCE(part_credit.amount, 0)"
                    )),
                    )
                for i in range(len(periods))
            )

            tail_query = report._get_engine_query_tail(offset, limit)
            query = SQL(
                """
                WITH period_table(date_start, date_stop, period_index) AS (%(period_table)s)

                SELECT
                    %(select_from_groupby)s
                    %(multiplicator)s * (
                        SUM(account_move_line.amount_currency)
                        - COALESCE(SUM(part_debit.debit_amount_currency), 0)
                        + COALESCE(SUM(part_credit.credit_amount_currency), 0)
                    ) AS amount_currency,
                    ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                    ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                    ARRAY_AGG(DISTINCT move.invoice_date) AS invoice_date,
                    ARRAY_AGG(DISTINCT move.receipt_date) AS invoice_received_date,
                    ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS report_date,
                    ARRAY_AGG(DISTINCT %(account_code)s) AS account_name,
                    ARRAY_AGG(DISTINCT COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date)) AS due_date,
                    ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                    COUNT(account_move_line.id) AS aml_count,
                    ARRAY_AGG(%(account_code)s) AS account_code,
                    %(select_period_query)s

                FROM %(table_references)s

                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_move move ON move.id = account_move_line.move_id
                %(currency_table_join)s

                LEFT JOIN LATERAL (
                    SELECT
                        SUM(part.amount) AS amount,
                        SUM(part.debit_amount_currency) AS debit_amount_currency,
                        part.debit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date_to)s AND part.debit_move_id = account_move_line.id
                    GROUP BY part.debit_move_id
                ) part_debit ON TRUE

                LEFT JOIN LATERAL (
                    SELECT
                        SUM(part.amount) AS amount,
                        SUM(part.credit_amount_currency) AS credit_amount_currency,
                        part.credit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date_to)s AND part.credit_move_id = account_move_line.id
                    GROUP BY part.credit_move_id
                ) part_credit ON TRUE

                JOIN period_table ON
                    (
                        period_table.date_start IS NULL
                        OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) <= DATE(period_table.date_start)
                    )
                    AND
                    (
                        period_table.date_stop IS NULL
                        OR COALESCE(account_move_line.%(aging_date_field)s, account_move_line.date) >= DATE(period_table.date_stop)
                    )

                WHERE %(search_condition)s

                GROUP BY %(groupby_clause)s

                HAVING
                    ROUND(SUM(%(having_debit)s), %(currency_precision)s) != 0
                    OR ROUND(SUM(%(having_credit)s), %(currency_precision)s) != 0

                ORDER BY %(groupby_clause)s

                %(tail_query)s
                """,
                account_code=account_code,
                period_table=period_table,
                select_from_groupby=select_from_groupby,
                select_period_query=select_period_query,
                multiplicator=multiplicator,
                aging_date_field=aging_date_field,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(options),
                date_to=date_to,
                search_condition=query.where_clause,
                groupby_clause=groupby_clause,
                having_debit=report._currency_table_apply_rate(
                    SQL("CASE WHEN account_move_line.balance > 0  THEN account_move_line.balance else 0 END - COALESCE(part_debit.amount, 0)")),
                having_credit=report._currency_table_apply_rate(
                    SQL("CASE WHEN account_move_line.balance < 0  THEN -account_move_line.balance else 0 END - COALESCE(part_credit.amount, 0)")),
                currency_precision=self.env.company.currency_id.decimal_places,
                tail_query=tail_query,
            )

            self._cr.execute(query)
            query_res_lines = self._cr.dictfetchall()

            if not current_groupby:
                return build_result_dict(report, query_res_lines)
            else:
                rslt = []

                all_res_per_grouping_key = {}
                for query_res in query_res_lines:
                    grouping_key = query_res['grouping_key']
                    all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

                for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                    rslt.append((grouping_key, build_result_dict(report, query_res_lines)))

                return rslt
            # return super()._aged_partner_report_custom_engine_common(options, internal_type, current_groupby, next_groupby, offset, limit)



class AgedReceivableCustomHandler(models.AbstractModel):
    _inherit = 'account.aged.receivable.report.handler'



    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        # We only optimize the unfold all if the groupby value of the report has not been customized. Else, we'll just run the full computation
        if self.env.ref('gulfco_account_reports.aged_receivable_line').groupby.replace(' ', '') == 'partner_id,id':
            return self._common_custom_unfold_all_batch_data_generator('asset_receivable', report, options, lines_to_expand_by_function)
        return {}
