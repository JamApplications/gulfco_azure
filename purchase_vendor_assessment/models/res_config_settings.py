
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    filter_vendor_assessment = fields.Boolean(
        string="Don't Buy from Vendor Marked as 'Stop The Partnership'",
        readonly=False,
        compute="_compute_filter_vendor_assessment",
        inverse="_inverse_filter_vendor_assessment")

    @api.depends("company_id")
    def _compute_filter_vendor_assessment(self):
        view = self.env.ref(
            "purchase_vendor_assessment.purchase_order_form_inherit", False)
        for record in self:
            record.filter_vendor_assessment = view and view.active

    def _inverse_filter_vendor_assessment(self):
        view = self.env.ref(
            "purchase_vendor_assessment.purchase_order_form_inherit", False)
        for record in self:
            view.active = record.filter_vendor_assessment
