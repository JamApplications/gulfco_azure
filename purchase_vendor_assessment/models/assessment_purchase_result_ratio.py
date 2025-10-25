# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _


class AssessmentPOResultRatio(models.Model):
    _name = "assessment.purchase.result.ratio"
    _description = "Assessment Purchase Result Ratio"
    _order = "sequence"

    sequence = fields.Integer(default=1)
    result_id = fields.Many2one(
        comodel_name="assessment.purchase.result"
    )
    assessment_id  = fields.Many2one(
        comodel_name="assessment.vendor",
    )
    count = fields.Integer()
    ratio = fields.Float()
