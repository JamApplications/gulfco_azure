# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from odoo import models
from odoo.tools.parse_version import parse_version
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter, to_pdf_stream

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)
        if not res_ids or report.report_name != 'account_followup.report_followup_print_all':
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        else:
            options = data.get('options', {})
            if options.get('attachment_ids') and options.get('soa_attachment_id'):
                attachment_ids = options.get('attachment_ids')
                attachment_ids.append(options.get('soa_attachment_id'))
                options.update({'attachment_ids':attachment_ids})
                data.update({'options':options})
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)