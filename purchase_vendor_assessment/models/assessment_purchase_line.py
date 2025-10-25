
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AssessmentPOLine(models.Model):
    _name = "assessment.purchase.line"
    _description = "Assessment PO Line"
    _order = "sequence,criteria_id"

    assessment_id = fields.Many2one(
        comodel_name="assessment.purchase"
    )
    sequence = fields.Integer(default=1)
    criteria_id = fields.Many2one(
        comodel_name="assessment.criteria",
        required=True
    )
    point = fields.Integer()
    point_min = fields.Integer(
        string="Min Point"
    )
    point_max = fields.Integer(
        string="Max Point"
    )
    comment = fields.Text(compute="_compute_comment")

    @api.depends("point_min", "point_max")
    def _compute_comment(self):
        for record in self:
            record.comment = _("Input point from {} to {}").format(
                record.point_min,
                record.point_max
            )

    @api.constrains("point")
    def _check_point(self):
        for record in self:
            if record.point < record.point_min or record.point > record.point_max:
                raise ValidationError(_('{} is invalid for {}. Input value between {} and {}!').format(
                    record.point,
                    record.criteria_id.name,
                    record.point_min,
                    record.point_max
                ))
