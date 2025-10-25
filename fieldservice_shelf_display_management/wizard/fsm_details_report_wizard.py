from odoo import models, fields, api
import io
import xlsxwriter
import base64

class FSMDetailsReport(models.TransientModel):
    _name = 'fsm.details.report'
    _description = 'FSM Details Report'

    date = fields.Date(string='Date', required=True)
    team_id = fields.Many2one('fsm.team', string='Team', required=True)
    export_type = fields.Selection([('pdf','PDF'),('xlsx','Xlsx')],default='pdf',string="Export Type")

    def print_report(self):
        data = {
            'date': self.date,
            'team_id': self.team_id.id,
        }
        if self.export_type == "pdf":
            return self.env.ref('fieldservice_shelf_display_management.action_fsm_detail_report').report_action(self)
        else:
            return self.action_print_excel()

    def get_report_data(self):
        visit_records = self.env['fsm.order'].sudo().search([('team_id','=',self.team_id.id)])
        data = []
        for visit  in visit_records:
            shelf_display_records = self.env['shelf.display'].sudo().search([('date','=',self.date),('visit_id','=',visit.id)])
            stock_count_records = self.env['merchandise.stock.store'].sudo().search(
                [('activity_date', '=', self.date), ('visit_id', '=', visit.id)])
            for shelf_display_record in shelf_display_records:
                vals  = {
                    'date' : shelf_display_record.date,
                    'staff_no' : shelf_display_record.worker_id.worker_code,
                    'name': shelf_display_record.worker_id.name,
                    'customer_name' : shelf_display_record.customer_id.name,
                    'account': shelf_display_record.customer_id.bank_ids[0].acc_number if shelf_display_record.customer_id.bank_ids else '',
                    'activity' :'SHELF DISPLAY',
                    'visit' : shelf_display_record.visit_id.name,
                    'activity_start': shelf_display_record.visit_id.date_start,
                    'activity_stop':shelf_display_record.visit_id.date_end
                }
                data.append(vals)
            for stock_count_record in stock_count_records:
                vals  = {
                    'date' : stock_count_record.activity_date,
                    'staff_no' : stock_count_record.worker_id.worker_code,
                    'name': stock_count_record.worker_id.name,
                    'customer_name' : stock_count_record.customer_id.name,
                    'account': stock_count_record.customer_id.bank_ids[0].acc_number if stock_count_record.customer_id.bank_ids else '' ,
                    'activity' :'STOCK COUNT',
                    'visit' : stock_count_record.visit_id.name,
                    'activity_start': stock_count_record.visit_id.date_start,
                    'activity_stop':stock_count_record.visit_id.date_end
                }
                data.append(vals)
            if visit.sale_order_count > 0:
                vals = {
                    'date': self.date,
                    'staff_no': visit.person_id_partner.worker_code,
                    'name': visit.person_id_partner.name,
                    'customer_name': visit.customer_id.name,
                    'account': visit.customer_id.bank_ids[0].acc_number if visit.customer_id.bank_ids else '',
                    'activity': 'PROMOTION',
                    'visit': visit.name,
                    'activity_start': visit.date_start,
                    'activity_stop': visit.date_end
                }
                data.append(vals)
            if visit.rma_count > 0:
                vals = {
                    'date': self.date,
                    'staff_no': visit.person_id_partner.worker_code,
                    'name': visit.person_id_partner.name,
                    'customer_name': visit.customer_id.name,
                    'account': visit.customer_id.bank_ids[0].acc_number if visit.customer_id.bank_ids else '',
                    'activity': 'RETURN REQUEST',
                    'visit': visit.name,
                    'activity_start': visit.date_start,
                    'activity_stop': visit.date_end
                }
                data.append(vals)
        return data


    def action_print_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("Details Report")
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        worksheet.merge_range('A1:H1', "Details Report", header_format)
        headers = [
            "Date", "Staff No", "Name", "Customer Name",
            "Account", "ACTIVITY", "Visit No.", "Activity Start Time","Activity End Time"
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(1, col_num, header, header_format)
        data = self.get_report_data()
        row = 2
        for record in data:
            for col, key in enumerate(record):
                if isinstance(record.get(key), (int, float)):
                    worksheet.write(row, col, record.get(key) or '', number_format)
                elif key == 'date':
                    if record.get(key):
                        worksheet.write(row, col,record.get(key).strftime('%Y-%m-%d'))
                    else:
                        worksheet.write(row, col,'')
                else:
                    worksheet.write(row, col, record.get(key) or '')
            row += 1
        worksheet.set_column(0, 10, 20)
        workbook.close()
        output.seek(0)
        xlsx_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Details_report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'fsm.details.report',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
