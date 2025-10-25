# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, osv, _
from odoo.exceptions import UserError
from odoo.tools import format_amount
import io
import xlsxwriter
from datetime import date
from datetime import datetime
from itertools import groupby
import markupsafe
from copy import deepcopy
from collections import defaultdict
import toolz as T
import toolz.curried as TC

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_location_plan = fields.Boolean(string="Location Filter", )
    filter_department_plan = fields.Boolean(string="Department Filter", )
    filter_channel_plan = fields.Boolean(string="Channel Filter", )
    is_payable_report = fields.Boolean(string="Is Payable Report")
    is_receivable_report = fields.Boolean(string="Is Receivable Report")

    def _init_options_buttons(self, options, previous_options):
        super()._init_options_buttons(options, previous_options)
        if self.name in ['Tax Report','VAT Return']:
            options['buttons'].append(
                {
                    'name': _('Vat Details'),
                    'sequence': 10,
                    'action': 'export_file',
                    'action_param': 'export_vat_details_xlsx',
                    'file_export_type':  _('XLSX'),
                    'branch_allowed': True,
                    'always_show': True
                },
            )
        if self.is_payable_report:
            buttons = [d for d in options['buttons'] if d.get('action_param') != 'export_to_pdf']
            options.update({'buttons': buttons})
            # if self == self.env.ref('account_reports.profit_and_loss'):
            options['buttons'].append({'name': _('Print Excel'), 'sequence': 15, 'action': 'export_file',
                                       'action_param': 'export_aging_payable_xlsx', 'file_export_type': _('XLSX'),
                                       'always_show': True})
            options['buttons'].append({'name': _('AP Trial Balance'), 'sequence': 16, 'action': 'export_file',
                                       'action_param': 'export_aging_trail_balance_xlsx', 'file_export_type': _('XLSX'),
                                       'always_show': True})

        if self.is_receivable_report:
            options['buttons'].append({'name': _('AR Aging Report'), 'sequence': 26, 'action': 'export_file',
                                       'action_param': 'export_to_xlsx_ar_aging_report', 'file_export_type': _('XLSX'),
                                       'always_show': True})

        if self == self.env.ref('gulfco_account_reports.soa_report'):
            options['buttons'].append(
                {'name': _('SOA PDF'), 'sequence': 10, 'action': 'export_file', 'action_param': 'soa_export_to_pdf',
                 'file_export_type': _('PDF'), 'branch_allowed': True, 'always_show': True}, )
    @api.model
    def get_custom_aging_sql(self, partner_id, date_to=None):
        date = datetime.today()
        if not partner_id:
            return {'error': 'Partner ID required'}
        sql_query = """WITH period_table(date_start, date_stop, period_index) AS (
                SELECT * FROM (
                    VALUES
                        (NULL::date, %(date_to)s::date, 0),                                          -- Current (Not Due Yet)
                        (%(date_to)s::date - INTERVAL '1 day', %(date_to)s::date - INTERVAL '30 days', 1),   -- <30 Days
                        (%(date_to)s::date - INTERVAL '31 days', %(date_to)s::date - INTERVAL '60 days', 2), -- 31-60
                        (%(date_to)s::date - INTERVAL '61 days', %(date_to)s::date - INTERVAL '90 days', 3), -- 61-90
                        (%(date_to)s::date - INTERVAL '91 days', %(date_to)s::date - INTERVAL '120 days', 4),-- 91-120
                        (%(date_to)s::date - INTERVAL '121 days', NULL::date, 5)                              -- >120 Days
                ) AS t(date_start, date_stop, period_index)
                ),

                aging_data AS (
                    SELECT
                        aml.partner_id,
                        pt.period_index,
                        SUM(
                            aml.amount_currency
                            - COALESCE(part_debit.debit_amount_currency, 0)
                            + COALESCE(part_credit.credit_amount_currency, 0)
                        ) AS amount_currency

                    FROM account_move_line aml
                    JOIN account_account acc ON aml.account_id = acc.id
                    JOIN account_move move ON move.id = aml.move_id

                    LEFT JOIN LATERAL (
                        SELECT
                            SUM(part.amount) AS amount,
                            SUM(part.debit_amount_currency) AS debit_amount_currency
                        FROM account_partial_reconcile part
                        WHERE part.max_date <= %(date_to)s
                          AND part.debit_move_id = aml.id
                    ) part_debit ON TRUE

                    LEFT JOIN LATERAL (
                        SELECT
                            SUM(part.amount) AS amount,
                            SUM(part.credit_amount_currency) AS credit_amount_currency
                        FROM account_partial_reconcile part
                        WHERE part.max_date <= %(date_to)s
                          AND part.credit_move_id = aml.id
                    ) part_credit ON TRUE

                    JOIN period_table pt ON (
                        (pt.date_start IS NULL OR COALESCE(aml.date_maturity, aml.date) <= pt.date_start)
                        AND (pt.date_stop IS NULL OR COALESCE(aml.date_maturity, aml.date) >= pt.date_stop)
                    )

                    WHERE
                        aml.partner_id = %(partner_id)s
                        AND acc.account_type = 'asset_receivable'
                        AND aml.parent_state = 'posted'
                        AND aml.reconciled = FALSE
                        AND aml.date <= %(date_to)s

                    GROUP BY aml.partner_id, pt.period_index
                )

                SELECT
                    %(partner_id)s AS partner_id,
                    COALESCE(SUM(amount_currency) FILTER (WHERE period_index = 0), 0.0) AS "current",
                    COALESCE(SUM(amount_currency) FILTER (WHERE period_index = 1), 0.0) AS "less_30",
                    COALESCE(SUM(amount_currency) FILTER (WHERE period_index = 2), 0.0) AS "30_60",
                    COALESCE(SUM(amount_currency) FILTER (WHERE period_index = 3), 0.0) AS "61_90",
                    COALESCE(SUM(amount_currency) FILTER (WHERE period_index = 4), 0.0) AS "91_120",
                    COALESCE(SUM(amount_currency) FILTER (WHERE period_index = 5), 0.0) AS "120_more"

                FROM aging_data;

                """
        self.env.cr.execute(sql_query, {
            'partner_id': partner_id,
            'date_to': date,
        })
        results = self.env.cr.dictfetchall()
        if results and len(results) > 0:
            return results[0]
        return False

    def soa_export_to_pdf(self, options):
        self.ensure_one()

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        print_options = self.get_options(previous_options={**options, 'export_mode': 'print'})
        if print_options['sections']:
            reports_to_print = self.env['account.report'].browse([section['id'] for section in print_options['sections']])
        else:
            reports_to_print = self

        reports_options = []
        for report in reports_to_print:
            reports_options.append(report.get_options(previous_options={**print_options, 'selected_section_id': report.id}))

        grouped_reports_by_format = groupby(
            zip(reports_to_print, reports_options),
            key=lambda report: len(report[1]['columns']) > 5 or report[1].get('horizontal_split')
        )

        footer = self.env['ir.actions.report']._render_template("account_reports.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=markupsafe.Markup(footer.decode())))

        action_report = self.env['ir.actions.report']
        files_stream = []
        for is_landscape, reports_with_options in grouped_reports_by_format:
            bodies = []

            for report, report_options in reports_with_options:
                partner_lines, totals_by_column_group = self.env[self.custom_handler_model_name]._build_partner_lines(report, options)
                partner_lines = report._regroup_lines_by_name_prefix(options, partner_lines,
                                                             '_report_expand_unfoldable_line_partner_ledger_prefix_group',
                                                             0)
                soa_report_data = []
                partner_ids_list = list((id for (_, id) in map(self._get_model_info_from_id, (line['id'] for line in partner_lines))))
                partner_records = self.env['res.partner'].browse(partner_ids_list)

                date_from = options.get('date').get('date_from')
                date_to = options.get('date').get('date_to')
                all_partners_pdc_payments = self.env['account.payment'].sudo().search([('is_pdc_payment','=',True),('date','<=',date_to),('date','>=',date_from),('partner_id', 'in', partner_ids_list)])
                all_pdc_payments_by_partner = defaultdict(lambda: self.env['account.payment'])
                for payment in all_partners_pdc_payments:
                    all_pdc_payments_by_partner[payment.partner_id.id] |= payment

                for partner_line, partner_record in zip(partner_lines, partner_records):
                    # model,id = self._get_model_info_from_id(partner_line['id'])
                    # partner_record = self.env['res.partner'].browse(id)
                    partner_aml_lines = self._fully_unfold_soa_lines_if_needed([partner_line],options)
                    lines = []
                    outstanding = 0.0
                    all_pdc_payments = all_pdc_payments_by_partner.get(partner_record.id, self.env['account.payment'])
                    applied_pdc_payment = all_pdc_payments.filtered(lambda s:s.invoice_ids or s.reconciled_invoice_ids)
                    unapplied_pdc_payment = all_pdc_payments - applied_pdc_payment
                    applied_pdc_amount = sum(applied_pdc_payment.mapped('amount'))
                    unapplied_pdc_amount = sum(unapplied_pdc_payment.mapped('amount'))
                    total_pdc_amount = applied_pdc_amount + unapplied_pdc_amount
                    aging_data = self.get_custom_aging_sql(partner_record.id,date_to)
                    for partner_aml_line in partner_aml_lines:
                        if not partner_aml_line.get('is_status_line'):
                            columns = partner_aml_line['columns']
                            invoice_date = list(
                                filter(lambda s: s.get('expression_label') == 'invoice_date', columns))
                            due_date = list(
                                filter(lambda s: s.get('expression_label') == 'date_maturity', columns))
                            ref = list(
                                filter(lambda s: s.get('expression_label') == 'inv_ref', columns))
                            debit = list(
                                filter(lambda s: s.get('expression_label') == 'debit', columns))
                            credit = list(
                                filter(lambda s: s.get('expression_label') == 'credit', columns))
                            balance = list(
                                filter(lambda s: s.get('expression_label') == 'balance', columns))
                            uncovered_balance = list(
                                filter(lambda s: s.get('expression_label') == 'uncovered_balance', columns))
                            aml_vals = {
                                'trx_number': partner_aml_line['name'],
                                'trx_date':invoice_date[0].get('no_format') if len(invoice_date)> 0 and invoice_date[0].get('no_format') else '',
                                'due_date':due_date[0].get('no_format') if len(due_date)> 0 and due_date[0].get('no_format') else '',
                                'ref': ref[0].get('no_format') if len(ref) > 0 else '',
                                'debit': debit[0].get('no_format') if len(debit) > 0 else '',
                                'credit': credit[0].get('no_format') if len(credit) > 0 else '',
                                'balance': balance[0].get('no_format') if len(balance) > 0 else '',
                                'uncovered_balance': uncovered_balance[0].get('no_format') if len(uncovered_balance) > 0 else '',
                            }
                            lines.append(aml_vals)
                            if len(debit) > 0 and len(credit) > 0:
                                outstanding += debit[0].get('no_format') - credit[0].get('no_format')
                    total_uncovered_balance = outstanding - applied_pdc_amount
                    vals = {
                        'name': partner_record.name,
                        'customer_account': partner_record.outlet_code,
                        'running_date':date.today(),
                        'as_of_date':date.today(),
                        'po_box':partner_record.po_box,
                        'area': partner_record.customer_type,
                        'arabic_name': partner_record.with_context(lang='ar_001').name,
                        'customer_code':partner_record.customer_code,
                        'phone':partner_record.phone,
                        'lines': lines,
                        'outstanding':outstanding,
                        'applied_pdc_amount':round(applied_pdc_amount,2),
                        'unapplied_pdc_amount':round(unapplied_pdc_amount,2),
                        'total_pdc_amount': round(total_pdc_amount,2),
                        'total_uncovered_balance':round(total_uncovered_balance,2),
                        'aging_data': aging_data
                    }
                    soa_report_data.append(vals)

                batch_size = 500
                for start in range(0, len(soa_report_data), batch_size):
                    batch_data = soa_report_data[start:start + batch_size]
                    body = report.get_soa_html(batch_data,print_options, base_url)
                    bodies = [body]

                    files_stream.append(
                        io.BytesIO(action_report._run_wkhtmltopdf(
                            bodies,
                            footer=footer.decode(),
                            landscape=is_landscape or self._context.get('force_landscape_printing'),
                            specific_paperformat_args={
                                'data-report-margin-top': 10,
                                'data-report-header-spacing': 10,
                                'data-report-margin-bottom': 15,
                            }
                        )
                    ))

        if len(files_stream) > 1:
            result_stream = action_report._merge_pdfs(files_stream)
            result = result_stream.getvalue()
            # Close the different stream
            result_stream.close()
            for file_stream in files_stream:
                file_stream.close()
        elif len(files_stream) > 0:
                result = files_stream[0].read()
                # files_stream[0].close()
        else:
            other_body = report.get_soa_html([], print_options, base_url)
            without_data_filestream = io.BytesIO(action_report._run_wkhtmltopdf(
                [other_body],
                footer=footer.decode(),
                landscape=is_landscape or self._context.get('force_landscape_printing'),
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-header-spacing': 10,
                    'data-report-margin-bottom': 15,
                }))
            result = without_data_filestream.read()

        return {
            'file_name': self.get_default_report_filename(options, 'pdf'),
            'file_content': result,
            'file_type': 'pdf',
        }

    def _fully_unfold_soa_lines_if_needed(self, lines, options):
        def line_need_expansion(line_dict):
            return line_dict.get('unfolded') and line_dict.get('expand_function')

        custom_unfold_all_batch_data = None

        # If it's possible to batch unfold and we're unfolding all lines, compute the batch, so that individual expansions are more efficient
        if options['unfold_all'] and self.custom_handler_model_id:
            lines_to_expand_by_function = {}
            for line_dict in lines:
                if line_need_expansion(line_dict):
                    lines_to_expand_by_function.setdefault(line_dict['expand_function'], []).append(line_dict)

            custom_unfold_all_batch_data = self.env[self.custom_handler_model_name]._custom_unfold_all_batch_data_generator(self, options, lines_to_expand_by_function)

        soa_aml_lines = []
        line_dict = lines[0]
        if line_need_expansion(line_dict):
            groupby = line_dict.get('groupby')
            progress = line_dict.get('progress')
            to_insert = self._expand_unfoldable_line(
                line_dict['expand_function'], line_dict['id'], groupby, options, progress, 0,
                line_dict.get('horizontal_split_side'),
                unfold_all_batch_data=custom_unfold_all_batch_data,
            )
            soa_aml_lines = to_insert
        return soa_aml_lines


    def get_soa_html(self,soa_report_data,print_options,base_url):
        render_values = {
            'soa_report_data':soa_report_data,
            'print_options': print_options,
            'base_url': base_url,
        }
        html = self.env['ir.qweb']._render('gulfco_account_reports.report_customer_statement_pdf', render_values)
        return html

    def export_to_xlsx_ar_aging_report(self, options, response=None, **kwargs):
        report = self.env['account.report'].browse(options['report_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': True,
        })
        worksheet = workbook.add_worksheet("AR Aging Report")
        report_info_format = workbook.add_format({
            "bold": True, "align": "left", "valign": "vcenter", "font_size": 16,
        })
        worksheet.set_row(0, 30)
        header_format = workbook.add_format({"bold": True, "border": 1, 'text_wrap': True, })
        other_format = workbook.add_format({"bold": True})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        headers = [
            "Customer Name", "Customer Number", "Customer Class", "Customer Category",
            "Branch", "Payment Term", "Payment Method", " Credit Limit", "Outstanding",
            "Uncovered", "Current", "B1_30", "B31_60", "B61_90", "B91_180", "B181_360",
            "B_Greater_360",  "Advance Payment", "Unapplied Payment","code","account"
        ]
        row = 0
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)

        data = self.env['account.aged.partner.balance.report.handler']._report_custom_engine_aged_receivable(
            expressions=None, options=options, date_scope=None, current_groupby='id', next_groupby=None,
            offset=0, limit=None)

        sum_fields = ['amount_currency'] + [f'period{i}' for i in range(7)]
        # Grouping dictionary
        partner_data = {}

        for _, record in data:
            partner_id = record['partner_id']

            if partner_id not in partner_data:
                # First entry: clone the structure
                partner_data[partner_id] = deepcopy(record)
            else:
                # Sum all period fields and amount_currency
                for field in sum_fields:
                    partner_data[partner_id][field] += record.get(field, 0.0)

        # Final output: single record per partner
        aggregated_data = list(partner_data.values())

        row += 1
        for record in aggregated_data:
            if len(record) > 1:
                # line = record[1]
                line = record
                if 'partner_id' in line and line.get('partner_id'):

                    partner_id = self.env['res.partner'].search([('id', '=', line.get('partner_id'))])

                    credit_limit = partner_id.credit_limit
                    payment_state = ''

                    invoices = self.env['account.move'].search([
                        ('partner_id', '=', partner_id.id),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted'),
                        ('payment_state', '!=', 'paid'),
                    ])
                    uncovered_amount = sum(invoices.filtered(lambda move: move.status_in_payment in ('in_payment')).mapped('amount_residual'))

                    # Sum up the residuals (amount still due)
                    outstanding_amount = sum(invoices.mapped('amount_residual')) or 0
                    domain = [('partner_id', '=', partner_id.id),
                              ('state', 'in', ['in_process','paid']),
                              ('advance_sale_purchase', 'in', ['purchase', 'sale'])]


                    payment =  self.env['account.payment'].search(domain)
                    advance_payment =sum(payment.mapped('amount'))
                    unapplied_payment =sum(payment.filtered(lambda pay: not pay.reconciled_invoice_ids).mapped('amount'))

                    chart_account_name = ''
                    if line.get('account_name') and line.get('chart_account_name'):
                        chart_account_name = line.get('account_name') + ' ' + line.get('chart_account_name')
                    if line.get('invoice_date'):
                        invoice_date = line.get('invoice_date').strftime("%Y-%m-%d")
                    if line.get('date'):
                        accounting_date = line.get('date').strftime("%Y-%m-%d")
                    if line.get('due_date'):
                        due_date = line.get('due_date').strftime("%Y-%m-%d")
                    if line.get('payment_state'):
                        payment_state = dict(self.env['account.move']._fields['payment_state'].selection).get(
                            line.get('payment_state'))
                    worksheet.write(row, 0, line.get('partner_name'))
                    worksheet.write(row, 1, line.get('partner_code'))
                    worksheet.write(row, 2, line.get('customer_class'))
                    worksheet.write(row, 3, line.get('customer_category'))
                    worksheet.write(row, 4, line.get('partner_state'))
                    # worksheet.write(row, 5, line.get('payment_term'))
                    worksheet.write(row, 5, partner_id.property_payment_term_id.name if partner_id.property_payment_term_id else None)
                    # worksheet.write(row, 6, line.get('payment_method'))
                    worksheet.write(row, 6, partner_id.property_inbound_payment_method_line_id.name if partner_id.property_inbound_payment_method_line_id else None)
                    # worksheet.write(row, 7, line.get('customer_credit_limit'))
                    worksheet.write(row, 7, credit_limit or None)
                    worksheet.write(row, 8, outstanding_amount, number_format)
                    # worksheet.write(row, 8, line.get('outstanding'))
                    worksheet.write(row, 9, uncovered_amount, number_format)
                    worksheet.write(row, 10, line.get('period0'), number_format)
                    worksheet.write(row, 11, line.get('period1'), number_format)
                    worksheet.write(row, 12, line.get('period2'), number_format)
                    worksheet.write(row, 13, line.get('period3'), number_format)
                    worksheet.write(row, 14, line.get('period4'), number_format)
                    worksheet.write(row, 15, line.get('period6'), number_format)
                    worksheet.write(row, 16, line.get('period5'), number_format)
                    worksheet.write(row, 17, advance_payment, number_format)
                    worksheet.write(row, 18, unapplied_payment, number_format)
                    worksheet.write(row, 19, line.get('account_name') or '')
                    worksheet.write(row, 20, chart_account_name)
                    
                    row += 1
        worksheet.set_column(0, 1, 30)
        worksheet.set_column(2, 6, 15)
        worksheet.set_column(7, 25, 15)
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        file_name = 'AR_Aging_receivable.xlsx'
        return {
            'file_name': file_name,
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def export_aging_trail_balance_xlsx(self,options, response=None):
        return self.with_context(from_aging_tb=True).export_aging_payable_xlsx(options,response)

    def export_aging_payable_xlsx(self, options, response=None):
        report = self.env['account.report'].browse(options['report_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': True,
        })
        if self.env.context.get('from_aging_tb'):
            worksheet = workbook.add_worksheet("Aging Trail Balance")
        else:
            worksheet = workbook.add_worksheet("Aging Payable")
        report_info_format = workbook.add_format({
            "bold": True, "align": "left", "valign": "vcenter", "font_size": 16,
        })
        worksheet.set_row(0, 30)
        header_format = workbook.add_format({"bold": True, "border": 1, 'text_wrap': True, })
        other_format = workbook.add_format({"bold": True})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        if self.env.context.get('from_aging_tb'):
            headers = [
                "Vendor Name","Division Name", "Division Code", "Vendor Type",
                "Vendor Number", "Invoice Type", "Invoice Number", "Voucher Number","Invoice Received Date", "Invoice Date",
                "GL Date", "Due Date", "Days Late", "Amount Due Original","Currency", "Rate", "Local Currency Amount",
                "Remaining Original","Remaining Balance (AED)","Payment Status","Payment Terms","Payment Method", "Balancing Segment Account", "Natural Account", "Current",
                "1-30 Days", "31-60 Days", "61-90 Days", "91-180 Days", "181-360", "Over 360+"
            ]
        else:
            headers = [
                "Vendor Name", "Division Name", "Division Code", "Vendor Type",
                "Vendor Number", "Invoice Type", "Invoice Number", "Voucher Number","Invoice Received Date", "Invoice Date",
                "GL Date", "Due Date", "Days Late", "Amount Due Original","Currency", "Rate", "Local Currency Amount",
                "Remaining Original","Remaining Balance (AED)","Payment Status","Payment Terms","Payment Method","Balancing Segment Account", "Natural Account", "Current",
                "1-30 Days", "31-60 Days","61-90 Days", "91-180 Days","181-360", "Over 360+"
            ]
        row = 0
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)
        data = self.env['account.aged.partner.balance.report.handler']._aged_partner_report_custom_engine_common(
            options=options, internal_type='liability_payable', current_groupby='id', next_groupby=None, offset=None,
            limit=None)
        # data = []
        row += 1
        for record in data:
            if len(record) > 1:
                line = record[1]
                if 'partner_id' in line and line.get('partner_id'):
                    rate = 1
                    if line.get('currency_rate'):
                        rate = line.get('currency_rate')
                    currency_name = ''
                    invoice_date = ''
                    invoice_received_date = ''
                    accounting_date = ''
                    due_date = ''
                    payment_state = ''
                    chart_account_name = ''
                    payment_method_name = ''
                    payment_term_name = ''
                    if line.get('currency_id'):
                        currency_name = self.env['res.currency'].browse(line.get('currency_id')).name
                    if line.get('account_name') and line.get('chart_account_name'):
                        chart_account_name = line.get('account_name') + ' ' + line.get('chart_account_name')
                    if line.get('invoice_date'):
                        invoice_date = line.get('invoice_date').strftime("%Y-%m-%d")
                    if line.get('invoice_received_date'):
                        invoice_received_date = line.get('invoice_received_date').strftime("%Y-%m-%d")
                    if line.get('date'):
                        accounting_date = line.get('date').strftime("%Y-%m-%d")
                    if line.get('due_date'):
                        due_date = line.get('due_date').strftime("%Y-%m-%d")
                    if line.get('payment_state'):
                        payment_state = dict(self.env['account.move']._fields['payment_state'].selection).get(line.get('payment_state'))
                    if line.get('payment_term_name') and len(line.get('payment_term_name')) > 0:
                        if line.get('payment_term_name')[0] is not None and isinstance(line.get('payment_term_name')[0],str):
                            payment_term_name = line.get('payment_term_name')[0]
                    if line.get('payment_method_name') and len(line.get('payment_method_name')) > 0:
                        if line.get('payment_method_name')[0] is not None and isinstance(line.get('payment_method_name')[0],str):
                            payment_method_name = line.get('payment_method_name')[0]
                    worksheet.write(row, 0, line.get('partner_name'))
                    worksheet.write(row, 1, line.get('division_name'))
                    worksheet.write(row, 2, line.get('division_code'))
                    worksheet.write(row, 3, line.get('supplier_type'))
                    worksheet.write(row, 4, line.get('vendor_number'))
                    worksheet.write(row, 5, line.get('journal_name'))
                    worksheet.write(row, 6, line.get('move_ref'))
                    worksheet.write(row, 7, line.get('move_name'))
                    worksheet.write(row, 8, invoice_date,date_format)
                    worksheet.write(row, 9, invoice_received_date,date_format)
                    worksheet.write(row, 10, accounting_date,date_format)
                    worksheet.write(row, 11, due_date,date_format)
                    days_late = ''
                    if line.get('due_date'):
                        day =  line.get('due_date') - date.today()
                        days = day.days
                        if days > 0:
                            days_late = ''
                        elif days < 0:
                            days_late = str(abs(day.days)) + ' Days'
                        else:
                            days_late = '0 Days'
                    worksheet.write(row, 12, days_late)
                    worksheet.write(row, 13, line.get('amount_currency') or '',number_format)
                    worksheet.write(row,14,currency_name)
                    worksheet.write(row, 15, line.get('currency_rate') or '',number_format)
                    worksheet.write(row, 16, round(line.get('local_balance'),2))
                    worksheet.write(row, 17, line.get('amount_currency') or '',number_format)
                    worksheet.write(row, 18, round(line.get('amount_currency')/rate,2) or '')
                    worksheet.write(row, 19, payment_state)
                    worksheet.write(row, 20, payment_term_name or '')
                    worksheet.write(row, 21, payment_method_name or '')
                    worksheet.write(row, 22, line.get('account_name') or '')
                    worksheet.write(row, 23, chart_account_name)
                    worksheet.write(row, 24, line.get('period0'), number_format)
                    worksheet.write(row, 25,line.get('period1'),number_format)
                    worksheet.write(row, 26, line.get('period2'),number_format)
                    worksheet.write(row, 27, line.get('period3'),number_format)
                    worksheet.write(row, 28, line.get('period4'),number_format)
                    worksheet.write(row, 29, line.get('period5'),number_format)
                    worksheet.write(row, 30, line.get('period6'), number_format)
                    row += 1
        worksheet.set_column(0, 1, 30)
        worksheet.set_column(2, 6, 15)
        worksheet.set_column(7, 25, 15)
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        file_name= 'Aging_payable.xlsx'
        if self.env.context.get('from_aging_tb'):
            file_name = 'Aging_trial_balance.xlsx'
        return {
            'file_name': file_name,
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    # =================================
    # Analytic Accounting Plan filter
    # =======================================

    def _init_options_location_plan(self, options, previous_options):
        options['location_plan'] = []
        if not self.filter_location_plan:
            return

        # ir_filters = self.env['ir.filters'].search([('model_id', '=', 'account.analytic.plan')])
        plan_id = self.env['account.analytic.plan'].search([('name', '=', 'Locations')])
        analytic_account_filters = self.env['account.analytic.account'].search([('plan_id', 'in', plan_id.ids)])
        if not analytic_account_filters:
            return

        location_plan = [{'id': x.id, 'name': x.name, 'selected': False} for x in analytic_account_filters]
        previous_options_location_plan = previous_options.get('location_plan', [])
        previous_options_filters_map = {filter_item['id']: filter_item for filter_item in
                                        previous_options_location_plan}

        for filter_item in location_plan:
            if filter_item['id'] in previous_options_filters_map:
                filter_item['selected'] = previous_options_filters_map[filter_item['id']]['selected']

        options['location_plan'] = location_plan

    def _init_options_department_plan(self, options, previous_options):
        options['department_plan'] = []
        if not self.filter_department_plan:
            return

        # ir_filters = self.env['ir.filters'].search([('model_id', '=', 'account.analytic.plan')])
        plan_id = self.env['account.analytic.plan'].search([('name', '=', 'Departments')])
        analytic_account_filters = self.env['account.analytic.account'].search([('plan_id', 'in', plan_id.ids)])
        if not analytic_account_filters:
            return

        department_plan = [{'id': x.id, 'name': x.name, 'selected': False} for x in analytic_account_filters]
        previous_options_department_plan = previous_options.get('department_plan', [])
        previous_options_filters_map = {filter_item['id']: filter_item for filter_item in
                                        previous_options_department_plan}

        for filter_item in department_plan:
            if filter_item['id'] in previous_options_filters_map:
                filter_item['selected'] = previous_options_filters_map[filter_item['id']]['selected']

        options['department_plan'] = department_plan

    def _init_options_channel_plan(self, options, previous_options):
        options['channel_plan'] = []
        if not self.filter_channel_plan:
            return

        # ir_filters = self.env['ir.filters'].search([('model_id', '=', 'account.analytic.plan')])
        plan_id = self.env['account.analytic.plan'].search([('name', '=', 'Channels')])
        analytic_account_filters = self.env['account.analytic.account'].search([('plan_id', 'in', plan_id.ids)])
        if not analytic_account_filters:
            return

        channel_plan = [{'id': x.id, 'name': x.name, 'selected': False} for x in analytic_account_filters]
        previous_options_channel_plan = previous_options.get('channel_plan', [])
        previous_options_filters_map = {filter_item['id']: filter_item for filter_item in
                                        previous_options_channel_plan}

        for filter_item in channel_plan:
            if filter_item['id'] in previous_options_filters_map:
                filter_item['selected'] = previous_options_filters_map[filter_item['id']]['selected']

        options['channel_plan'] = channel_plan

    @api.model
    def _get_options_location_plan(self, options):
        selected_filters_ids = [
            filter_item['id']
            for filter_item in options.get('location_plan', [])
            if filter_item['selected']
        ]
        if not selected_filters_ids:
            return []

        # selected_ir_filters = self.env['ir.filters'].browse(selected_filters_ids)
        # return osv.expression.OR([filter_record._get_eval_domain() for filter_record in selected_ir_filters])
        selected_ir_filters = self.env['account.analytic.account'].browse(selected_filters_ids)
        # return osv.expression.OR([('id', 'in', selected_ir_filters.ids)])
        # return osv.expression.AND([('id', 'in', selected_ir_filters.ids)])
        return [('distribution_analytic_account_ids', 'in', selected_ir_filters.ids)]

    @api.model
    def _get_options_department_plan(self, options):
        selected_filters_ids = [
            filter_item['id']
            for filter_item in options.get('department_plan', [])
            if filter_item['selected']
        ]
        if not selected_filters_ids:
            return []

        # selected_ir_filters = self.env['ir.filters'].browse(selected_filters_ids)
        # return osv.expression.OR([filter_record._get_eval_domain() for filter_record in selected_ir_filters])
        selected_ir_filters = self.env['account.analytic.account'].browse(selected_filters_ids)
        # return osv.expression.AND([('id', 'in', selected_ir_filters.ids)])
        # return selected_ir_filters
        return [('distribution_analytic_account_ids', 'in', selected_ir_filters.ids)]

    @api.model
    def _get_options_channel_plan(self, options):
        selected_filters_ids = [
            filter_item['id']
            for filter_item in options.get('channel_plan', [])
            if filter_item['selected']
        ]
        if not selected_filters_ids:
            return []

        # selected_ir_filters = self.env['ir.filters'].browse(selected_filters_ids)
        # return osv.expression.OR([filter_record._get_eval_domain() for filter_record in selected_ir_filters])
        selected_ir_filters = self.env['account.analytic.account'].browse(selected_filters_ids)
        # return osv.expression.OR([('id', 'in', selected_ir_filters.ids)])
        return [('distribution_analytic_account_ids', 'in', selected_ir_filters.ids)]
        # return osv.expression.AND([('id', 'in', selected_ir_filters.ids)])
        # return selected_ir_filters

    def _get_options_domain(self, options, date_scope):
        domain_list = []
        domain = super()._get_options_domain(options, date_scope)
        if options.get('location_plan') or 'location_plan' in options:
            domain_list += self._get_options_location_plan(options)
            # domain_list.append(self._get_options_location_plan(options))
        if options.get('department_plan') or 'department_plan' in options:
            domain_list += self._get_options_department_plan(options)
            # domain_list.append(self._get_options_department_plan(options))
        if options.get('channel_plan') or 'channel_plan' in options:
            domain_list += self._get_options_channel_plan(options)
            # domain_list.append(self._get_options_channel_plan(options))
        if self == self.env.ref('gulfco_account_reports.soa_report'):
            domain += [('move_id.move_type','in',['out_invoice'])]
        return domain + domain_list

    def export_vat_details_xlsx(self, options, response=None):
        
        def _get_sign(move_type):
            """Return +1 or -1 depending on move type"""
            if move_type in ("in_invoice", "out_invoice"):
                return 1
            elif move_type in ("in_refund", "out_refund"):
                return -1
            return 1

        def _fmt(val, exchange_rate=0, sign=1):
            """Format with sign, commas, decimals"""
            # aed_currency = self.env.ref("base.AED")
            if val is None:
                return ""
            if exchange_rate > 0:
                val *= exchange_rate
            return sign * abs(float(val))
            # return "{:,.2f}".format(sign * abs(float(val)))
            # val = sign * abs(float(val))
            # return format_amount(self.env, val, aed_currency)

        report = self.env['account.report'].browse(options['report_id'])
        report_period = options.get('date', {}).get('string', '')
        date_from = options.get('date', {})['date_from']
        date_to = options.get('date', {})['date_to']
        vat_details_query = """
        WITH tax_grouped_lines AS (
            SELECT 
                aml.move_id,
                atx.id as tax_id,
                atx.vat_code,
                SUM(aml.price_subtotal) as tax_group_subtotal
            FROM account_move_line aml
            LEFT JOIN account_move_line_account_tax_rel amltr ON amltr.account_move_line_id = aml.id
            LEFT JOIN account_tax atx ON atx.id = amltr.account_tax_id
            WHERE aml.parent_state = 'posted' 
                AND aml.date BETWEEN %(date_from)s AND %(date_to)s
            GROUP BY aml.move_id, atx.id, atx.vat_code
        )
        SELECT
            AM.NAME AS DOCUMENT_NO,
            AM.MOVE_TYPE,
            TO_CHAR(AM.DATE, 'YYYY-MM-DD') AS DOC_DATE,
            TO_CHAR(AM.INVOICE_DATE_DUE, 'YYYY-MM-DD') AS DUE_DATE,
            TO_CHAR(AM.INVOICE_DATE, 'YYYY-MM-DD') AS INVOICE_DATE,
            TO_CHAR(AM.RECEIPT_DATE, 'YYYY-MM-DD') AS INVOICE_RECEIVING_DATE,
            AM.BRANCH AS BRANCH,
            AM.REF AS MOVE_REF,
            AM.REMARK_INVOICE AS clear_description,
            AM.CUSTOM_AUTHORITY AS CUSTOM_AUTHORITY,
            CASE WHEN AM.IS_EXCHANGE THEN 1/AM.RATE ELSE 1/AM.INVOICE_CURRENCY_RATE END AS "Exchange Rate",
            AM.BOE_NUMBER AS BOE_NUMBER,
            TO_CHAR(AM.DATE, 'YYYY') AS YEAR,
            AML.NAME AS LINE_NAME,
            RP.NAME AS PARTNER_NAME,
            RP.CUSTOMER_CODE as CUSTOMER_ACCOUNT,
            RP.VENDOR_CODE as VENDOR_ACCOUNT,
            RP.VAT_TRN AS PARTNER_TRN,
            RP.CONTACT_ADDRESS_COMPLETE AS PARTNER_ADDRESS,
            AM.ASS_VALUE AS ASS_VALUE,
            -- Updated PRICE_SUBTOTAL: Sum of all lines with same tax for this move
            COALESCE(TGL.tax_group_subtotal, 0) AS PRICE_SUBTOTAL,
            SUM(AM.AMOUNT_UNTAXED) OVER (PARTITION BY AM.ID, AA.VAT_DETAIL_TYPE) AS BASE_AMOUNT,
            AML.CREDIT - AML.DEBIT AS VAT_AMOUNT,
            AM.AMOUNT_TOTAL AS PRICE_TOTAL,
            %(report_period)s AS REPORT_PERIOD,
            AJ.NAME -> 'en_US' AS TYPE,
            RS.NAME AS EMIRATES,
            RU.LOGIN AS ENTERED_BY,
            ATX.VAT_CODE AS VAT_CODE,
            AA.CODE_STORE -> '1' AS GL_NUMBER,
            AA.NAME -> 'en_US' AS GL_NAME,
            AA.VAT_DETAIL_TYPE AS VAT_DETAIL_TYPE,
            PT.ITEM_TYPE AS "Nature of activity",
            RC.NAME AS CURRENCY,
            RCT.NAME -> 'en_US' AS COUNTRY
        FROM ACCOUNT_MOVE_LINE AS AML
        LEFT JOIN ACCOUNT_TAX_REPARTITION_LINE AS ATRL ON ATRL.ID = AML.TAX_REPARTITION_LINE_ID
        LEFT JOIN ACCOUNT_MOVE AS AM ON AM.ID = AML.MOVE_ID
        LEFT JOIN ACCOUNT_ACCOUNT AS AA ON AA.ID = AML.ACCOUNT_ID
        LEFT JOIN ACCOUNT_JOURNAL AS AJ ON AJ.ID = AM.JOURNAL_ID
        LEFT JOIN ACCOUNT_TAX AS ATX ON ATX.ID = ATRL.TAX_ID
        LEFT JOIN RES_PARTNER AS RP ON AM.PARTNER_ID = RP.ID
        LEFT JOIN RES_USERS AS RU ON RU.ID = AM.CREATE_UID
        LEFT JOIN RES_PARTNER AS SALES_PERSON_PARTNER ON SALES_PERSON_PARTNER.ID = AM.ASSIGN_TO
        LEFT JOIN RES_COUNTRY_STATE AS RS ON RS.ID = SALES_PERSON_PARTNER.STATE_ID
        LEFT JOIN RES_CURRENCY AS RC ON RC.ID = AML.CURRENCY_ID
        LEFT JOIN RES_COUNTRY AS RCT ON RCT.ID = RP.COUNTRY_ID
        LEFT JOIN PRODUCT_PRODUCT AS PP ON PP.ID = AML.PRODUCT_ID
        LEFT JOIN PRODUCT_TEMPLATE AS PT ON PP.PRODUCT_TMPL_ID = PT.ID
        -- Join with the tax-grouped subtotals
        LEFT JOIN tax_grouped_lines TGL ON TGL.move_id = AM.ID AND TGL.tax_id = ATX.ID
        WHERE AML.PARENT_STATE = 'posted'
        AND AML.DATE BETWEEN %(date_from)s AND %(date_to)s
        AND AM.MOVE_TYPE IN ('in_invoice','in_refund','out_invoice','out_refund')
        AND AML.ID NOT IN (SELECT ACCOUNT_MOVE_LINE_ID FROM ACCOUNT_MOVE_LINE_ACCOUNT_TAX_REL)
		    AND AML.ID IN (SELECT ACCOUNT_MOVE_LINE_ID FROM ACCOUNT_ACCOUNT_TAG_ACCOUNT_MOVE_LINE_REL)
        """
        self.env.cr.execute(vat_details_query,
         {
            # 'account_move_ids': tuple(account_move_lines_ids),
            'report_period': report_period ,
            'date_from':date_from,
            'date_to':date_to
         }
         )
        data = self.env.cr.dictfetchall()
        for line in data:
            sign = _get_sign(line['move_type'])
            # currency = line['currency'] or ""
            # apply to all numeric amounts
            exchange_rate = line['Exchange Rate']
            line['base_amount'] = _fmt(line['base_amount'], exchange_rate, sign)
            line['price_subtotal'] = _fmt(line['price_subtotal'], exchange_rate, sign)
            line['ass_value'] = _fmt(line['ass_value'], 0, sign)
            line['vat_amount'] = _fmt(line['vat_amount'], 0, sign)
            line['price_total'] = _fmt(line['price_total'], exchange_rate, sign)

        grouped_by_move_type = T.groupby('vat_detail_type',data)
        vat_output_rows = T.pipe(
            grouped_by_move_type.get('output',[]),
            TC.map(
                lambda line:[
                    line['document_no'],line['doc_date'],line['report_period'],
                    line['branch'],line['emirates'],line['year'],line['partner_name'],
                    line['partner_trn'],line['partner_address'],line['type'],
                    line['customer_account'],line['entered_by'],line['base_amount'],line['price_subtotal'],
                    line['ass_value'],line['vat_amount'],line['line_name'],line['price_total'],
                    line['vat_code'],line['move_ref'],line['gl_number'],line['gl_name'],
                    line['Nature of activity'],line['currency'],line['Exchange Rate'],
                    line['country'],

                ]
            ),
            list
        )
        vat_input_rows = T.pipe(
            grouped_by_move_type.get('input',[]),
            TC.map(
                lambda line:[
                    line['document_no'],line['doc_date'],line['due_date'],
                    line['report_period'],line['branch'],line['year'],line['type'],
                    line['vendor_account'],line['entered_by'],line['base_amount'],line['price_subtotal'],
                    line['ass_value'],line['vat_amount'],line['line_name'],line['vat_code'],
                    line['invoice_date'],line['invoice_receiving_date'],line['partner_name'],
                    line['move_ref'],line['clear_description'],line['partner_trn'],
                    line['partner_address'], line['currency'],line['Exchange Rate'],
                    line['gl_number'],line['gl_name'],line['custom_authority'],line['boe_number']
                ]
            ),
            list
        )
        vat_output_columns_headers = [
            "Document","Doc Date","Reporting Period",
            "Branch","Emirates","Year",
            "Customer Name","Customer TRN","Customer Address",
            "Type","Account","Enter by",
            "Base Amount","Base Distribution","RCM - Ass.value","VAT Amount","Line Name",
            "Total value","VAT Code","Clear Description",
            "GL Number","GL Name","Nature of activity",
            "Currency","Exchange Rate","Country (Based on Customer)",
        ]
        # # =================================================================
        vat_input_columns_headers = [
            "Document No", "Doc Date", "Due Date", "Reporting Period", "Branch", "Year", "Type", "Account",
            "Enter by", "Goods Invoice","Base Distribution", "Ass.Value", "VAT Invoice","Line Name","VAT Code", "Invoice date",
            "Invoice Receiving Date", "Supplier Name", "Supplier Invoice No", "Clear Descriptions",
            "Supplier TRN", "Supplier Address", "Curency", "Exchange Rate", "GL Number", "GL Name",
            "Custom Authority", "BOE No"
        ]
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            "constant_memory": True,     # stream rows, low memory
            "in_memory": False,           # write zip to disk, faster for big files
            "strings_to_formulas": False, # skip "=SUM(...)" detection
            "strings_to_urls": False,     # skip URL regex on every string
            "use_zip64": True,            # allow very large files
        })
        header_format = workbook.add_format({"bold": True, "border": 1, 'text_wrap': False, })
        number_format = workbook.add_format({'num_format': '#,##0.00'})  # comma + 2 decimals

        # ===============================================================
        output_worksheet = workbook.add_worksheet("Output")
        output_worksheet.write_row(0, 0, vat_output_columns_headers, header_format)

        for row_index, row in enumerate(vat_output_rows, start=1):
            for col_index, value in enumerate(row):
                # Check if value is numeric (int/float)
                if isinstance(value, (int, float)):
                    output_worksheet.write(row_index, col_index, value, number_format)
                else:
                    output_worksheet.write(row_index, col_index, value)

        # ===============================================================
        input_worksheet = workbook.add_worksheet("Input")
        input_worksheet.write_row(0, 0, vat_input_columns_headers, header_format)

        for row_index, row in enumerate(vat_input_rows, start=1):
            for col_index, value in enumerate(row):
                if isinstance(value, (int, float)):
                    input_worksheet.write(row_index, col_index, value, number_format)
                else:
                    input_worksheet.write(row_index, col_index, value)
        # # ===============================================================
        # output_worksheet = workbook.add_worksheet("Output")
        # output_worksheet.write_row(0,0,vat_output_columns_headers,header_format)
        # for row_index, row in enumerate(vat_output_rows,start=1):
        #     output_worksheet.write_row(row_index,0,row)
        # # ===============================================================
        # input_worksheet = workbook.add_worksheet("Input")
        # input_worksheet.write_row(0,0,vat_input_columns_headers,header_format)
        # for row_index, row in enumerate(vat_input_rows,start=1):
        #     input_worksheet.write_row(row_index,0,row)
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return {
            'file_name': "Vat_Details_Report",
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def _report_custom_engine_compute_ass_value_base_three(self, *args, **kwargs):
        expression, options, strict_range, currency_table, financial_report = args
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        country_id = expression.report_line_id.report_id.country_id

        formula = '3. Supplies subject to reverse charge provisions (Base)'
        tags = self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
        # formula = '11. Supplies subject to the reverse charge provisions (Base)'
        # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

        domain = [
            ('move_id.move_type', '=', 'in_invoice'),  # Vendor Bill
            ('ass_value', '>', 0),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
            ('tax_tag_ids', 'in', tags.ids),
            ('move_id.state', '=', 'posted')
        ]

        move_lines = self.env['account.move.line'].search(domain)
        total = 0
        if move_lines:
            total = sum(map(abs, move_lines.mapped('ass_value')))
            # total = sum(move_lines.mapped('ass_value'))

        return {
            'balance': total,
        }

    # def _report_custom_engine_compute_ass_value_base_seven(self, *args, **kwargs):
    #     expression, options, strict_range, currency_table, financial_report = args
    #     date_from = options['date']['date_from']
    #     date_to = options['date']['date_to']
    #     country_id = expression.report_line_id.report_id.country_id

    #     formula = '7. Goods imported into the UAE (Base)'
    #     tags = self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
    #     # formula = '11. Supplies subject to the reverse charge provisions (Base)'
    #     # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

    #     domain = [
    #         ('move_id.move_type', '=', 'in_invoice'),  # Vendor Bill
    #         # ('ass_value', '>', 0),
    #         ('date', '>=', date_from),
    #         ('date', '<=', date_to),
    #         ('company_id', '=', self.env.company.id),
    #         ('tax_tag_ids', 'in', tags.ids),
    #         ('move_id.state', '=', 'posted')
    #     ]

    #     move_lines = self.env['account.move.line'].search(domain)
    #     total = 0
    #     if move_lines:
    #         # total = sum(map(abs, move_lines.mapped('balance')))
    #         total = sum(map(abs, move_lines.move_id.mapped('ass_value')))
    #         # total = sum(move_lines.mapped('ass_value'))

    #     return {
    #         'balance': total,
    #     }

    def _report_custom_engine_compute_ass_value_vat_three(self, *args, **kwargs):
        expression, options, strict_range, currency_table, financial_report = args
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        country_id = expression.report_line_id.report_id.country_id

        formula = '3. Supplies subject to reverse charge provisions (Tax)'
        tags = self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
        # formula = '11. Supplies subject to the reverse charge provisions (Tax)'
        # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

        domain = [
            ('move_id.move_type', '=', 'in_invoice'),  # Vendor Bill
            # ('ass_value', '>', 0),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
            ('tax_tag_ids', 'in', tags.ids),
            ('move_id.state', '=', 'posted')
        ]

        move_lines = self.env['account.move.line'].search(domain)
        total = 0
        if move_lines:
            # total = sum(move_lines.mapped("ass_value")) + sum(
            #     map(abs, move_lines.filtered(lambda l: not l.tax_ids).mapped("debit"))
            # )
            total = sum(map(abs, move_lines.filtered(lambda l: not l.tax_ids).mapped("balance")))

        return {
            'balance': total,
        }

    # def _report_custom_engine_compute_ass_value_vat_seven(self, *args, **kwargs):
    #         expression, options, strict_range, currency_table, financial_report = args
    #         date_from = options['date']['date_from']
    #         date_to = options['date']['date_to']
    #         country_id = expression.report_line_id.report_id.country_id

    #         formula = '7. Goods imported into the UAE (Tax)'
    #         tags = self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
    #         # formula = '3. Supplies subject to reverse charge provisions (Tax)'
    #         # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
    #         # formula = '11. Supplies subject to the reverse charge provisions (Tax)'
    #         # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

    #         domain = [
    #             ('move_id.move_type', '=', 'in_invoice'),  # Vendor Bill
    #             # ('ass_value', '>', 0),
    #             ('date', '>=', date_from),
    #             ('date', '<=', date_to),
    #             ('company_id', '=', self.env.company.id),
    #             ('tax_tag_ids', 'in', tags.ids),
    #             ('move_id.state', '=', 'posted')
    #         ]

    #         move_lines = self.env['account.move.line'].search(domain)
    #         total = 0
    #         if move_lines:
    #             # total = sum(move_lines.mapped("ass_value")) + sum(
    #             #     map(abs, move_lines.filtered(lambda l: not l.tax_ids).mapped("debit"))
    #             # )
    #             total = sum(map(abs, move_lines.filtered(lambda l: not l.tax_ids).mapped("balance")))

    #         return {
    #             'balance': total,
    #         }


    # TAG 6 for custom report

    def _report_custom_engine_compute_ass_value_base_six(self, *args, **kwargs):
        # For Goods
        expression, options, strict_range, currency_table, financial_report = args
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        country_id = expression.report_line_id.report_id.country_id

        formula = '6 Supplies subject to the reverse charge provisions (Base) S'
        tags = self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

        formula = '6 Supplies subject to the reverse charge provisions (Base) G'
        tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
        # formula = '11. Supplies subject to the reverse charge provisions (Base)'
        # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

        domain = [
            ('move_id.move_type', '=', 'in_invoice'),  # Vendor Bill
            ('ass_value', '>', 0),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
            ('tax_tag_ids', 'in', tags.ids),
            ('move_id.state', '=', 'posted')
        ]

        move_lines = self.env['account.move.line'].search(domain)
        total = 0
        if move_lines:
            # total = sum(map(abs, move_lines.mapped('balance')))
            total = sum(map(abs, move_lines.mapped('ass_value')))
            # total = sum(move_lines.mapped('ass_value'))

        return {
            'balance': total,
        }


    def _report_custom_engine_compute_ass_value_vat_six(self, *args, **kwargs):
        expression, options, strict_range, currency_table, financial_report = args
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        country_id = expression.report_line_id.report_id.country_id

        formula = '6. Supplies subject to reverse charge provisions (Tax)'
        tags = self.env['account.account.tag']._get_tax_tags(formula, country_id.id)
        # formula = '11. Supplies subject to the reverse charge provisions (Tax)'
        # tags |= self.env['account.account.tag']._get_tax_tags(formula, country_id.id)

        domain = [
            ('move_id.move_type', '=', 'in_invoice'),  # Vendor Bill
            # ('ass_value', '>', 0),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
            ('tax_tag_ids', 'in', tags.ids),
            ('move_id.state', '=', 'posted')
        ]

        move_lines = self.env['account.move.line'].search(domain)
        total = 0
        if move_lines:
            # total = sum(move_lines.mapped("ass_value")) + sum(
            #     map(abs, move_lines.filtered(lambda l: not l.tax_ids).mapped("debit"))
            # )
            total = sum(map(abs, move_lines.filtered(lambda l: not l.tax_ids).mapped("balance")))

        return {
            'balance': total,
        }

