from odoo import models, fields, api
import io
import xlsxwriter
import base64
from datetime import datetime, time


class FSMSummaryReport(models.TransientModel):
    _name = 'fsm.summary.report'
    _description = 'FSM Summary Report'

    date = fields.Date(string='Date', required=True)
    team_id = fields.Many2one('fsm.team', string='Team')

    def print_report(self):
        data = {
            'date': self.date,
            'team_id': self.team_id.id,
        }
        return self.env.ref('fieldservice_shelf_display_management.action_fsm_summary_report').report_action(self)

    def get_report_data(self):
        visit_records = self.env['fsm.order'].sudo().search([('team_id','=',self.team_id.id)])
        data = []
        for visit  in visit_records:
            rma = self.env['rma'].sudo().search([
                ('visit_id', '=', visit.id),
            ])
            if rma:
                rma = rma.filtered(lambda o: o.date.date() == self.date)
            so = self.env['sale.order'].sudo().search([('fsm_order_id', '=', visit.id)])
            if so:
                so = so.filtered(lambda o: o.date_order.date() == self.date)

            shelf_display_records = self.env['shelf.display'].sudo().search([('date','=',self.date),('visit_id','=',visit.id)])
            stock_count_records = self.env['merchandise.stock.store'].sudo().search(
                [('activity_date', '=', self.date), ('visit_id', '=', visit.id)])
            if shelf_display_records or shelf_display_records or so or rma:
                vals = {
                    'date': self.date.strftime("%Y-%m-%d"),
                    'customer_name': visit.customer_id.name,
                    'staff_no': visit.person_id_partner.worker_code,
                    'name': visit.person_id_partner.name,
                    'account': visit.customer_id.bank_ids[0].acc_number if visit.customer_id.bank_ids else '',
                    'activity_start': visit.date_start.strftime("%Y-%m-%d") if visit.date_start else '',
                    'activity_stop': visit.date_end.strftime("%Y-%m-%d") if visit.date_end else '',
                    'is_shelf_display': 'N',
                    'is_stock_count': 'N',
                    'is_rma_count': 'N',
                    'is_promotion': 'N',
                }
                if shelf_display_records:
                    vals.update({
                        'is_shelf_display': 'Y',
                    })
                if stock_count_records:
                    vals.update({
                        'is_stock_count': 'Y',
                    })
                if so:
                    vals.update({
                        'is_promotion': 'Y',
                    })
                if rma:
                    vals.update({
                        'is_rma_count': 'Y',
                    })
                data.append(vals)
        return data


    def action_print_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("Summary Report")
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        worksheet.merge_range('A1:K1', "Summary Report", header_format)
        worksheet.merge_range('H2:K2', "Activity", header_format)
        headers = [
            "Date", "Staff No", "Name", "Customer Name",
            "Account", "First Start Time", "Day End Time", "SHELF DISPLAY",
            "STOCK COUNT", "RETURN REQUEST", "PROMOTION"
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(2, col_num, header, header_format)
        data = self.get_report_data()
        row = 3
        for record in data:
            for col, key in enumerate(record):
                if isinstance(record.get(key), (int, float)):
                    worksheet.write(row, col, record.get(key) or '', number_format)
                else:
                    worksheet.write(row, col, record.get(key) or '')
            row += 1
        worksheet.set_column(0, 10, 20)
        workbook.close()
        output.seek(0)
        xlsx_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Summary_report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'fsm.summary.report',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }