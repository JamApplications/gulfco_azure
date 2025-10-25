from odoo import fields, models, _, api
from odoo.tools import SQL
from collections import defaultdict
from odoo.exceptions import UserError

class AccountFollowupCustomHandler(models.AbstractModel):
    _name = 'account.soa.report.handler'
    _inherit = 'account.partner.ledger.report.handler'
    _description = 'SOA Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['hide_initial_balance'] = True
        if len(options['partner_ids']) == 1:
            options['ignore_totals_below_sections'] = True
            options['hide_partner_totals'] = True

        if options['report_id'] != previous_options.get('report_id'):
            options['unreconciled'] = True
            # by default, select only the 'sales' journals
            for journal in options['journals']:
                journal['selected'] = journal.get('type') != 'general'  # dividers don't get a type
            # Since we forced the selection of some journal, we need to recompute the filter label
            report._init_options_journals_names(options, previous_options=previous_options)

    def _get_partner_aml_report_lines(self, report, options, partner_line_id, aml_results, progress, offset=0,
                                      level_shift=0):

        def create_status_line(status_name):
            return {
                'id': report._get_generic_line_id(None, None, markup=status_name, parent_line_id=partner_line_id),
                'name': status_name,
                'level': 3 + level_shift,
                'parent_id': partner_line_id,
                'columns': [{} for _col in options['columns']],
                'unfolded': True,
                'is_status_line':True
            }

        def get_aml_lines_with_status_line(status_name, status_line_id, aml_values, treated_results_count, progress):
            lines = []
            next_progress = progress
            has_more = False

            if not status_line_id or offset == 0:
                status_line = create_status_line(status_name)
                lines.append(status_line)
                status_line_id = status_line['id']

            for aml_value in aml_values:
                if self._is_report_limit_reached(report, options, treated_results_count):
                    # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                    has_more = True
                    break

                aml_report_line = self._get_report_line_move_line(options, aml_value, status_line_id, next_progress,
                                                                  level_shift=level_shift + 1)
                lines.append(aml_report_line)
                next_progress = self._init_load_more_progress(options, aml_report_line)
                treated_results_count += 1

            return lines, next_progress, treated_results_count, has_more

        lines = []
        next_progress = progress
        has_more = False
        treated_results_count = 0
        today = fields.Date.today()
        due_line_id, overdue_line_id = self._get_unfolded_partner_status_lines(report, options, partner_line_id)

        overdue_aml_values = list(filter(lambda aml: aml['date_maturity'] < today, aml_results))
        due_aml_values = list(filter(lambda aml: aml['date_maturity'] >= today, aml_results))

        if overdue_aml_values:
            overdue_lines, next_progress, treated_results_count, has_more = get_aml_lines_with_status_line(_('Overdue'),
                                                                                                           overdue_line_id,
                                                                                                           overdue_aml_values,
                                                                                                           treated_results_count,
                                                                                                           next_progress)
            lines.extend(overdue_lines)
            # If we reached the limit just before the due line and have already loaded one extra line, we should skip the due line for now and add a "load more" line
            if self._is_report_limit_reached(report, options, treated_results_count) and due_aml_values:
                has_more = True

        if due_aml_values and not has_more:
            due_lines, next_progress, treated_results_count, has_more = get_aml_lines_with_status_line(_('Due'),
                                                                                                       due_line_id,
                                                                                                       due_aml_values,
                                                                                                       treated_results_count,
                                                                                                       next_progress)
            lines.extend(due_lines)

        return lines, next_progress, treated_results_count, has_more

    def _get_unfolded_partner_status_lines(self, report, options, partner_line_id):
        _dummy1, _dummy2, partner_id = report._parse_line_id(partner_line_id)[-1]
        due_line_id, overdue_line_id = None, None
        for line_id in options['unfolded_lines']:
            res_ids_map = report._get_res_ids_from_line_id(line_id, ['account.report', 'res.partner'])
            if res_ids_map['account.report'] == report.id and res_ids_map['res.partner'] == partner_id:
                markup, _dummy1, _dummy2 = report._parse_line_id(line_id)[-1]
                if markup == 'Due':
                    due_line_id = line_id
                if markup == 'Overdue':
                    overdue_line_id = line_id
        return due_line_id, overdue_line_id

    def _get_order_by_aml_values(self):
        return SQL('account_move_line.date_maturity, %(order_by)s', order_by=super()._get_order_by_aml_values())

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        rslt = {partner_id: [] for partner_id in partner_ids}

        partner_ids_wo_none = [x for x in partner_ids if x]
        directly_linked_aml_partner_clauses = []
        indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IS NOT NULL')
        if None in partner_ids:
            directly_linked_aml_partner_clauses.append(SQL('account_move_line.partner_id IS NULL'))
        if partner_ids_wo_none:
            directly_linked_aml_partner_clauses.append(
                SQL('account_move_line.partner_id IN %s', tuple(partner_ids_wo_none)))
            indirectly_linked_aml_partner_clause = SQL('aml_with_partner.partner_id IN %s', tuple(partner_ids_wo_none))
        directly_linked_aml_partner_clause = SQL('(%s)', SQL(' OR ').join(directly_linked_aml_partner_clauses))

        queries = []
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
        report = self.env.ref('gulfco_account_reports.soa_report')
        # report = self.env.ref('account_reports.partner_ledger_report')
        additional_columns = self._get_additional_column_aml_values()
        order_by = self._get_order_by_aml_values()
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(group_options, 'strict_range')
            account_alias = query.left_join(lhs_alias='account_move_line', lhs_column='account_id',
                                            rhs_table='account_account', rhs_column='id', link='account_id')
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
                    CASE
                        WHEN account_move.amount_residual <= account_move.uncovered_balance THEN account_move.amount_residual
                        ELSE account_move.amount_residual - account_move.uncovered_balance
                    END AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    account_move.ref                                                 AS inv_ref,
                    account_move.invoice_origin                                      AS invoice_origin,
                    account_move.uncovered_balance                                   AS uncovered_balance,
                    %(account_code)s                                                 AS account_code,
                    %(account_name)s                                                 AS account_name,
                    journal.code                                                     AS journal_code,
                    %(journal_name)s                                                 AS journal_name,
                    %(column_group_key)s                                             AS column_group_key,
                    'directly_linked_aml'                                            AS key,
                    0                                                                AS partial_id
                FROM %(table_references)s
                JOIN account_move ON account_move.id = account_move_line.move_id and account_move.move_type in ('out_invoice')
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
                    CASE
                        WHEN account_move.amount_residual <= account_move.uncovered_balance THEN account_move.amount_residual
                        ELSE account_move.amount_residual - account_move.uncovered_balance
                    END AS balance,
                    account_move.name                                                AS move_name,
                    account_move.move_type                                           AS move_type,
                    account_move.ref                                                 AS inv_ref,
                    account_move.invoice_origin                                      AS invoice_origin,
                    account_move.uncovered_balance                                   AS uncovered_balance,
                    %(account_code)s                                                 AS account_code,
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

    def _build_partner_lines(self, report, options, level_shift=0):
        lines = []

        totals_by_column_group = {
            column_group_key: {
                total: 0.0
                for total in ['debit', 'credit', 'amount', 'balance','uncovered_balance']
            }
            for column_group_key in options['column_groups']
        }

        partners_results = self._query_partners(report, options)

        search_filter = options.get('filter_search_bar', '')
        accept_unknown_in_filter = search_filter.lower() in self._get_no_partner_line_label().lower()
        for partner, results in partners_results:
            if options['export_mode'] == 'print' and search_filter and not partner and not accept_unknown_in_filter:
                # When printing and searching for a specific partner, make it so we only show its lines, not the 'Unknown Partner' one, that would be
                # shown in case a misc entry with no partner was reconciled with one of the target partner's entries.
                continue

            partner_values = defaultdict(dict)
            for column_group_key in options['column_groups']:
                partner_sum = results.get(column_group_key, {})

                partner_values[column_group_key]['debit'] = partner_sum.get('debit', 0.0)
                partner_values[column_group_key]['credit'] = partner_sum.get('credit', 0.0)
                partner_values[column_group_key]['amount'] = partner_sum.get('amount', 0.0)
                partner_values[column_group_key]['balance'] = partner_sum.get('balance', 0.0)
                partner_values[column_group_key]['uncovered_balance'] = partner_sum.get('uncovered_balance', 0.0)

                totals_by_column_group[column_group_key]['debit'] += partner_values[column_group_key]['debit']
                totals_by_column_group[column_group_key]['credit'] += partner_values[column_group_key]['credit']
                totals_by_column_group[column_group_key]['amount'] += partner_values[column_group_key]['amount']
                totals_by_column_group[column_group_key]['balance'] += partner_values[column_group_key]['balance']
                totals_by_column_group[column_group_key]['uncovered_balance'] += partner_values[column_group_key]['uncovered_balance']

            lines.append(self._get_report_line_partners(options, partner, partner_values, level_shift=level_shift))

        return lines, totals_by_column_group

    def _query_partners(self, report, options):
        def assign_sum(row):
            fields_to_assign = ['balance', 'debit', 'credit', 'amount','uncovered_balance']
            if any(not company_currency.is_zero(row[field]) for field in fields_to_assign):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))
                for field in fields_to_assign:
                    groupby_partners[row['groupby']][row['column_group_key']][field] += row[field]

        company_currency = self.env.company.currency_id
        query = self._get_query_sums(report, options)
        groupby_partners = {}
        self._cr.execute(query)
        for res in self._cr.dictfetchall():
            assign_sum(res)

        query = self._get_sums_without_partner(options)
        self._cr.execute(query)
        totals = {}
        for total_field in ['debit', 'credit', 'amount', 'balance','uncovered_balance']:
            totals[total_field] = {col_group_key: 0 for col_group_key in options['column_groups']}

        for row in self._cr.dictfetchall():
            totals['debit'][row['column_group_key']] += row['debit']
            totals['credit'][row['column_group_key']] += row['credit']
            totals['amount'][row['column_group_key']] += row['amount']
            totals['balance'][row['column_group_key']] += row['balance']
            totals['uncovered_balance'][row['column_group_key']] += row['uncovered_balance']

            if row['groupby'] not in groupby_partners:
                continue

            assign_sum(row)

        if None in groupby_partners:
            # Debit/credit are inverted for the unknown partner as the computation is made regarding the balance of the known partner
            for column_group_key in options['column_groups']:
                groupby_partners[None][column_group_key]['debit'] += totals['credit'][column_group_key]
                groupby_partners[None][column_group_key]['credit'] += totals['debit'][column_group_key]
                groupby_partners[None][column_group_key]['amount'] += totals['amount'][column_group_key]
                groupby_partners[None][column_group_key]['balance'] -= totals['balance'][column_group_key]
                groupby_partners[None][column_group_key]['uncovered_balance'] += totals['uncovered_balance'][column_group_key]
        if groupby_partners:
            partners = self.env['res.partner'].with_context(active_test=False).search_fetch([('id', 'in', list(groupby_partners.keys()))], ["id", "name", "trust", "company_registry", "vat"])
        else:
            partners = []
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]
        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]

    def _get_query_sums(self, report, options) -> SQL:
        queries = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, 'from_beginning')
            date_from = options['date']['date_from']
            queries.append(SQL(
                """
                (WITH partner_sums AS (
                    SELECT
                        account_move_line.partner_id            AS groupby,
                        %(column_group_key)s                    AS column_group_key,
                        SUM(%(debit_select)s)                   AS debit,
                        SUM(%(credit_select)s)                  AS credit,
                        CASE
                            WHEN account_move.amount_residual <= account_move.uncovered_balance THEN account_move.amount_residual
                            ELSE account_move.amount_residual - account_move.uncovered_balance
                        END AS amount,
                        CASE
                            WHEN account_move.amount_residual <= account_move.uncovered_balance THEN account_move.amount_residual
                            ELSE account_move.amount_residual - account_move.uncovered_balance
                        END AS balance,
                        SUM(account_move.uncovered_balance)       AS uncovered_balance,
                        BOOL_AND(account_move_line.reconciled)  AS all_reconciled,
                        MAX(account_move_line.date)             AS latest_date
                    FROM %(table_references)s
                    JOIN account_move ON account_move.id = account_move_line.move_id 
                    %(currency_table_join)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.partner_id,account_move.amount_residual,account_move.uncovered_balance
                )
                SELECT *
                FROM partner_sums
                WHERE partner_sums.balance != 0
                OR partner_sums.all_reconciled = FALSE
                OR partner_sums.latest_date >= %(date_from)s
                )""",
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_group_options),
                search_condition=query.where_clause,
                date_from=date_from,
            ))

        return SQL(' UNION ALL ').join(queries)

    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        company_currency = self.env.company.currency_id

        partner_data = next(iter(partner_values.values()))
        unfoldable = not company_currency.is_zero(partner_data.get('debit', 0) or partner_data.get('credit', 0))
        column_values = []
        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            col_expr_label = column['expression_label']
            value = None if options.get('hide_partner_totals') else partner_values[column['column_group_key']].get(col_expr_label)
            unfoldable = unfoldable or (col_expr_label in ('debit', 'credit', 'amount','uncovered_balance') and not company_currency.is_zero(value))
            column_values.append(report._build_column_dict(value, column, options=options))


        line_id = report._get_generic_line_id('res.partner', partner.id) if partner else report._get_generic_line_id('res.partner', None, markup='no_partner')

        return {
            'id': line_id,
            'name': partner is not None and (partner.name or '')[:128] or self._get_no_partner_line_label(),
            'columns': column_values,
            'level': 1 + level_shift,
            'trust': partner.trust if partner else None,
            'unfoldable': unfoldable,
            'unfolded': line_id in options['unfolded_lines'] or options['unfold_all'],
            'expand_function': '_report_expand_unfoldable_line_partner_ledger',
        }

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        if aml_query_result['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        columns = []
        report = self.env['account.report'].browse(options['report_id'])
        for column in options['columns']:
            col_expr_label = column['expression_label']

            if col_expr_label not in aml_query_result:
                raise UserError(_("The column '%s' is not available for this report.", col_expr_label))

            col_value = aml_query_result[col_expr_label] if column['column_group_key'] == aml_query_result['column_group_key'] else None

            if col_value is None:
                columns.append(report._build_column_dict(None, None))
            else:
                currency = False
                # if col_expr_label == 'balance':
                #     col_value += init_bal_by_col_group[column['column_group_key']]

                if col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(aml_query_result['currency_id'])

                    if currency == self.env.company.currency_id:
                        col_value = ''

                columns.append(report._build_column_dict(col_value, column, options=options, currency=currency))

        return {
            'id': report._get_generic_line_id('account.move.line', aml_query_result['id'], parent_line_id=partner_line_id, markup=aml_query_result['partial_id']),
            'parent_id': partner_line_id,
            'name': self._format_aml_name(aml_query_result['name'], aml_query_result['invoice_origin'], aml_query_result['move_name']),
            # 'name': self._format_aml_name(aml_query_result['name'], aml_query_result['ref'], aml_query_result['move_name']),
            'columns': columns,
            'caret_options': caret_type,
            'level': 3 + level_shift,
        }

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        return self.env['account.move.line'].with_context(from_soa_report_format=True)._format_aml_name(line_name, move_ref, move_name=move_name)