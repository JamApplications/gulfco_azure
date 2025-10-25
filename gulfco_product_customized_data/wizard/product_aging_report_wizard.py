from odoo import models, fields, api
import io
import xlsxwriter
import base64
from datetime import date

class ProductAgingReportWizard(models.TransientModel):
    _name = 'product.aging.report.wizard'
    _description = 'Product Aging Report Wizard'

    brand_ids = fields.Many2many('product.brand', string='Product Brand')
    category_ids = fields.Many2many('product.category', string='Product Category')
    all_category = fields.Boolean(string='All Categories')
    location_ids = fields.Many2many('stock.location', string='Location')
    all_location = fields.Boolean(string='All Locations')
    date = fields.Date(string="Date",default=fields.Date.context_today)

    @api.onchange('all_category')
    def _onchange_all_category(self):
        if self.all_category:
            self.category_ids = [(5, 0, 0)]

    @api.onchange('all_location')
    def _onchange_all_location(self):
        if self.all_location:
            self.location_ids = [(5, 0, 0)]

    def print_pdf(self):
        return self.env.ref('gulfco_product_customized_data.action_product_aging_report').report_action(self)

    def print_xls(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet("Summary Report")
        border = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'dd-mmm-yyyy hh:mm', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        # Headers
        headers = [
            "Department", "Item Code", "Item Description", "UOM", "Item Type",
            "Inventory Category", "Qty OH", "Cost", "Item Amount",
            "<=3", "<=6", "<=12", "<=18", "<=24", "<=30","<=36", ">36"
        ]
        sheet.write('A1', self.env.company.name)
        sheet.write('B1', 'Date:')
        sheet.write_datetime('C1', fields.Datetime.now(), date_format)
        row = 3
        for col_num, header in enumerate(headers):
            sheet.write(row, col_num, header, header_format)
        row += 1
        data = self.get_product_aging_report_data()
        for line in data:
            sheet.write(row, 0, line.get('brand_name'))
            sheet.write(row, 1, line.get('default_code'))
            sheet.write(row, 2, line.get('item_name'))
            sheet.write(row, 3, line.get('uom'))
            sheet.write(row, 4, line.get('item_type'))
            sheet.write(row, 5, line.get('category'))
            sheet.write(row, 6, line.get('on_hand_qty'))
            sheet.write(row, 7, line.get('cost'))
            sheet.write(row, 8, line.get('item_amount'))
            sheet.write(row, 9, line.get('0_3') or 0.0,number_format)
            sheet.write(row, 10, line.get('4_6') or 0.0 ,number_format)
            sheet.write(row, 11, line.get('10_12') or 0.0,number_format)
            sheet.write(row, 12, line.get('13_18') or 0.0,number_format)
            sheet.write(row, 13, line.get('19_24') or 0.0,number_format)
            sheet.write(row, 14, line.get('25_30') or 0.0,number_format)
            sheet.write(row, 15, line.get('31_36') or 0.0,number_format)
            sheet.write(row, 15, line.get('over_36') or 0.0,number_format)
            row += 1
        sheet.set_column(0, 5, 30)
        sheet.set_column(6, 17, 20)
        workbook.close()
        output.seek(0)
        xlsx_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Product_Aging.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'product.aging.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


    def _get_product_period_qty(self, expiry_date):
        today = date.today()
        diff_months = (expiry_date.year - today.year) * 12 + (expiry_date.month - today.month)
        if diff_months <= 3:
            return '0_3'
        elif diff_months <= 6:
            return '4_6'
        elif diff_months <= 12:
            return '7_12'
        elif diff_months <= 18:
            return '13_18'
        elif diff_months <= 24:
            return '19_24'
        elif diff_months <= 30:
            return '25_30'
        elif diff_months <= 36:
            return '31_36'
        else:
            return 'over_36'

    def get_product_aging_report_data(self):
        if self.all_category:
            product_template_records = self.env['product.template'].sudo().search([('brand_id','=',self.brand_ids.ids)])
        else:
            product_template_records = self.env['product.template'].sudo().search([('brand_id','=',self.brand_ids.ids),('categ_id','in',self.category_ids.ids)])
        lines = []
        for product in product_template_records:
            if self.all_location:
                on_hand_qty = product.qty_available
                quant_records = self.env['stock.quant'].search([
                    ('product_id', 'in', product.product_variant_ids.ids)
                ])
                lots_records  = quant_records.mapped("lot_id")
            else:
                on_hand_qty = product.with_context(location=self.location_ids.ids).qty_available
                quant_records = self.env['stock.quant'].search([
                    ('product_id', 'in', product.product_variant_ids.ids)
                    ('location_id', 'in', self.location_ids.ids)
                ])
                lots_records  = quant_records.mapped("lot_id")
            result = []
            existing = False
            for lot in lots_records:
                bucket = self._get_product_period_qty(lot.expiration_date)
                existing = next((line for line in result if line['product'] == product.id), None)
                if not existing:
                    existing = {
                        'product': product.id,
                        'uom': product.uom_id.name,
                        'qty': lot.product_qty,
                        product.id: {'0_3': 0, '4_6': 0, '10_12': 0, '13_18': 0, '19_24': 0,'25_30':0,'31_36':0,'over_36':0}
                    }
                    result.append(existing)
                existing[product.id][bucket] += lot.product_qty
            vals = {
                'brand_name' : product.brand_id.name,
                'default_code': product.default_code,
                'item_name': product.name,
                'uom':product.uom_id.name,
                'item_type':product.item_type,
                'category' : product.categ_id.name,
                'on_hand_qty':on_hand_qty,
                'cost':product.standard_price,
                'item_amount':product.list_price,
            }
            if existing:
                if existing.get(product.id):
                    vals = {**vals,**existing.get(product.id)}
            lines.append(vals)
        return lines
