
# from odoo import models, fields, api
# import io
# import base64
# import xlsxwriter
# from odoo.exceptions import ValidationError
# from datetime import datetime, time
#
# class SalesOrderRmaReportWizard(models.TransientModel):
#     _name = 'sales.order.rma.report.wizard'
#     _description = 'Sales Order Rma Report Wizard'
#
#     date_from = fields.Date(string="Sales Order Start Date")
#     date_to = fields.Date(string="Sales Order End Date")
#     file_data = fields.Binary(string="Report File", readonly=True)
#     file_name = fields.Char(string="File Name")
#
#     show_invoice_dates = fields.Boolean(string="Filter by Sales Order Date")
#
#     invoice_date_from = fields.Datetime(string="Invoice Start Date")
#     invoice_date_to = fields.Datetime(string="Invoice End Date")
#     refund_id = fields.Many2one('account.move', string="Refund Invoice")
#
#     @api.constrains('date_from', 'date_to')
#     def _check_dates(self):
#         for record in self:
#             if record.date_from and record.date_to and record.date_to < record.date_from:
#                 raise ValidationError("End Date cannot be before Start Date.")
#
#     @api.constrains('invoice_date_from', 'invoice_date_to')
#     def _check_invoice_dates(self):
#         for record in self:
#             if record.invoice_date_from and record.invoice_date_to and record.invoice_date_to < record.invoice_date_from:
#                 raise ValidationError("Invoice End Date cannot be before Invoice Start Date.")
#
#     def generate_report(self):
#         # ===== دالة داخلية لتوحيد بيانات العميل =====
#         def get_partner_data(partner):
#             if not partner:
#                 return {
#                     'name': '',
#                     'customer_code': '',
#                     'channel': '',
#                     'outlet': '',
#                     'sub_outlet': '',
#                     'customer_type': '',
#                     'group': '',
#                     'subdivision': '',
#                     'external_ref': '',
#                 }
#             return {
#                 'name': partner.name or '',
#                 'customer_code': partner.customer_code or '',
#                 'channel': partner.partner_channel_id.display_name if partner.partner_channel_id else '',
#                 'outlet': partner.outlet_id.outlet_name if partner.outlet_id else '',
#                 'sub_outlet': partner.sub_outlet_id.display_name if partner.sub_outlet_id else '',
#                 'customer_type': partner.customer_type or '',
#                 'group': partner.customer_group_id.name if partner.customer_group_id else '',
#                 'subdivision': partner.customer_subdivision_id.name if partner.customer_subdivision_id else '',
#                 'external_ref': partner.external_ref or '',
#             }
#
#         # ===== إعداد domain لجلب Sales Orders =====
#         domain = [('state', 'in', ['sale', 'done'])]
#         if self.show_invoice_dates:
#             if self.date_from:
#                 domain.append(('date_order', '>=', datetime.combine(self.date_from, time.min)))
#             if self.date_to:
#                 domain.append(('date_order', '<=', datetime.combine(self.date_to, time.max)))
#         orders = self.env['sale.order'].search(domain, order='date_order')
#
#         # فلترة حسب الفواتير إذا لم نستخدم تاريخ الطلب
#         if not self.show_invoice_dates and (self.invoice_date_from or self.invoice_date_to):
#             invoice_domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
#             if self.invoice_date_from:
#                 invoice_domain.append(('invoice_date', '>=', datetime.combine(self.invoice_date_from, time.min)))
#             if self.invoice_date_to:
#                 invoice_domain.append(('invoice_date', '<=', datetime.combine(self.invoice_date_to, time.max)))
#             invoices = self.env['account.move'].search(invoice_domain)
#             orders_with_invoices = invoices.mapped('invoice_line_ids.sale_line_ids.order_id')
#             orders = orders.filtered(lambda o: o in orders_with_invoices)
#
#         # ===== بناء خريطة invoice_lines مرة واحدة =====
#         all_invoices = self.env['account.move'].search([
#             ('move_type', '=', 'out_invoice'),
#             ('state', '=', 'posted'),
#             ('invoice_line_ids.sale_line_ids.order_id', 'in', orders.ids)
#         ])
#         invoice_line_map = {sl.id: l for inv in all_invoices for l in inv.invoice_line_ids for sl in l.sale_line_ids}
#
#         # ===== تجهيز ملف Excel =====
#         output = io.BytesIO()
#         workbook = xlsxwriter.Workbook(output, {'constant_memory': True})
#         sheet = workbook.add_worksheet("Sales Orders & Credit Notes")
#
#         header_format = workbook.add_format({
#             'bold': True,
#             'bg_color': '#D3D3D3',
#             'border': 1,
#             'align': 'center',
#             'valign': 'vcenter'
#         })
#
#         headers = ['Day', 'Order Number', 'Customer', 'Customer Code', 'Channel', 'Outlet Classification',
#                    'Sub Classification', 'Customer Type', 'Customer Group', 'Delivery Address', 'Sub Channel',
#                    'External Reference', 'Salesman', 'Order Date', 'Product', 'Internal Reference', 'Category',
#                    'Brand', 'Product Division', 'SO_Product Packaging', 'SO_Packaging Quantity',
#                    'SO_Product Packaging Price', 'INV_Product Packaging', 'INV_Packaging Quantity',
#                    'INV_Product Packaging Price', 'SO_Unit Qty', 'INV_Unit Qty', 'SO_Unit Price', 'INV_Unit Price',
#                    'Delivered Qty', 'Invoiced Qty', 'Cost', 'Excise Tax', 'INV_Discount', 'INV_Discount Amount',
#                    'INV_Gross Amount', 'SO_Total Before Vat(TAX)', 'SO_VAT(TAX) Amount', 'SO_Total after VAT(TAX)',
#                    'INV_Total Before Vat(TAX)', 'INV_VAT(TAX) Amount', 'INV_Total after VAT(TAX)',
#                    'Sales Order Status', 'Delivery Status', 'Invoice Status', 'Invoice Number', 'Invoice Dates',
#                    'Journal Name', 'Invoice Status', 'Payment Status', 'Return Reason']
#
#         for col_num, header in enumerate(headers):
#             sheet.write(0, col_num, header, header_format)
#
#         row = 1
#
#         # ===== كتابة Sales Orders =====
#         for order in orders:
#             partner_data = get_partner_data(order.partner_id)
#             invoices = order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')
#             invoice_line_ids = [invoice_line_map.get(line.id) for line in order.order_line]
#             invoice_names = ', '.join(inv.name for inv in invoices if inv.name)
#             invoice_dates = ', '.join(inv.invoice_date.strftime('%Y-%m-%d') for inv in invoices if inv.invoice_date)
#             for line in order.order_line:
#                 inv_line = invoice_line_map.get(line.id)
#                 product = line.product_id
#                 sales_amount_before_tax = (line.price_unit or 0) * (line.product_uom_qty or 0) * (
#                             1 - (line.discount or 0) / 100)
#                 tax_percent = sum(t.amount for t in line.tax_id)
#                 vat_amount = sales_amount_before_tax * (tax_percent / 100)
#                 discount_value = inv_line.discount if inv_line else 0
#                 discount_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0) * (
#                             inv_line.discount / 100)) if inv_line else 0
#                 gross_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0)) if inv_line else 0
#                 delivery_status = 'Delivered' if all(p.state == 'done' for p in order.picking_ids) else 'Pending'
#                 invoice_status_label = dict(order._fields['invoice_status'].selection).get(order.invoice_status, 'N/A')
#
#                 sheet.write_row(row, 0, [
#                     order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
#                     order.name or '',
#                     partner_data['name'],
#                     partner_data['customer_code'],
#                     partner_data['channel'],
#                     partner_data['outlet'],
#                     partner_data['sub_outlet'],
#                     partner_data['customer_type'],
#                     partner_data['group'],
#                     order.partner_shipping_id.display_name if order.partner_shipping_id else '',
#                     partner_data['subdivision'],
#                     partner_data['external_ref'],
#                     order.assign_to.name if order.assign_to else '',
#                     order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
#                     product.name or '',
#                     product.default_code or '',
#                     product.categ_id.name if product.categ_id else '',
#                     product.brand_id.name if product.brand_id else '',
#                     product.division or '',
#                     line.product_packaging_id.name if line.product_packaging_id else '',
#                     line.product_packaging_qty or '',
#                     line.product_packaging_price or '',
#                     inv_line.product_packaging_id.name if inv_line and inv_line.product_packaging_id else '',
#                     inv_line.product_packaging_qty or '' if inv_line else '',
#                     inv_line.product_packaging_price or '' if inv_line else '',
#                     line.product_uom_qty or '',
#                     inv_line.quantity or '' if inv_line else '',
#                     line.price_unit or '',
#                     inv_line.price_unit or '' if inv_line else '',
#                     line.qty_delivered or '',
#                     line.qty_invoiced or '',
#                     getattr(line, 'purchase_price', '') or '',
#                     getattr(line, 'exercise_price', '') or '',
#                     discount_value,
#                     discount_amount,
#                     gross_amount,
#                     sales_amount_before_tax or '',
#                     vat_amount or '',
#                     line.price_total or '',
#                     inv_line.price_subtotal or '' if inv_line else '',
#                     getattr(inv_line, 'l10n_ae_vat_amount', '') or '',
#                     getattr(inv_line, 'price_total', inv_line.price_subtotal) or '' if inv_line else '',
#                     order.state or '',
#                     delivery_status,
#                     invoice_status_label,
#                     invoice_names or 'No Invoice',
#                     invoice_dates,
#                     inv_line.move_id.journal_id.name if inv_line and inv_line.move_id and inv_line.move_id.journal_id else '',
#                     inv_line.move_id.state if inv_line and inv_line.move_id else '',
#                     dict(inv_line.move_id._fields['payment_state'].selection).get(inv_line.move_id.payment_state,
#                                                                                   '') if inv_line and inv_line.move_id else ''
#                 ])
#                 row += 1
#
#         # # ===== كتابة Credit Notes =====
#         # credit_notes = self.env['account.move'].search([
#         #     ('move_type', '=', 'out_refund'),
#         #     ('state', '=', 'posted')
#         # ])
#
#         rma_format = workbook.add_format(
#             {'bold': True, 'font_size': 14, 'bg_color': '#5B9BD5', 'font_color': 'white', 'align': 'center'})
#         sheet.write(row, 0, "RMA / Credit Notes", rma_format)
#         row += 1
#
#         rmas = self.env['rma'].search([])
#         for rma in rmas:
#             if rma.refund_id:
#                 cn = rma.refund_id
#                 if cn.move_type == 'out_refund' and cn.state == 'posted':
#                     partner_data = get_partner_data(cn.partner_id)
#                     for line in cn.invoice_line_ids:
#                         inv_line = line
#                         product = line.product_id
#
#                         # ===== القيم الحسابية =====
#                         sales_amount_before_tax = (line.price_unit or 0) * (line.quantity or 0) * (
#                                     1 - (line.discount or 0) / 100)
#                         tax_percent = sum(t.amount for t in line.tax_ids) if line.tax_ids else 0
#                         vat_amount = sales_amount_before_tax * (tax_percent / 100)
#
#                         # ===== الحقول الجديدة =====
#                         # discount_value = inv_line.discount if hasattr(inv_line, 'discount') else 0
#                         # discount_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0) * (
#                         #             inv_line.discount / 100)) if hasattr(inv_line, 'discount') else 0
#
#                         discount_value = inv_line.discount or 0  # النسبة
#                         discount_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0) * (
#                                     (inv_line.discount or 0) / 100))
#
#                         gross_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0)) if inv_line else 0
#                         delivery_status = ''  # لا يوجد تسليم عادة للفواتير المرجعة
#                         invoice_status_label = dict(cn._fields['invoice_status'].selection).get(cn.invoice_status,
#                           '') if hasattr(cn, 'invoice_status') else ''
#
#                         # ===== كتابة الصف في Excel مع الأعمدة الصحيحة =====
#                         sheet.write_row(row, 0, [
#                             rma.date.strftime('%Y-%m-%d') if rma.date else '',
#                             rma.name or '',
#                             # cn.name or '',
#                             partner_data['name'],
#                             partner_data['customer_code'],
#                             partner_data['channel'],
#                             partner_data['outlet'],
#                             partner_data['sub_outlet'],
#                             partner_data['customer_type'],
#                             partner_data['group'],
#                             cn.partner_shipping_id.display_name if cn.partner_shipping_id else '',
#                             partner_data['subdivision'],
#                             partner_data['external_ref'],
#                             cn.invoice_user_id.name if cn.invoice_user_id else '',
#                             cn.invoice_date.strftime('%Y-%m-%d') if cn.invoice_date else '',
#                             product.name or '',
#                             product.default_code or '',
#                             product.categ_id.name if product.categ_id else '',
#                             product.brand_id.name if product.brand_id else '',
#                             product.division or '',
#                             '', '', '',  # SO_Product Packaging, Qty, Price فارغة
#                             line.product_packaging_id.name if line.product_packaging_id else '',
#                             line.product_packaging_qty or '',
#                             line.product_packaging_price or '',
#                             line.quantity or '',
#                             line.price_unit or '',
#                             '',  # SO Unit Price فارغة
#                             line.price_unit or '',
#                             '', '', '',  # SO Delivered & Invoiced Qty فارغة
#                             '', '', '', '',  # Cost, Excise Tax فارغة
#                             sales_amount_before_tax or 0,
#                             vat_amount or 0,
#                             discount_value,
#                             discount_amount,
#                             gross_amount,
#                             line.price_subtotal or '',
#                             getattr(line, 'l10n_ae_vat_amount', '') or '',
#                             getattr(line, 'price_total', line.price_subtotal) or '',
#                             delivery_status,
#                             invoice_status_label,
#                             cn.name or 'No Invoice',
#                             cn.invoice_date.strftime('%Y-%m-%d') if cn.invoice_date else '',
#                             cn.journal_id.name if cn.journal_id else '',
#                             cn.state or '',
#                             dict(cn._fields['payment_state'].selection).get(cn.payment_state, '') if hasattr(cn,
#                             'payment_state') else ''
#                             # rma.return_reason_id.name if rma.return_reason_id else ''
#                         ])
#                         row += 1
#
#         sheet.write(
#             row, 0,
#             f"Sales Order Period: {self.date_from.strftime('%Y-%m-%d') if self.date_from else 'N/A'} to "
#             f"{self.date_to.strftime('%Y-%m-%d') if self.date_to else 'N/A'}    |    "
#             f"Invoice Period: {invoice_date_from_local.strftime('%Y-%m-%d') if invoice_date_from_local else 'N/A'} to "
#             f"{invoice_date_to_local.strftime('%Y-%m-%d') if invoice_date_to_local else 'N/A'}",
#             period_format
#         )
#         row += 1
#
#
#         workbook.close()
#         output.seek(0)
#         self.file_data = base64.b64encode(output.read())
#         self.file_name = "sales_order_and_credit_notes_report.xlsx"
#
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'sales.order.rma.report.wizard',
#             'view_mode': 'form',
#             'res_id': self.id,
#             'target': 'new',
#         }


