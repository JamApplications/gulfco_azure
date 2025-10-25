from odoo import models
import base64
import io
import zipfile

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_download_invoice_reports(self):
        self.ensure_one()
        IrActionsReport = self.env['ir.actions.report']

        # Generate first report (Original Invoice)
        report1 = IrActionsReport._render_qweb_pdf(
            'stock_outbouding_operation.tax_account_invoices', [self.id]
        )[0]

        # Generate second report (Copy Invoice)
        report2 = IrActionsReport._render_qweb_pdf(
            'stock_outbouding_operation.tax_account_invoices_copy', [self.id]
        )[0]

        safe_name = self.name.replace('/', '_')        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr(f"{safe_name}_TaxInvoice.pdf", report1)
            zip_file.writestr(f"{safe_name}_TaxInvoice_Copy.pdf", report2)

        zip_buffer.seek(0)
        zip_base64 = base64.b64encode(zip_buffer.read())

        # Return as downloadable attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'{safe_name}_Invoices.zip',
            'type': 'binary',
            'datas': zip_base64,
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/zip'
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
