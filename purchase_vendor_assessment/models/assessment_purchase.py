
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from functools import reduce
import logging
import random
import math
import pytz

from collections import defaultdict, Counter
from odoo.tools import float_round, date_utils, convert_file, format_amount
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval, datetime as safe_eval_datetime, dateutil as safe_eval_dateutil



class AssessmentPurchase(models.Model):
    _name = "assessment.purchase"
    _description = "Assessment Purchase"
    _rec_name= "purchase_id"
    _order = "purchase_id"

    assessment_line_id = fields.Many2one(comodel_name='assessment.criteria.line', ondelete="cascade",)

    criteria_id = fields.Many2one(
        comodel_name="assessment.criteria",
    )

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        # inverse="_inverse_purchase_id",
        required=True,
        tracking=True,
        copy=False
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="purchase_id.partner_id",
        store=True,
        copy=False
    )

    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Result')
    score = fields.Float()
    weightage_point = fields.Float()
    point_scored = fields.Float(compute='_compute_point_scored')


    def _compute_point_scored(self):
        for rec in self:
            # rec.purchase_id.ETA_score = None
            rec.point_scored = (rec.score * rec.weightage_point) or 0.0
            # rec.purchase_id.ETA_score = rec.point_scored

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True, readonly=True,
        default=lambda self: self.env.company
    )

    # rdd_days = fields.Float()  # RDD criteria result store

    # partner_categ_ids = fields.Many2many(
    #     comodel_name="res.partner.category",
    #     string="Vendor Tags",
    #     related="partner_id.category_id"
    # )
    # assessment_date = fields.Date(
    #     string="Date",
    #     default=fields.Date.today,
    #     required=True,
    #     tracking=True,
    #     copy=False
    # )
    # user_id = fields.Many2one(
    #     comodel_name="res.users",
    #     required=True,
    #     default=lambda self: self.env.user,
    # )
    # point = fields.Integer(
    #     compute="_compute_point",
    #     store=True,
    #     copy=False
    # )
    # result_id = fields.Many2one(
    #     comodel_name="assessment.purchase.result",
    #     copy=False
    # )
    # color = fields.Char(
    #     related="result_id.color"
    # )
    # line_ids = fields.One2many(
    #     comodel_name="assessment.purchase.line",
    #     inverse_name="assessment_id",
    #     copy=False
    # )
    # state = fields.Selection([
    #     ("draft", "Draft"),
    #     ("wip", "In progress"),
    #     ("waiting", "To Approve"),
    #     ("done", "Released"),
    #     ("refused", "Refused"),
    #     ("canceled", "Canceled")
    # ], default="draft", tracking=True, copy=False)
    # notes = fields.Text()
    # template_id = fields.Many2one(
    #     comodel_name="assessment.purchase.template",
    #     compute="_compute_template",
    #     readonly=False,
    #     store=True,
    #     tracking=True,
    #     copy=False
    # )
    # company_id = fields.Many2one(
    #     comodel_name="res.company",
    #     required=True, readonly=True,
    #     default=lambda self: self.env.company
    # )
    #
    # @api.depends("purchase_id")
    # def _compute_template(self):
    #     templates = self.env["assessment.purchase.template"].search([])
    #     default_template = templates.filtered(
    #         lambda t: not t.partner_categ_ids)
    #     for record in self:
    #         catgs = record.purchase_id.partner_id.category_id
    #         tmpl = templates.filtered(lambda t: t.partner_categ_ids == catgs)
    #         if not tmpl:
    #             tmpl = templates.filtered(lambda t: t.partner_categ_ids & catgs)
    #         if not tmpl:
    #             tmpl = default_template
    #         record.template_id = tmpl and tmpl[0] or tmpl
    #
    # @api.depends("line_ids", "line_ids.point")
    # def _compute_point(self):
    #     for record in self:
    #         record.point = sum(record.line_ids.mapped("point"))
    #
    # def _inverse_purchase_id(self):
    #     Purchase = self.env["purchase.order"]
    #     old = Purchase.search([("assessment_purchase_id", "in", self.ids)])
    #     old.update({"assessment_purchase_id": None})
    #     for record in self:
    #         if record.purchase_id:
    #             record.purchase_id.sudo().assessment_purchase_id = record
    #
    # def action_start(self):
    # #     Line = self.env["assessment.purchase.line"]
    #     records = self.filtered(
    #         lambda r: r.state == "draft")
    # # and r.template_id)
    # #     for record in records:
    # #         record.line_ids = None
    # #         for line_tmpl in record.template_id.line_ids:
    # #             line = Line.new()
    # #             line.assessment_id = record
    # #             line.criteria_id = line_tmpl.criteria_id
    # #             line.point_min = line_tmpl.point_min
    # #             line.point_max = line_tmpl.point_max
    # #             line.sequence = line_tmpl.sequence
    # #             vals = Line._convert_to_write(line._cache)
    # #             Line.create(vals)
    #     records.update({"state": "wip"})
    #
    # def action_submit(self):
    #     records = self.filtered(lambda r: r.state == "wip")
    #     for record in records:
    # #         template_results = record.template_id.result_ids.\
    # #             sorted("point_max")
    # #         if not template_results:
    # #             raise ValidationError(
    # #                 _("No available result defined in the template"))
    # #         results = template_results.\
    # #             filtered(lambda r: r.point_max > record.point)
    # #         record.result_id = (results and results[0] or
    # #                             template_results[-1]).result_id
    #         record.state = "waiting"
    #
    # def action_approve(self):
    #     self.check_approver()
    #     records = self.filtered(lambda r: r.state == "waiting")
    #     records.update({"state": "done"})
    #
    # def action_refuse(self):
    #     self.check_approver()
    #     records = self.filtered(lambda r: r.state == "waiting")
    #     action = self.env["ir.actions.act_window"]._for_xml_id(
    #         "purchase_vendor_assessment.refused_reason_action"
    #     )
    #     action["context"] = {
    #         "active_id": records and records[0].id,
    #         "active_ids": records.ids,
    #         "active_model": records._name
    #     }
    #     return action
    #
    # def action_reset(self):
    #     records = self.filtered(lambda r: r.state in ("canceled", "refused"))
    #     # exists = self.search([
    #     #     ("purchase_id", "in", records.mapped("purchase_id.id")),
    #     #     ("id", "not in", records.ids)
    #     # ], limit=1)
    #     # if exists:
    #     #     raise ValidationError(
    #     #         _("This Order has been assessed."))
    #     records.update({"state": "draft", "result_id": False})
    #
    # def action_cancel(self):
    #     records = self.filtered(lambda r: r.state in ("draft", "wip", "waiting"))
    #     records.update({"state": "canceled"})
    #
    # def set_refused(self, reason=""):
    #     self.check_approver()
    #     records = self.filtered(lambda r: r.state == "waiting")
    #     records.update({
    #         "state": "refused"
    #     })
    #     if reason:
    #         msg = _('I refused due to this reason: {}'.format(reason))
    #         records.message_post(body=msg)
    #
    # def check_approver(self):
    #     if not self.env.user.has_group(
    #         "purchase_vendor_assessment.group_assessment_approver"):
    #         raise UserError(_("You have no right"))

    # @api.constrains("criteria_id", "state")
    # def _check_criteria_id(self):
    #     if not self:
    #         return
    #
    #     for record in self:
    #         exist = self.search([
    #             ("criteria_id", "=", record.criteria_id.id),
    #             ("state", "!=", "canceled"),
    #             ("id", "!=", record.id)
    #         ])
    #         if exist:
    #             raise ValidationError(_("This Order has been assessed."))



    def _get_base_local_dict(self):
        return {
            'float_round': float_round,
            'float_compare': float_compare,
            'relativedelta': safe_eval_dateutil.relativedelta.relativedelta,
            'ceil': math.ceil,
            'floor': math.floor,
            'UserError': UserError,
            'date': safe_eval_datetime.date,
            'datetime': safe_eval_datetime.datetime,
            'defaultdict': defaultdict,
        }

    def _get_localdict(self):
        self.ensure_one()
        # Check for multiple inputs of the same type and keep a copy of
        # them because otherwise they are lost when building the dict
        po_line = [line for line in self.purchase_id.order_line if line.product_id]
        # cnt = Counter(input_list)
        # multi_input_lines = [k for k, v in cnt.items() if v > 1]

        asn_object = self.env['asn.request.line'].search([('purchase_order_id','in', [line.order_id.id for line in self.purchase_id.order_line if line.product_id])])

        asn_line = [line for line in asn_object if line.purchase_order_id]

        localdict = {
            **self._get_base_local_dict(),
            **{
                'purchase_assesment': self,
                'purchase': self.purchase_id,
                'vendore': self.partner_id,
                'criteria': self.criteria_id,
                'asn_line': asn_line,
                'purchase_line': po_line,

                # 'categories': DefaultDictPayroll(lambda: 0),
                # 'rules': DefaultDictPayroll(lambda: dict(total=0, amount=0, quantity=0)),
                # 'payslip': self,
                # 'worked_days': {line.code: line for line in self.worked_days_line_ids if line.code},
                # 'inputs': {line.code: line for line in self.input_line_ids if line.code},
                # 'employee': self.employee_id,
                # 'contract': self.contract_id,
                # 'result_rules': DefaultDictPayroll(lambda: dict(total=0, amount=0, quantity=0, rate=0)),
                # 'same_type_input_lines': same_type_input_lines,
            }
        }
        return localdict

    def calculate_purchase_assessment(self):
        line_vals = []


        # line_values = ytd_payslips._get_line_values(code_set, ['ytd'])

        for rec in self:
            # if not rec:
            #     raise UserError(_("There's no contract set on payslip %(payslip)s for %(employee)s. Check that there is at least a contract set on the employee form.", payslip=payslip.name, employee=payslip.employee_id.name))

            localdict = self.env.context.get('force_payslip_localdict', None)
            if localdict is None:
                localdict = rec._get_localdict()

            # rules_dict = localdict['rules']
            # result_rules_dict = localdict['result_rules']
            #
            # blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            res = {}
            print('====>', rec.criteria_id.name, rec.criteria_id._compute_rule(localdict))
            res.update({self.criteria_id.name:rec.criteria_id._compute_rule(localdict)})
            print("rec.score: !:", rec.score)
            print('-->:', rec.criteria_id._compute_rule(localdict))
            # rec.rdd_days = rec.criteria_id._compute_rule(localdict)

            print("rec.score: !!:", rec.score)


            if rec.criteria_id.name in ['RDD']:
                if res['RDD'] <= 0:
                    rec.score = 1
                    rec.status = 'pass'
                elif res['RDD'] > 15:
                    rec.score = 0
                    rec.status = 'fail'
                elif res['RDD'] >= 1 and res['RDD'] <= 15:
                    rec.score =0.8
                    rec.status = 'pass'
            elif rec.criteria_id.name in ['ETA']:
                if res['ETA'] <= 0:
                    rec.score = 1
                    rec.status = 'pass'
                elif res['ETA'] > 15:
                    rec.score = 0
                    rec.status = 'fail'
                elif res['ETA'] >= 1 and res['ETA'] <= 15:
                    rec.score =0.8
                    rec.status = 'pass'

            elif rec.criteria_id.name in ['Case to Fill']:
                if res['Case to Fill']:
                    print("case to fill:",rec.criteria_id.name, '000:', res['Case to Fill'],rec.purchase_id.name, )
                    # print("ETA score:===:",rec.purchase_id.ETA_score)
                    if res['Case to Fill'] > 0:
                        rec.score = res['Case to Fill']
                        rec.status = 'pass'
                    else:
                        rec.score = 0
                        rec.status = 'fail'
                else:
                    rec.score = 0
                    rec.status = 'fail'

            elif rec.criteria_id.name in ['Price Difference']:
                if res['Price Difference'] == True:
                    rec.status = 'pass'
                    rec.score = 1
                else:
                    rec.score = 0
                    rec.status = 'fail'

            elif rec.criteria_id.name in ['Damage']:
                if res['Damage'] == True:
                    rec.score = 0
                    rec.status = 'fail'
                else:
                    rec.score = 1
                    rec.status = 'pass'

            elif rec.criteria_id.name in ['Shortage/Excess']:
                if res['Shortage/Excess'] == True:
                    rec.status = 'fail'
                    rec.score = 0
                else:
                    rec.score = 1
                    rec.status = 'pass'

            elif rec.criteria_id.name in ['Quality Issue']:
                if res['Quality Issue'] == True:
                    rec.status = 'fail'
                    rec.score = 0
                else:
                    rec.score = 1
                    rec.status = 'pass'

            elif rec.criteria_id.name in ['Late Receipt of Document']:
                if res['Late Receipt of Document'] <= 5:
                    rec.score = 0
                    rec.status = 'fail'
                else:
                    rec.score = 1
                    rec.status = 'pass'

            elif rec.criteria_id.name in ['Demurrage & Storage']:
                if res['Demurrage & Storage'] > 0:
                    rec.status = 'fail'
                    rec.score = 0
                else:
                    rec.score = 1
                    rec.status = 'pass'
            else:
                print("In ELSE condition 'res':", res, res[rec.criteria_id.name])
                if res[rec.criteria_id.name]:
                    rec.status = 'pass'
                    rec.score = 1
                else:
                    rec.score = 0
                    rec.status = 'fail'


            print("re==:rES:----:", res)