from odoo import models, fields, api
import io
import base64
import xlsxwriter
from odoo.exceptions import ValidationError
from datetime import datetime, time

class SalesOrderReportWizard(models.TransientModel):
    _name = 'sales.order.report.wizard'
    _description = 'Sales Order Report Wizard'

    date_from = fields.Date(string="Sales Order Start Date")
    date_to = fields.Date(string="Sales Order End Date")
    file_data = fields.Binary(string="Report File", readonly=True)
    file_name = fields.Char(string="File Name")

    show_invoice_dates = fields.Boolean(string="Filter by Sales Order Date")

    invoice_date_from = fields.Datetime(string="Invoice Start Date")
    invoice_date_to = fields.Datetime(string="Invoice End Date")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_to < record.date_from:
                raise ValidationError("End Date cannot be before Start Date.")

    @api.constrains('invoice_date_from', 'invoice_date_to')
    def _check_invoice_dates(self):
        for record in self:
            if record.invoice_date_from and record.invoice_date_to and record.invoice_date_to < record.invoice_date_from:
                raise ValidationError("Invoice End Date cannot be before Invoice Start Date.")

    def generate_report(self):
        # ===== إعداد domain لجلب الطلبات =====
        domain = [('state', 'in', ['sale', 'done'])]
        if self.show_invoice_dates:
            if self.date_from:
                domain.append(('date_order', '>=', datetime.combine(self.date_from, time.min)))
            if self.date_to:
                domain.append(('date_order', '<=', datetime.combine(self.date_to, time.max)))
        orders = self.env['sale.order'].search(domain, order='date_order')

        # فلترة الطلبات حسب الفواتير إذا لم نستخدم تاريخ الطلب
        if not self.show_invoice_dates and (self.invoice_date_from or self.invoice_date_to):
            invoice_domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
            if self.invoice_date_from:
                invoice_domain.append(('invoice_date', '>=', datetime.combine(self.invoice_date_from, time.min)))
            if self.invoice_date_to:
                invoice_domain.append(('invoice_date', '<=', datetime.combine(self.invoice_date_to, time.max)))
            invoices = self.env['account.move'].search(invoice_domain)
            orders_with_invoices = invoices.mapped('invoice_line_ids.sale_line_ids.order_id')
            orders = orders.filtered(lambda o: o in orders_with_invoices)

        # ===== بناء خريطة invoice_lines مرة واحدة =====
        all_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_line_ids.sale_line_ids.order_id', 'in', orders.ids)
        ])
        invoice_line_map = {sl.id: l for inv in all_invoices for l in inv.invoice_line_ids for sl in l.sale_line_ids}

        # ===== تجهيز ملف Excel =====
        output = io.BytesIO()
        # workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        workbook = xlsxwriter.Workbook(output, {'constant_memory': True})

        sheet = workbook.add_worksheet("Sales Orders")

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        period_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#5B9BD5',
            'font_color': 'white'
        })

        headers = ['Day', 'Order Number', 'Customer', 'Customer Code', 'Channel', 'Outlet Classification',
                   'Sub Classification', 'Customer Type', 'Customer Group', 'Customer Outlet Code', 'Delivery Address', 'Sub Channel',
                   'External Reference', 'Ship to Site', 'Customer Po Reference', 'Salesman', 'Order Date', 'Product', 'Internal Reference', 'Category',
                   'Brand', 'Product Division', 'SO_Product Packaging', 'SO_Packaging Quantity',
                   'SO_Product Packaging Price', 'INV_Product Packaging', 'INV_Packaging Quantity',
                   'INV_Product Packaging Price', 'SO_Unit Qty', 'INV_Unit Qty', 'SO_Unit Price', 'INV_Unit Price',
                   'Delivered Qty', 'Invoiced Qty', 'Cost', 'Excise Tax', 'INV_Discount', 'INV_Discount Amount',
                   'INV_Gross Amount', 'SO_Total Before Vat(TAX)', 'SO_VAT(TAX) Amount', 'SO_Total after VAT(TAX)',
                   'INV_Total Before Vat(TAX)', 'INV_VAT(TAX) Amount', 'INV_Total after VAT(TAX)',
                   'Sales Order Status', 'Delivery Status', 'Invoice Status', 'Invoice Number', 'Invoice Dates',
                   'Journal Name', 'Invoice Status', 'Payment Status']

        for col_num, header in enumerate(headers):
            sheet.write(0, col_num, header, header_format)

        row = 1
        for order in orders:
            partner = order.partner_id
            partner_data = {
                'name': partner.name or '',
                'customer_code': partner.customer_code or '',
                'channel': partner.partner_channel_id.display_name if partner.partner_channel_id else '',
                'outlet': partner.outlet_id.outlet_name if partner.outlet_id else '',
                'sub_outlet': partner.sub_outlet_id.display_name if partner.sub_outlet_id else '',
                'customer_type': partner.customer_type or '',
                'group': partner.customer_group_id.name if partner.customer_group_id else '',
                'outlet_code': partner.outlet_code or '',
                'subdivision': partner.customer_subdivision_id.name if partner.customer_subdivision_id else '',
                'external_ref': partner.external_ref or '',
            }

            invoices = order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')

            invoice_names = ', '.join(inv.name for inv in invoices if inv.name)
            invoice_dates = ', '.join(inv.invoice_date.strftime('%Y-%m-%d') for inv in invoices if inv.invoice_date)

            for line in order.order_line:
                inv_line = invoice_line_map.get(line.id)
                product = line.product_id

                sales_amount_before_tax = (line.price_unit or 0) * (line.product_uom_qty or 0) * (1 - (line.discount or 0) / 100)
                tax_percent = sum(t.amount for t in line.tax_id)
                vat_amount = sales_amount_before_tax * (tax_percent / 100)
                discount_value = inv_line.discount if inv_line else 0
                discount_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0) * (inv_line.discount / 100)) if inv_line else 0
                gross_amount = ((inv_line.price_unit or 0) * (inv_line.quantity or 0)) if inv_line else 0
                delivery_status = 'Delivered' if all(p.state == 'done' for p in order.picking_ids) else 'Pending'
                invoice_status_label = dict(order._fields['invoice_status'].selection).get(order.invoice_status, 'N/A')

                sheet.write_row(row, 0, [
                    order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
                    order.name or '',
                    partner_data['name'],
                    partner_data['customer_code'],
                    partner_data['channel'],
                    partner_data['outlet'],
                    partner_data['sub_outlet'],
                    partner_data['customer_type'],
                    partner_data['group'],
                    partner_data['outlet_code'],
                    order.partner_shipping_id.display_name if order.partner_shipping_id else '',
                    partner_data['subdivision'],
                    partner_data['external_ref'],
                    order.x_studio_site_ or '',
                    order.po_number or '',
                    order.assign_to.name if order.assign_to else '',
                    order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
                    product.name or '',
                    product.default_code or '',
                    product.categ_id.name if product.categ_id else '',
                    product.brand_id.name if product.brand_id else '',
                    product.division or '',
                    line.product_packaging_id.name if line.product_packaging_id else '',
                    line.product_packaging_qty or 0,
                    line.product_packaging_price or 0,
                    inv_line.product_packaging_id.name if inv_line and inv_line.product_packaging_id else '',
                    inv_line.product_packaging_qty or 0 if inv_line else 0,
                    inv_line.product_packaging_price or 0 if inv_line else 0,
                    line.product_uom_qty or 0,
                    inv_line.quantity or 0 if inv_line else 0,
                    line.price_unit or 0,
                    inv_line.price_unit or 0 if inv_line else 0,
                    line.qty_delivered or 0,
                    line.qty_invoiced or 0,
                    line.purchase_price or 0,
                    line.exercise_price or 0,
                    discount_value,
                    discount_amount,
                    gross_amount,
                    sales_amount_before_tax or 0,
                    vat_amount or 0,
                    line.price_total or 0,
                    inv_line.price_subtotal or 0 if inv_line else 0,
                    getattr(inv_line, 'l10n_ae_vat_amount', 0) or 0,
                    getattr(inv_line, 'price_total', inv_line.price_subtotal) or 0 if inv_line else 0,
                    order.state or '',
                    delivery_status,
                    invoice_status_label,
                    invoice_names or 'No Invoice',
                    invoice_dates,
                    inv_line.move_id.journal_id.name if inv_line and inv_line.move_id and inv_line.move_id.journal_id else '',
                    inv_line.move_id.state if inv_line and inv_line.move_id else '',
                    dict(inv_line.move_id._fields['payment_state'].selection).get(inv_line.move_id.payment_state, '') if inv_line and inv_line.move_id else ''
                ])
                row += 1

        # sheet.write(
        #     row, 0,
        #     f"Sales Order Period: {self.date_from.strftime('%Y-%m-%d') if self.date_from else 'N/A'} to "
        #     f"{self.date_to.strftime('%Y-%m-%d') if self.date_to else 'N/A'}    |    "
        #     f"Invoice Period: {self.invoice_date_from.strftime('%Y-%m-%d') if self.invoice_date_from else 'N/A'} to "
        #     f"{self.invoice_date_to.strftime('%Y-%m-%d') if self.invoice_date_to else 'N/A'}",
        #     period_format
        # )

        invoice_date_from_local = fields.Datetime.context_timestamp(self,
                                                                    self.invoice_date_from) if self.invoice_date_from else None
        invoice_date_to_local = fields.Datetime.context_timestamp(self,
                                                                  self.invoice_date_to) if self.invoice_date_to else None

        sheet.write(
            row, 0,
            f"Sales Order Period: {self.date_from.strftime('%Y-%m-%d') if self.date_from else 'N/A'} to "
            f"{self.date_to.strftime('%Y-%m-%d') if self.date_to else 'N/A'}    |    "
            f"Invoice Period: {invoice_date_from_local.strftime('%Y-%m-%d') if invoice_date_from_local else 'N/A'} to "
            f"{invoice_date_to_local.strftime('%Y-%m-%d') if invoice_date_to_local else 'N/A'}",
            period_format
        )



        workbook.close()
        output.seek(0)
        self.file_data = base64.b64encode(output.read())
        self.file_name = "sales_order_report.xlsx"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sales.order.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
