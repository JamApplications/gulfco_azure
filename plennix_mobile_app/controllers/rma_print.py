from odoo.addons.plennix_mobile_app.controllers.user_authenticate import PlennixMobileAppAPI
import requests
from odoo import http
from odoo.http import content_disposition, request

class RMAPrint(PlennixMobileAppAPI):

    @http.route('/my/rma/<int:rma_id>', type='http', auth='public', website=True)
    def _rma_tax_credit_4inch_report_download(self, rma_id, access_token=None, download=False, **kw):
        rma = request.env['rma'].sudo().browse(rma_id)
        if rma.refund_id:
            pdf_content, _ = request.env['ir.actions.report'].with_context(
                force_report_rendering=True).sudo()._render_qweb_pdf(
                'plnx_rma_extended.report_tax_credit_note_4_inch_pdf',
                res_ids=rma.refund_id.id
            )
            headers = [('Content-Type', 'application/pdf')]
            if download:
                headers.append(
                    ('Content-Disposition', f'attachment; filename="Tax Credit(4inch)_{rma.refund_id.name}.pdf"'))
            return request.make_response(pdf_content, headers=headers)
        else:
            return request.make_response(
                "<h3 style='color:red;'>RMA is not in refund state or refund is not created yet.</h3>",
                headers=[('Content-Type', 'text/html')]
            )