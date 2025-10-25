
from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class AssessmentCriteriaGroup(models.Model):
    _name = "assessment.criteria.group"
    _description = "Assessment Criteria group"
    _order = "name"

    name = fields.Char(required=True)
    criteria_ids = fields.Many2many('assessment.criteria', required=True, compute='_compute_criteria_ids', store=True)


    weightage_point = fields.Float(required=True, )
    vendor_ids = fields.One2many('res.partner', 'criteria_group_id')
    criteria_group_line = fields.One2many('assessment.criteria.group.line', 'criteria_group_id', required=True)

    @api.depends('criteria_group_line', 'criteria_group_line.criteria_id', 'criteria_group_line.weightage_point')
    def _compute_criteria_ids(self):
        for rec in self:
            rec.criteria_ids = None
            rec.weightage_point = 0
            for crt in rec.criteria_group_line:
                rec.criteria_ids = [(4, crt.criteria_id.id)]
                rec.weightage_point += crt.weightage_point


    @api.constrains("weightage_point", "criteria_group_line", "criteria_group_line.weightage_point")
    def _check_criteria_weightage_point(self):
        for rec in self:
            fix_weightage_point = 100.0
            if fix_weightage_point != sum(rec.criteria_group_line.mapped('weightage_point')):
                raise ValidationError(_(
                    "The weightage point must be equal to the %s (Criteria Weightage Points).",
                    fix_weightage_point
                ))


class AssessmentCriteriaGroupLine(models.Model):
    _name = "assessment.criteria.group.line"
    _description = "Assessment Criteria Group Line"
    _order = "criteria_id"

    criteria_group_id = fields.Many2one('assessment.criteria.group', ondelete="cascade",)
    criteria_id = fields.Many2one('assessment.criteria', required=True)
    weightage_point = fields.Float(required=True)




