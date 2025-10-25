from odoo import _, api, fields, models
from odoo.tools import get_lang


class ResPartner(models.Model):
    _inherit = "res.partner"

    # def get_soa_html(self, options=None):
    #     """
    #     Return the content of the follow-up report in HTML
    #     """
    #     if options is None:
    #         options = {}
    #     options.update({
    #         'partner_id': self.id,
    #         # 'followup_line_id': self.followup_line_id,
    #     })
    #     return self.with_context(print_mode=True,lang=self.lang or self.env.user.lang).get_soa_report_html(options)
    #
    # def get_soa_report_html(self, options):
    #     template = 'gulfco_account_reports.report_customer_statement_pdf'
    #     partner = self.env['res.partner'].browse(options['partner_id'])
    #     render_values = {
    #         'doc': partner,
    #         'lang': partner.lang or get_lang(self.env).code,
    #         'options': options,
    #         'context': self.env.context,
    #     }
    #     return self.env['ir.qweb']._render(template, render_values)

    def _execute_followup_partner(self, options=None):
        soa_attachment_id = self._get_soa_report(options)
        if soa_attachment_id:
            options.update({'soa_attachment_id':soa_attachment_id})
        return super()._execute_followup_partner(options)

    def _get_soa_report(self, options):
        soa_report = self.env.ref('gulfco_account_reports.soa_report', raise_if_not_found=False)
        return self._get_partner_soa_account_report_attachment(soa_report).id

    def _get_partner_soa_account_report_attachment(self, report, options=None):
        self.ensure_one()
        if self.lang:
            # Print the followup in the customer's language
            report = report.with_context(lang=self.lang)

        if not options:
            options = report.get_options({
                'forced_companies': self.env.company.search([('id', 'child_of', self.env.context.get('allowed_company_ids', self.env.company.id))]).ids,
                'partner_ids': self.ids,
                'unfold_all': True,
                'unreconciled': True,
                # The following two options are Deprecated, will be removed in master
                'hide_account': True,
                'hide_debit_credit': True,
                'all_entries': False,
            })
        attachment_file = report.soa_export_to_pdf(options)
        return self.env['ir.attachment'].create([
            {
                'name': f"{self.name} - {attachment_file['file_name']}",
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary',
                'raw': attachment_file['file_content'],
                'mimetype': 'application/pdf',
            },
        ])

