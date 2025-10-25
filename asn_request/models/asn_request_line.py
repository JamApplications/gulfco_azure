from odoo import models, fields, api
import io
import xlsxwriter
import base64
from odoo.exceptions import UserError



class ASNRequestLine(models.Model):
    _name = 'asn.request.line'
    _description = 'ASN Request Line'

    asn_request_id = fields.Many2one('asn.request', string='ASN Request')
    partner_id = fields.Many2one('res.partner', string='Supplier', related='asn_request_id.supplier_id')
    purchase_order_id = fields.Many2one('purchase.order', string='PO Number', domain="[('partner_id', '=', partner_id),('po_category','=','foreign')]")
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='PO Line',domain="[('order_id', '=', purchase_order_id)]")
    prchase_order_line_sequence = fields.Integer(string='PO Line Sequence',related='purchase_order_line_id.sequence')
    product_product_id = fields.Many2one('product.product', string='Product')
    product_default_code = fields.Char(string='Product Code', related='product_product_id.default_code')
    product_description = fields.Char(string="Item Description")
    po_uom = fields.Many2one('uom.uom', string='UOM')
    po_qty = fields.Float(string='PO QTY')
    po_unit_price = fields.Float(string='PO Unit Price')
    asn_released_qty = fields.Float(string='ASN Released Qty', ) # tore=True, related="purchase_order_line_id.asn_released_qty") #compute='_compute_product_asn_qty',

    available_qty_to_release = fields.Float(
        string='Available QTY to Release',
        compute='_compute_available_qty_to_release',
        store=True
    )
    invoice_no = fields.Char(string='Invoice No')
    qty_in_invoice = fields.Integer(string='Qty in Invoice')
    container_type = fields.Selection([
        ('20ft', "20' Ft"),
        ('40ft', "40' Ft"),
        ('truck', 'Truck'),
        ('lcl', 'LCL')
    ], string='Container Type')
    container_no = fields.Char(string='Container No')
    count_of_pallets = fields.Char(string='Count of Pallets')
    hs_code = fields.Char(string='HS Code',related="product_product_id.hs_code")
    country_of_origin = fields.Many2one('res.country', string='Country of Origin',related="product_product_id.country_of_origin")
    shipment_value = fields.Float(
        string='Shipment Value',
        compute='_compute_shipment_value',
        store=True
    )
    remarks = fields.Text(string='Remarks')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('warehouse_id', '=', warehouse_id)]"
    )
    po_due_qty_in_case = fields.Integer(string="PO due qty in case", compute="compute_po_due_qty_in_eac")
    po_due_qty_in_eac = fields.Integer(string="PO due qty in Cartoon",compute="_compute_available_qty_to_release",store=True)

    po_qty_in_ctn = fields.Float(string="PO Qty in CTN",compute="compute_po_due_qty_in_eac",store=True)
    qty_in_invoice_ctn = fields.Float(string="Qty Invoice CTN",compute="compute_po_due_qty_in_eac",store=True,readonly=False,precompute=True)
    available_qty_to_release_ctn = fields.Float(string="Available QTY to Release CTN",compute="compute_po_due_qty_in_eac",store=True)

    @api.onchange('qty_in_invoice_ctn')
    def onchange_qty_in_invoice_ctn(self):
        if self.qty_in_invoice_ctn:
            if self.product_product_id.product_tmpl_id.packaging_ids:
                ctn_package = self.product_product_id.product_tmpl_id.packaging_ids.filtered(
                    lambda pack: pack.package_type_id.type == 'ctn')
                if ctn_package:
                    qty_in_invoice = self.qty_in_invoice_ctn * ctn_package[0].qty
                    if qty_in_invoice > self.available_qty_to_release:
                        raise UserError("you can't set more than available quantity for Qty In Invoice field")
                    self.qty_in_invoice = qty_in_invoice
                    self.purchase_order_id._compute_asn_count()
                    self.purchase_order_line_id._compute_product_asn_qty()
                    self.purchase_order_line_id._compute_due_qty()


    @api.onchange('qty_in_invoice')
    def onchange_qty_in_invoice(self):
        if self.qty_in_invoice > self.available_qty_to_release:
            raise UserError("you can't set more than available quantity for Qty In Invoice field")

    @api.depends('qty_in_invoice','available_qty_to_release', 'po_due_qty_in_case','po_qty')
    def compute_po_due_qty_in_eac(self):
        for record in self:
            record.po_due_qty_in_case = 0
            # record.po_due_qty_in_eac = 0
            po_qty_in_ctn = 0.0
            qty_in_invoice_ctn = 0.0
            available_qty_to_release_ctn = 0.0
            if record.product_product_id.product_tmpl_id.packaging_ids:
                box_package = record.product_product_id.product_tmpl_id.packaging_ids.filtered(lambda pack: pack.package_type_id.type == 'box')
                if box_package:
                     record.po_due_qty_in_case = int(record.available_qty_to_release / box_package[0].qty)
                #     pass
                if record.product_product_id.product_tmpl_id.packaging_ids:
                    ctn_package = record.product_product_id.product_tmpl_id.packaging_ids.filtered(
                        lambda pack: pack.package_type_id.type == 'ctn')
                    if ctn_package:
                        # record.po_due_qty_in_eac = int(record.available_qty_to_release / ctn_package[0].qty)
                        po_qty_in_ctn = record.po_qty / ctn_package[0].qty
                        available_qty_to_release_ctn = record.available_qty_to_release / ctn_package[0].qty
                        qty_in_invoice_ctn = record.qty_in_invoice / ctn_package[0].qty
            record.po_qty_in_ctn = po_qty_in_ctn
            record.qty_in_invoice_ctn = qty_in_invoice_ctn
            record.available_qty_to_release_ctn = available_qty_to_release_ctn
            record.purchase_order_id._compute_asn_count()
            record.purchase_order_line_id._compute_product_asn_qty()
            record.purchase_order_line_id._compute_due_qty()



            # record.po_due_qty_in_eac = record.po_due_qty_in_case * 12

    @api.depends('purchase_order_line_id.product_qty','purchase_order_line_id.move_ids','purchase_order_line_id.move_ids.state')
    def _compute_available_qty_to_release(self):
        for record in self:
            move_quantity = sum(record.purchase_order_line_id.move_ids.mapped('quantity'))
            done_move_quantity = sum(record.purchase_order_line_id.move_ids.filtered(lambda s:s.state == 'done').mapped('quantity'))
            record.available_qty_to_release = record.purchase_order_line_id.product_qty - move_quantity
            po_due_qty_in_eac = record.purchase_order_line_id.product_qty - done_move_quantity
            if record.product_product_id.product_tmpl_id.packaging_ids:
                ctn_package = record.product_product_id.product_tmpl_id.packaging_ids.filtered(
                    lambda pack: pack.package_type_id.type == 'ctn')
                if ctn_package:
                    po_due_qty_in_eac = po_due_qty_in_eac / ctn_package[0].qty
            record.po_due_qty_in_eac = po_due_qty_in_eac

    @api.depends('po_unit_price', 'qty_in_invoice')
    def _compute_shipment_value(self):
        for record in self:
            record.shipment_value = record.qty_in_invoice * record.po_unit_price


    @api.onchange('purchase_order_line_id')
    def _onchange_purchase_order_line_id(self):
        if self.purchase_order_line_id:
            self.product_product_id = self.purchase_order_line_id.product_id
            self.po_uom = self.purchase_order_line_id.product_uom
            self.po_qty = self.purchase_order_line_id.product_qty - self.purchase_order_line_id.asn_released_qty
            self.po_unit_price = self.purchase_order_line_id.price_unit
            self.hs_code = self.purchase_order_line_id.product_id.product_tmpl_id.hs_code
            # self.asn_released_qty = self.purchase_order_line_id.asn_released_qty
            # self.country_of_origin = self.purchase_order_line_id.product_id.product_tmpl_id.country_of_origin


    def action_print_asn_summery_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("ASN Summery Report")

        bold = workbook.add_format({'bold': True})
        border = workbook.add_format({'border': 1})
        center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        text_format = workbook.add_format({
            'font_name': 'Calibri',
            'font_size': 11,
            'align': 'left',
            'valign': 'top'
        })
        headers = [
            "BL NO/ASN", "HS Code", "Country of Origin", "Total Invoice Amount",
            "Goods Description", "Total Package", "Total Gross Weight"
        ]
        row =  0
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)
        row += 1
        for record in self:
            total_invoice_amount = record.po_unit_price * record.asn_released_qty
            total_weight = str(record.product_product_id.weight) + ' ' + record.product_product_id.uom_id.name
            worksheet.write(row, 0, record.asn_request_id.bl_no_asn_no or '')
            worksheet.write(row, 1, record.hs_code or '')
            worksheet.write(row, 2, record.country_of_origin.name or '')
            worksheet.write(row, 3, total_invoice_amount,number_format)
            worksheet.write(row, 4, record.product_description or '')
            worksheet.write(row, 5, record.po_due_qty_in_case)
            worksheet.write(row, 6, total_weight)
            row += 1


        # data = []
        # for record in self:
        #     expiry_date = ''
        #     if record.expiry_date:
        #         expiry_date = record.expiry_date.strftime("%Y-%m-%d")
        #     data.append({'product_default_code': record.product_default_code, 'product_id': record.product_id.name,
        #                  'lot_id': record.lot_id.name, 'internal_ref_lot': record.internal_ref_lot,
        #                  'expiry_date': expiry_date, 'on_hand_qty': record.on_hand_qty,
        #                  'counted_qty': record.counted_qty, 'difference_qty': record.difference_qty})
        # row = 9
        # for record in data:
        #     for col, key in enumerate(record):
        #         if isinstance(record.get(key), (int, float)):
        #             worksheet.write(row, col, record.get(key) or '', number_format)
        #         else:
        #             worksheet.write(row, col, record.get(key) or '')
        #     row += 1
        worksheet.set_column(4,4, 40)
        workbook.close()
        output.seek(0)
        # generated_file = output.read()
        xlsx_data = base64.b64encode(output.read())
        output.close()
        # return {
        #     'file_name': 'asn_summery_report.xlsx',
        #     'file_content': generated_file,
        #     'file_type': 'xlsx',
        # }
        attachment = self.env['ir.attachment'].create({
            'name': 'ASN_Summery_report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'asn.request.line',
            'res_id': self[0].id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }