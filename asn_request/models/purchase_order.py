from odoo import models, fields, api,SUPERUSER_ID
import io
import xlsxwriter
import base64
from datetime import date

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_category = fields.Selection([('foreign', 'FPO'), ('local', 'LPO')], string='PO Category')

    # def _create_picking(self):
    #     if not self.env.context.get('from_asn_request'):
    #         res = super(PurchaseOrder, self.filtered(lambda s: s.po_category != 'foreign'))._create_picking()
    #     else:
    #         res = super(PurchaseOrder, self)._create_picking()
    #     return res

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        if not self.env.context.get('from_asn_request'):
            self = self.filtered(lambda s: s.po_category != 'foreign')
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            if any(product.type == 'consu' for product in order.order_line.product_id):
                order = order.with_company(order.company_id)
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if not pickings or self.env.context.get('from_asn_request'):
                    res = order._prepare_picking()
                    picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                    pickings = picking
                else:
                    picking = pickings[0]
                if self.env.context.get('from_asn_request'):
                    order_line = self.env.context.get('asn_record').line_ids.mapped('purchase_order_line_id').filtered(lambda s:s.order_id == order)
                    context = dict(self._context)
                    moves = order_line.with_context(context)._create_stock_moves(picking)
                else:
                    moves = order.order_line._create_stock_moves(picking)
                moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                # Get following pickings (created by push rules) to confirm them as well.
                forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
                (pickings | forward_pickings).action_confirm()
                picking.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': picking, 'origin': order},
                    subtype_xmlid='mail.mt_note',
                )
        return True

    def action_print_po_report_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet("Purchase Report")
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_format = workbook.add_format({"num_format": "#,##0.00"})
        headers = [
            "Vendor No", "Vendor name", "PO number", "PO Type",
            "Receipt num trx ", "Receive date", "Amount in currency","Currency","Amount AED"
        ]
        row =  0
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, header_format)
        row += 1
        for record in self:
            # aed_currency = self.env.ref('base.AED')
            # aed_amount = record.amount_total
            # if record.currency_id != aed_currency:
            #     aed_amount = record.currency_id._convert(
            #         from_amount=record.amount_total,
            #         to_currency=aed_currency,
            #         date=date.today(),
            #         company=record.company_id,
            #     )
            worksheet.write(row, 0, record.vendor_trn or '')
            worksheet.write(row, 1, record.partner_id.name or '')
            worksheet.write(row, 2, record.name or '')
            po_type = ''
            if record.po_type:
                po_type = dict(record.fields_get(allfields=['po_type'])['po_type']['selection'])[record.po_type]
            worksheet.write(row, 3, po_type)
            if record.picking_ids:
                picking_name = record.picking_ids[-1].name
                worksheet.write(row, 4, picking_name)
            else:
                worksheet.write(row, 4, '')
            if record.picking_ids:
                date_done = record.picking_ids[-1].date_done
                if date_done:
                    worksheet.write(row, 5, date_done.strftime('%Y-%m-%d'))
                else:
                    worksheet.write(row, 5, '')
            else:
                worksheet.write(row, 5, '')
            worksheet.write(row, 6, record.amount_total,number_format)
            worksheet.write(row, 7, record.currency_id.symbol)
            worksheet.write(row, 8, record.amount_total_cc, number_format)
            row += 1
        worksheet.set_column(0, 5, 30)
        worksheet.set_column(6, 17, 30)
        workbook.close()
        output.seek(0)
        xlsx_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Purchase_Report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'res_model': 'purchase.order',
            'res_id': self[0].id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    @api.onchange('picking_ids', 'picking_ids.state', 'asn_ids.line_ids', 'order_line', 'order_line.product_qty',
                  'order_line.asn_released_qty', 'order_line.qty_received')
    def _onchange_po_line_state(self):
        for po_line in self.order_line:
            print("\n\n PO Line state:", po_line.state)
            if po_line.asn_released_qty == po_line.product_qty:
                po_line.state = 'done'
            else:
                po_line.state = po_line.order_id.state
            po_line._compute_po_line_state()
            print("Po line final state:", po_line.state , '\n----------------------------\n')
