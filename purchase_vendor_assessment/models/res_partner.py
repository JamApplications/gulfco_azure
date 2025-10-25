# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError

VENDOR_DECISION = [
    ("0", "Do Nothing"),
    ("1", "Mark As Strategy Partnership"),
    ("2", "Warning"),
    ("3", "Stop The Partnership")
]
class Partner(models.Model):
    _inherit = "res.partner"

    vendor_decision = fields.Selection(
        VENDOR_DECISION,
        tracking=True,
        copy=False,
    )


    criteria_id = fields.Many2one(
        comodel_name="assessment.criteria",
        string='Vendor Evaluation parameters')

    #
    # criteria_ids = fields.Many2many(
    #     comodel_name="assessment.criteria",
    #     relation="partner_criteria_assessment_rel",
    #     string='Vendor Evaluation parameters'
    # )

    criteria_group_id = fields.Many2one('assessment.criteria.group')

    @api.constrains('criteria_group_id', 'criteria_id')
    def _check_exclusive_criteria_fields(self):
        for record in self:
            if record.criteria_group_id and record.criteria_id:
                raise ValidationError(
                    "Please set either 'Criteria Group' or 'Vendor Evaluation Parameters', not both."
                )

    @api.onchange('criteria_group_id', 'criteria_id')
    def onchange_criteria_id(self):
        if self.criteria_group_id:
            self.criteria_id = None
        elif self.criteria_id:
            self.criteria_group_id = None


    vendor_assessment_ids = fields.One2many(
        comodel_name="assessment.vendor",
        inverse_name="partner_id"
    )
    vendor_assessment_count = fields.Integer(
        compute="_compute_assessment_count"
    )

    def _compute_assessment_count(self):
        for record in self:
            assessments = record.vendor_assessment_ids.filtered(
                lambda r: r.state == "done")
            record.vendor_assessment_count = len(assessments)

    def action_open_assessments(self):
        assessments = self.mapped("vendor_assessment_ids").filtered(
            lambda r: r.state == "done")
        return {
            'name': _('Related Assessments'),
            'type': 'ir.actions.act_window',
            'res_model': 'assessment.vendor',
            'view_mode': 'list,form',
            'domain': [('id', 'in', assessments.ids)],
        }
