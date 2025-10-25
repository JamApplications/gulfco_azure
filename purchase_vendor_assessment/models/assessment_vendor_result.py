
from odoo import api, fields, models
from .res_partner import VENDOR_DECISION

class AssessmentVendorResult(models.Model):
    _name = "assessment.vendor.result"
    _description = "Assessment Vendor Result"
    _order = "criteria_id"
    _rac_name = "criteria_id"

    # sequence = fields.Integer(default=1)
    name = fields.Char(
        required=True,
        string="Description")
    criteria_id = fields.Many2one(
        comodel_name="assessment.criteria",
        required=True
    )
    criteria_domain = fields.Char(default="[]")
    note = fields.Text()
    # decision = fields.Selection(VENDOR_DECISION, help="""
    #     If the vendor is "Stategy Partnership" but the decision is
    #     not "Make As Strategy Partnership", the vendor will not be
    #     Stategy Partnership anymore"
    #     """, default="0"
    # )

    # status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status')
    # score = fields.Float()
    # weightage_point = fields.Float()
    # point_scored = fields.Float()
