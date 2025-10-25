from odoo.addons.plennix_mobile_app.controllers.user_authenticate import PlennixMobileAppAPI
import requests
from odoo import http
from odoo.http import content_disposition, request
from odoo.exceptions import AccessError

class PAYMENTPrint(PlennixMobileAppAPI):

    @http.route('/my/payment/<int:payment_id>', type='http', auth='public', website=True)
    def payment_download(self, payment_id, access_token=None, download=False, **kw):
        payment = request.env['account.payment'].sudo().browse(payment_id)

        pdf_content, _ = request.env['ir.actions.report'].with_context(
            force_report_rendering=True).sudo()._render_qweb_pdf(
            'account.report_payment_receipt', res_ids=payment.id)
        headers = [('Content-Type', 'application/pdf')]
        if download:
            headers.append(
                ('Content-Disposition', f'attachment; filename="Payment Receipt_{payment.name}.pdf"'))
        return request.make_response(pdf_content, headers=headers)