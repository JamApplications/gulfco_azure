
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AssessmentCriteriaiLine(models.Model):
    _name = "assessment.criteria.line"
    _description = "Assessment Criteria Lines"
    _rec_name= "criteria_id"
    _order = "criteria_id"

    criteria_id = fields.Many2one(
        comodel_name="assessment.criteria",
        required=True
    )
    assessment_id = fields.Many2one('assessment.vendor', ondelete="cascade")
    purchase_assessment_lines = fields.One2many('assessment.purchase', 'assessment_line_id')

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        # required=True,
        tracking=True,
        copy=False
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="purchase_id.partner_id",
        store=True,
        copy=False
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True, readonly=True,
        default=lambda self: self.env.company
    )

    # Fields to be add as per request
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status')
    score = fields.Float()
    weightage_point = fields.Float()
    point_scored = fields.Float(compute='_compute_point_scored')

    def _compute_point_scored(self):
        for rec in self:
            if rec.purchase_assessment_lines:
                rec.score = sum(rec.purchase_assessment_lines.mapped('score'))/len(rec.purchase_assessment_lines)
            else:
                rec.score = 0
            rec.point_scored = (rec.score * rec.weightage_point) or 0.0


            total_orders = len(rec.purchase_assessment_lines)
            pass_count = sum(1 for o in rec.purchase_assessment_lines if o.status == 'pass')
            fail_count = total_orders - pass_count  # Since total = pass + fail

            # Determine the average result based on the counts
            if total_orders > 0:
                if pass_count >= fail_count:
                    rec.status = 'pass'
                else:
                    rec.status = 'fail'
            else:
                rec.status = False  # No relevant orders


    def open_po(self):
        '''
        Get PO details that match with criteria
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_vendor_assessment.assessment_purchase_action")
        action['views'] = [[False, 'list']]
        action['domain'] = [('criteria_id', '=', self.criteria_id.id),('assessment_line_id', '=', self.id)]
        action['context'] = {
            'default_assessment_line_id': self.id
        }
        return action
