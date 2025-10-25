from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountReportInvoice(models.AbstractModel):
    _name = 'report.account.report_invoice'
    _template = 'account.report_invoice'
    _description = 'PDF without Payment Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env['account.move'].browse(docids)
        for move in moves:
            if move.state == 'draft':
                if move.move_type == 'in_invoice':
                    raise UserError("You cannot print the report while the bill is in draft state.")
                else:
                    raise UserError("You cannot print the report while the invoice is in draft state.")
        return {
            'doc_ids': docids,
            'docs': moves,
        }

class AccountReportInvoicePayments(models.AbstractModel):
    _name = 'report.account.report_invoice_with_payments'
    _template = 'account.report_invoice_with_payments'
    _description = 'Invoice With Payment Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env['account.move'].browse(docids)
        for move in moves:
            if move.state == 'draft':
                if move.move_type == 'in_invoice':
                    raise UserError("You cannot print the report while the bill is in draft state.")
                else:
                    raise UserError("You cannot print the report while the invoice is in draft state.")
        return {
            'doc_ids': docids,
            'docs': moves,
        }



class ReportInvoicePDfOverride(models.AbstractModel):
    _name = 'report.stock_outbouding_operation.dummy_template'
    _template = 'stock_outbouding_operation.dummy_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Call your custom ZIP logic here
        moves = self.env['stock.move'].browse(docids)
        return moves.action_print_related_so_invoices()
