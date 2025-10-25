from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import xlsxwriter
import base64



class AccountMove(models.Model):
    _inherit = "account.move"


    is_advanced_payment = fields.Boolean("advanced Payment",compute='_compute_is_advanced_payment', store=True)

    @api.depends('origin_payment_id', 'origin_payment_id.advance_sale_purchase')
    def _compute_is_advanced_payment(self):
        for rec in self:
            if rec.origin_payment_id and rec.origin_payment_id.advance_sale_purchase:
                rec.is_advanced_payment = True
            else:
                rec.is_advanced_payment = False


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_sale_purchase = fields.Selection([
        ('purchase', 'Purchase'),
        ('sale', 'Sale')], string='Advance Sale Purchase')

    @api.model
    def create(self, vals):
        partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
        if vals.get('advance_sale_purchase') == 'sale':
            if not partner_id.advance_account_receivable_id:
                raise UserError(_("Please set the Advance Account Receivable for the customer: {}").format(partner_id.name))
        if vals.get('advance_sale_purchase') == 'purchase':
            if not partner_id.advance_account_payable_id:
                raise UserError(_("Please set the Advance Account Payable for the Vendor: {}").format(partner_id.name))
        res = super(AccountPayment, self).create(vals)
        if res.advance_sale_purchase == 'sale':
            res.move_id.line_ids.filtered(lambda x: x.credit > 0).update(
                {'account_id': res.partner_id.advance_account_receivable_id.id})
        if res.advance_sale_purchase == 'purchase':
            res.move_id.line_ids.filtered(lambda x: x.debit > 0).update(
                {'account_id': res.partner_id.advance_account_payable_id.id})
        if res.advance_sale_purchase == 'sale' and res.sale_id:
            res.memo = res.sale_id.name
        if res.advance_sale_purchase == 'purchase' and res.purchase_id:
            res.memo = res.purchase_id.name
        return res

    # def action_post(self):
    #     payment =  super(AccountPayment, self).action_post()
    #     for rec in self:
    #         if rec.advance_sale_purchase == 'purchase':
    #             rec.move_id.line_ids.filtered(lambda x: x.debit > 0).update(
    #                 {'account_id': rec.partner_id.advance_account_payable_id.id})
    #         if rec.advance_sale_purchase == 'sale':
    #             rec.move_id.line_ids.filtered(lambda x: x.credit > 0).update(
    #                 {'account_id': rec.partner_id.advance_account_receivable_id.id})
    #     return payment

    @api.onchange('payment_type')
    def onchange_payment_type(self):
        if self._context.get('default_advance_sale_purchase') == 'purchase' and self.payment_type == 'inbound':
            self.advance_sale_purchase = 'sale'
        elif self._context.get('default_advance_sale_purchase') == 'sale' and self.payment_type == 'outbound':
            self.advance_sale_purchase = 'purchase'
        elif self._context.get('default_advance_sale_purchase') == 'purchase' and self.payment_type == 'outbound':
            self.advance_sale_purchase = 'purchase'
        elif self._context.get('default_advance_sale_purchase') == 'sale' and self.payment_type == 'inbound':
            self.advance_sale_purchase = 'sale'



    prepayment_type = fields.Selection([('Temporary', 'Temporary'), ('Permanent', 'Permanent')], string="Prepayment Type")

    def action_print_pre_payment_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("Pre-Payment Report")

        bold = workbook.add_format({'bold': True})
        border = workbook.add_format({'border': 1})
        center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap':True})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        text_format = workbook.add_format({
            'font_name': 'Calibri',
            'font_size': 11,
            'align': 'left',
            'valign': 'top'
        })
        date_format = workbook.add_format({
            'num_format': 'mm/dd/yyyy',  # You can customize this format
            'align': 'center',
            'valign': 'vcenter',
        })
        headers = [
            "Division", "Supplier Number", "Supplier Type", "Supplier Name",
            "Prepayment Type", "Prepayment amount ", "currency", "Prepayment amount (AED)",
            "Voucher Number", "Invoice Number", "Invoice Date", "Currency", "Invoice Amount",
            "Invoice Amount (AED)", "Remaining Amount", "Remaining Amount (AED)"
        ]
        row = 0
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)
        row += 1
        for record in self:
            prepayment_amount_company = record.currency_id._convert(record.amount, record.company_id.currency_id, record.company_id,
                                         record.date)

            # currency_text = ("%s - %s"%(record.currency_id.name, record.currency_id.symbol))
            # total_invoice_amount = record.po_unit_price * record.asn_released_qty
            # total_weight = str(record.product_product_id.weight) + ' ' + record.product_product_id.uom_id.name
            if record.partner_id.supplier_type == 'local':
                supplier_type = 'Local'
            elif record.partner_id.supplier_type == 'foreign':
                supplier_type = 'Foreign'
            else:
                supplier_type = None
            worksheet.write(row, 0, record.company_id.name or '')
            worksheet.write(row, 1, record.partner_id.vendor_code or '')
            worksheet.write(row, 2, supplier_type or '')
            worksheet.write(row, 3, record.partner_id.name, )
            worksheet.write(row, 4, record.prepayment_type or '')
            worksheet.write(row, 5, record.amount, number_format)
            worksheet.write(row, 6, record.currency_id.name)
            worksheet.write(row, 7, prepayment_amount_company or '', number_format)
            worksheet.write(row, 8, record.memo or '')
            if record.sale_id:
                print("inside sale id:")
                inv_list = []
                for inv in record.sale_id.invoice_ids.filtered(lambda move: move.state == 'posted'):
                    total_invoice_amount_company = inv.currency_id._convert(inv.amount_total,
                                                                               inv.company_id.currency_id,
                                                                               inv.company_id,
                                                                               inv.invoice_date or inv.date)

                    amount_residual_company = inv.currency_id._convert(inv.amount_residual,
                                                                          inv.company_id.currency_id,
                                                                          inv.company_id,
                                                                          inv.invoice_date or inv.date)
                    worksheet.write(row, 9, inv.name or '')
                    worksheet.write(row, 10, inv.invoice_date or '', date_format)
                    worksheet.write(row, 11, inv.currency_id.name or '')
                    worksheet.write(row, 12, inv.amount_total or '', number_format)
                    worksheet.write(row, 13, total_invoice_amount_company or '', number_format)
                    worksheet.write(row, 14, inv.amount_residual or 0.0, number_format)
                    worksheet.write(row, 15, amount_residual_company or 0.0, number_format)
                    if inv.id:
                        row += 1
                    inv_list.append(inv.id)

            elif record.purchase_id:
                bill_list = []
                for inv in record.purchase_id.invoice_ids.filtered(lambda move: move.state == 'posted'):
                    total_invoice_amount_company = inv.currency_id._convert(inv.amount_total,
                                                                            inv.company_id.currency_id,
                                                                            inv.company_id,
                                                                            inv.invoice_date or inv.date)

                    amount_residual_company = inv.currency_id._convert(inv.amount_residual,
                                                                       inv.company_id.currency_id,
                                                                       inv.company_id,
                                                                       inv.invoice_date or inv.date)
                    worksheet.write(row, 9, inv.name or '')
                    worksheet.write(row, 10, inv.invoice_date or '', date_format)
                    worksheet.write(row, 11, inv.currency_id.name or '')
                    worksheet.write(row, 12, inv.amount_total or '',number_format)
                    worksheet.write(row, 13, total_invoice_amount_company or '',number_format)
                    worksheet.write(row, 14, inv.amount_residual or 0.0, number_format)
                    worksheet.write(row, 15, amount_residual_company or 0.0, number_format)
                    if inv.id:
                        row += 1
                    bill_list.append(inv.id)

            if not (record.sale_id and record.sale_id.invoice_ids.filtered(lambda move: move.state == 'posted')) and \
                    not (record.purchase_id and record.purchase_id.invoice_ids.filtered(
                        lambda move: move.state == 'posted')):
                row += 1
            # row += 1

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
        worksheet.set_column(0, 16, 20)
        worksheet.set_row(0, 30)
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
            'name': 'Pre-Payment Report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'account.payment',
            'res_id': self[0].id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }