from odoo.addons.plennix_mobile_app.controllers.user_authenticate import PlennixMobileAppAPI
import requests
from odoo import http
from odoo.http import content_disposition, request
from odoo.exceptions import AccessError

class InvoicePrint(PlennixMobileAppAPI):

    @http.route('/my/invoice/<int:invoice_id>', type='http', auth='public', website=True)
    def invoice_download(self, invoice_id, access_token=None, download=False, **kw):
        move = request.env['account.move'].sudo().browse(invoice_id)

        pdf_content, _ = request.env['ir.actions.report'].with_context(
            force_report_rendering=True).sudo()._render_qweb_pdf(
            'account.report_invoice_with_payments', res_ids=move.id)
        headers = [('Content-Type', 'application/pdf')]
        if download:
            headers.append(
                ('Content-Disposition', f'attachment; filename="{(move._get_report_base_filename())}.pdf"'))
        return request.make_response(pdf_content, headers=headers)