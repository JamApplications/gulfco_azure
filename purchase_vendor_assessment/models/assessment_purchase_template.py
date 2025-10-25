
from odoo import api, fields, models, _


class AssessmentPOTemplate(models.Model):
    _name = "assessment.purchase.template"
    _description = "Assessment Purchase Template"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=1)
    partner_categ_ids = fields.Many2many(
        comodel_name="res.partner.category",
        string="Vendor Tags"
    )
    result_ids = fields.One2many(
        comodel_name="assessment.purchase.template.result",
        inverse_name="template_id"
    )
    line_ids = fields.One2many(
        comodel_name="assessment.purchase.template.line",
        inverse_name="template_id"
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company"
    )
