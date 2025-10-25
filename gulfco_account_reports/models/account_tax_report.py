# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, osv, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.tools import SQL, Query
from odoo.tools.misc import file_path, format_date, formatLang, split_every, xlsxwriter
import io
import re
from odoo.http import request
import xlsxwriter
import base64
from datetime import date
from datetime import datetime
from itertools import groupby
import markupsafe
from copy import deepcopy
from collections import defaultdict



class AccountTaxReportHandler(models.AbstractModel):
    _inherit = 'account.tax.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['buttons'].append({
            'name': _('VAT Detail Report'),
            'action': 'export_file',
            'action_param': 'export_to_xlsx_tax_return_in_out_report',
            'sequence': 90,
            'always_show': True,
        })

    def export_to_xlsx_tax_return_in_out_report(self, options, response=None, **kwargs):
        report = self.env['account.report'].browse(options['report_id'])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': True,
        })
        worksheet = workbook.add_worksheet("VAT Output Report")
        worksheet1 = workbook.add_worksheet("VAT Input Report")

        report_info_format = workbook.add_format({
            "bold": True, "align": "left", "valign": "vcenter", "font_size": 16,
        })
        header_format = workbook.add_format({"bold": True, "border": 1, 'text_wrap': True})
        number_format = workbook.add_format({"num_format": "#,##0.00"})

        headers = [
            "Transaction Date", "Trx Type", "Invoice No", "Doc Number",
            "Po Rev", "Due Date", "Pay Group", "Currency", "Original Amount",
            "Balance", "Accumulative", "Payment Type", "Div Code"
        ]

        # Write headers
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
            worksheet1.write(0, col_num, header, header_format)

        # _get_report_line_move_line | account.partner.ledger.report.handler
        data = self.env['account.partner.ledger.report.handler']._dynamic_lines_generator(
            report=report, options=options, all_column_groups_expression_totals=None, warnings=None,
        )

        print("data:", data)
        report_lines = report._get_lines(options)
        vendor_moves = []

        for line in report_lines:
            if 'model' in line and line['model'] == 'account.move':
                move_id = int(line['id'].split('~')[-1])
                move = self.env['account.move'].browse(move_id)
                if move.move_type == 'in_invoice':
                    vendor_moves.append(move)
            elif 'expandable' in line and 'children' in line:
                for subline in line['children']:
                    if subline.get('model') == 'account.move':
                        move_id = int(subline['id'].split('~')[-1])
                        move = self.env['account.move'].browse(move_id)
                        if move.move_type == 'in_invoice':
                            vendor_moves.append(move)

        row = 1
        for move in vendor_moves:
            worksheet.write(row, 0, str(move.invoice_date or ''))
            worksheet.write(row, 1, move.move_type)
            worksheet.write(row, 2, move.name or '')
            worksheet.write(row, 3, move.ref or '')
            worksheet.write(row, 4, move.invoice_origin or '')
            worksheet.write(row, 5, str(move.invoice_date_due or ''))
            worksheet.write(row, 6, move.invoice_payment_term_id.name or '')
            worksheet.write(row, 7, move.currency_id.name or '')
            worksheet.write_number(row, 8, move.amount_total, number_format)
            worksheet.write_number(row, 9, move.amount_residual, number_format)
            worksheet.write(row, 10, '')  # Accumulative logic if needed
            worksheet.write(row, 11, '')  # Payment type if needed
            worksheet.write(row, 12, move.company_id.code or '')
            row += 1

        worksheet.set_column(0, 12, 18)
        worksheet1.set_column(0, 12, 18)
        workbook.close()

        output.seek(0)
        generated_file = output.read()
        output.close()

        file_name = 'Tax_Return_Report.xlsx'
        return {
            'file_name': file_name,
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

