
from odoo import api, fields, models, _


class AssessmentPOTemplateLine(models.Model):
    _name = "assessment.purchase.template.line"
    _description = "Assessment Purchase Template Line"
    _rec="sequence,criteria_id"

    template_id = fields.Many2one(
        comodel_name="assessment.purchase.template"
    )
    sequence = fields.Integer(default=1)
    criteria_id = fields.Many2one(
        comodel_name="assessment.criteria",
        required=True
    )
    point_min = fields.Integer(
        string="Min Point"
    )
    point_max = fields.Integer(
        string="Max Point"
    )
