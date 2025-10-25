
from odoo import api, fields, models, _


class AssessmentPOTemplateResult(models.Model):
    _name = "assessment.purchase.template.result"
    _description = "Assessment Purchase Template Result"
    _order="template_id, point_max desc"

    template_id = fields.Many2one(
        comodel_name="assessment.purchase.template"
    )
    result_id = fields.Many2one(
        comodel_name="assessment.purchase.result",
        required=True
    )
    point_max = fields.Integer(
        string="Max Point"
    )
    note = fields.Char(
        compute="_compute_note"
    )

    @api.depends("point_max", "template_id")
    def _compute_note(self):
        for record in self:
            prev = record.search([
                ("point_max", "<", record.point_max),
                ("template_id", "=", record.template_id.id)
            ], limit=1, order="point_max desc")
            if prev:
                record.note = _("From {f} to {t}").format(
                    f=prev.point_max + 1,
                    t=record.point_max
                )
            else:
                record.note = _("Equal or below {p}").format(
                    p=record.point_max
                )
