# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression

import logging
import random
import math
import pytz

from collections import defaultdict, Counter
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from functools import reduce

from odoo.tools import float_round, date_utils, convert_file, format_amount
from odoo.tools.float_utils import float_compare
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval, datetime as safe_eval_datetime, dateutil as safe_eval_dateutil


# class DefaultDictPayroll(defaultdict):
#     def get(self, key, default=None):
#         if key not in self and default is not None:
#             self[key] = default
#         return self[key]




class AssessmentVendor(models.Model):
    _name = "assessment.vendor"
    _inherit = "mail.thread"
    _description = "Assessment Vendor"

    display_name = fields.Char('Display Name', compute="_compute_display_name")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        tracking=True,
    )
    date_from = fields.Date(
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        required=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
    )

    assessment_criteria_ids = fields.One2many(
        comodel_name="assessment.criteria.line", inverse_name='assessment_id', ondelete='cascade'
    )
    assessment_purchase_ids = fields.Many2many(
        comodel_name="assessment.purchase", ondelete='cascade'
    )
    result_ratio_ids = fields.One2many(
        comodel_name="assessment.purchase.result.ratio",
        inverse_name="assessment_id"
    )
    state = fields.Selection([
        ("draft", "Draft"),
        ("waiting", "To Approve"),
        ("done", "Released"),
        ("refused", "Refused"),
        ("canceled", "Canceled")
    ], default="draft", tracking=True, copy=False,)
    # result_id = fields.Many2one(
    #     comodel_name="assessment.vendor.result",
    #     tracking=True,
    #     copy=False,
    # )
    notes = fields.Text()
    domain_id = fields.Many2one(
        comodel_name="assessment.vendor.domain",
        copy=False,
    )
    # template_id = fields.Many2one(
    #     comodel_name="assessment.purchase.template",
    #     compute="_compute_template",
    #     readonly=False,
    #     store=True,
    #     tracking=True,
    #     copy=False
    # )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True, readonly=True,
        default=lambda self: self.env.company
    )

    @api.constrains("date_from", "date_to", "state", "partner_id")
    def _check_dates(self):
        """
        Check date_to > date_from and not overlap
        """
        for record in self:
            if record.date_from and record.date_to and \
                    record.date_from > record.date_to:
                raise ValidationError(
                    _("Date To must be greater than Date From."))
            # Check overlapped
            args = [
                ("date_from", "<=", record.date_to),
                ("date_to", ">=", record.date_from),
                ("state", "not in", ("canceled", "refused")),
                ("partner_id", "=", record.partner_id.id),
                ("id", "!=", record.id)
            ]
            exist = self.search(args, limit=1)
            if exist:
                raise ValidationError(
                    _("This assessment is overlapped with {}").format(
                        exist.display_name
                    )
                )

    @api.depends('partner_id', 'date_from')
    def _compute_display_name(self):
        for record in self:
            name_lst = []
            if record.partner_id:
                name_lst.append(record.partner_id.display_name)
            if record.date_from:
                name_lst.append(fields.Date.to_string(record.date_from))
            name = ""
            if name_lst:
                name = ": ".join(name_lst)
            record.display_name = name

    # @api.depends("partner_id")
    # def _compute_template(self):
    #     templates = self.env["assessment.purchase.template"].search([])
    #     default_template = templates.filtered(
    #         lambda t: not t.partner_categ_ids)
    #     for record in self:
    #         catgs = record.partner_id.category_id
    #         tmpl = templates.filtered(lambda t: t.partner_categ_ids == catgs)
    #         if not tmpl:
    #             tmpl = templates.filtered(lambda t: t.partner_categ_ids & catgs)
    #         if not tmpl:
    #             tmpl = default_template
    #         record.template_id = tmpl and tmpl[0] or tmpl

    def action_load(self):
        """ Load All the purchase order with an assessment with define criteria and get the result"""
        records = self.filtered(lambda r: r.state == "draft")
        for record in records:

            confirmed_po = self.env['purchase.order'].search([
                ('partner_id', '=', record.partner_id.id),
                ('state', 'in', ['purchase', 'done']),
                ('date_order', '>=', record.date_from),
                ('date_order', '<=', record.date_to)
            ])
            print("confirm order fdhjdf:", confirmed_po, confirmed_po)

            purchase_assessment_list = []
            # for po in confirmed_po:
            #     pass

            # if record.partner_id.criteria_ids:
            #     vendor_criteria = record.partner_id.criteria_ids

            if record.partner_id.criteria_id:
                vendor_criteria = record.partner_id.criteria_id

                if not vendor_criteria:
                    record.assessment_criteria_ids = None
                    continue
                if record.assessment_criteria_ids:
                    record.assessment_criteria_ids.unlink()
                if not record.assessment_criteria_ids:
                    for crt in vendor_criteria:
                        record.write({
                            'assessment_criteria_ids':[(0,0, {
                                'criteria_id': crt.id,
                                'partner_id': record.partner_id.id,
                                'company_id': record.company_id.id,
                                'user_id': record.user_id.id,
                                # 'score': 100,
                                'weightage_point': crt.weightage_point
                            })]
                        })

                    for ass in record.assessment_criteria_ids:
                        for po in confirmed_po:
                            ass.write({
                                'purchase_assessment_lines': [(0,0, {
                                    'purchase_id': po.id,
                                    'criteria_id': ass.criteria_id.id,
                                    'weightage_point': ass.weightage_point,
                                })]
                            })
                        for psl in ass.purchase_assessment_lines:
                            psl.calculate_purchase_assessment()
                        ass._compute_point_scored()

            elif record.partner_id.criteria_group_id:
                vendor_group_criteria = record.partner_id.criteria_group_id

                if not vendor_group_criteria:
                    record.assessment_criteria_ids = None
                    continue

                if record.assessment_criteria_ids:
                    record.assessment_criteria_ids.unlink()
                if not record.assessment_criteria_ids:
                    for crt_grp in vendor_group_criteria.criteria_group_line:
                        record.write({
                            'assessment_criteria_ids': [(0, 0, {
                                'criteria_id': crt_grp.criteria_id.id,
                                'partner_id': record.partner_id.id,
                                'company_id': record.company_id.id,
                                'user_id': record.user_id.id,
                                # 'score': 100,
                                'weightage_point': crt_grp.weightage_point
                            })]
                        })

                    for ass in record.assessment_criteria_ids:
                        for po in confirmed_po:
                            ass.write({
                                'purchase_assessment_lines': [(0, 0, {
                                    'purchase_id': po.id,
                                    'criteria_id': ass.criteria_id.id,
                                    'weightage_point': ass.weightage_point,
                                })]
                            })
                        for psl in ass.purchase_assessment_lines:
                            psl.calculate_purchase_assessment()
                        ass._compute_point_scored()


            else:
                raise ValidationError("Criteria not Define in this Vendor")




    def _add_domain(self):
        AssDomain = self.env["assessment.vendor.domain"]
        for record in self:
            vals = {}
            for ratio in record.result_ratio_ids:
                if not ratio.result_id.res_field:
                    continue
                vals[ratio.result_id.res_field] = ratio.ratio
            if vals:
                vals["order_count"] = sum(
                    record.result_ratio_ids.mapped("count"))
                domain = AssDomain.create(vals)
                record.domain_id = domain

    def _unlink_domain(self):
        domains = self.mapped("domain_id")
        if domains:
            domains.unlink()

    def _search_result(self):
        AssDomain = self.env["assessment.vendor.domain"]
        available_rs = self.env["assessment.vendor.result"].search([
            ("criteria_domain", "!=", False)
        ])
        for result in available_rs:
            args = safe_eval(result.criteria_domain)
            for record in self:
                # if not record.domain_id or record.result_id:
                #     continue
                domain = expression.AND(
                    [args, [("id", "=", record.domain_id.id)]])
                found = AssDomain.search(domain, limit=1)
                # if found:
                #     record.result_id = result

    def action_submit(self):
        if not self.assessment_criteria_ids:
            raise ValidationError("%s don't have any criteria or please load the criteria before submit" % (self.partner_id.display_name))
        records = self.filtered(lambda r: r.state == "draft")
        records._add_domain()
        records._search_result()
        # records = records.filtered(lambda r: r.result_id)
        records.update({"state": "waiting"})

    def action_approve(self):
        self.check_approver()
        records = self.filtered(lambda r: r.state == "waiting")
        records.update({"state": "done"})
        for record in records:
            assessments = record.partner_id.vendor_assessment_ids.filtered(
                lambda r: r.state == "done").sorted("date_to")
            if not assessments:
                continue
            assessment = assessments[-1]  # Get the latest one
            # record.partner_id.vendor_decision = assessment.result_id.decision

    def action_refuse(self):
        self.check_approver()
        records = self.filtered(lambda r: r.state == "waiting")
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "purchase_vendor_assessment.refused_reason_action"
        )
        action["context"] = {
            "active_id": records and records[0].id,
            "active_ids": records.ids,
            "active_model": records._name
        }
        return action

    def action_reset(self):
        records = self.filtered(lambda r: r.state in ("canceled", "refused"))
        records.update({"state": "draft", })
        # "result_id": False})

    def action_cancel(self):
        records = self.filtered(lambda r: r.state in ("draft", "wip", "waiting"))
        records._unlink_domain()
        records.update({"state": "canceled"})

    def set_refused(self, reason=""):
        self.check_approver()
        records = self.filtered(lambda r: r.state == "waiting")
        records.update({
            "state": "refused"
        })
        if reason:
            msg = _('I refused due to this reason: {}'.format(reason))
            records.message_post(body=msg)

    def check_approver(self):
        if not self.env.user.has_group(
            "purchase_vendor_assessment.group_assessment_approver"):
            raise UserError(_("You have no right"))


    # Rules for criteria calcualtion

    # def _get_base_local_dict(self):
    #     return {
    #         'float_round': float_round,
    #         'float_compare': float_compare,
    #         'relativedelta': safe_eval_dateutil.relativedelta.relativedelta,
    #         'ceil': math.ceil,
    #         'floor': math.floor,
    #         'UserError': UserError,
    #         'date': safe_eval_datetime.date,
    #         'datetime': safe_eval_datetime.datetime,
    #         'defaultdict': defaultdict,
    #     }

    # def _get_localdict(self):
    #     self.ensure_one()
    #     # Check for multiple inputs of the same type and keep a copy of
    #     # them because otherwise they are lost when building the dict
    #     # input_list = [line.code for line in self.input_line_ids if line.code]
    #     # cnt = Counter(input_list)
    #     # multi_input_lines = [k for k, v in cnt.items() if v > 1]
    #     # same_type_input_lines = {line_code: [line for line in self.input_line_ids if line.code == line_code] for
    #     #                          line_code in multi_input_lines}
    #     localdict = {
    #         **self._get_base_local_dict(),
    #         **{
    #             'vednor_assesment': self,
    #             'purchase': {line.purchase_id.name: line.purchase_id for line in self.assessment_criteria_ids},
    #             'vendore': self.partner_id,
    #             'criteria': {line.criteria_id.name: line.criteria_id for line in self.assessment_criteria_ids},
    #             # 'asn':'',
    #             # 'purchase_line': '',
    #
    #             # 'categories': DefaultDictPayroll(lambda: 0),
    #             # 'rules': DefaultDictPayroll(lambda: dict(total=0, amount=0, quantity=0)),
    #             # 'payslip': self,
    #             # 'worked_days': {line.code: line for line in self.worked_days_line_ids if line.code},
    #             # 'inputs': {line.code: line for line in self.input_line_ids if line.code},
    #             # 'employee': self.employee_id,
    #             # 'contract': self.contract_id,
    #             # 'result_rules': DefaultDictPayroll(lambda: dict(total=0, amount=0, quantity=0, rate=0)),
    #             # 'same_type_input_lines': same_type_input_lines,
    #         }
    #     }
    #     return localdict

    # def get_assessment_lines(self):
    #     line_vals = []
    #
    #
    #     # line_values = ytd_payslips._get_line_values(code_set, ['ytd'])
    #
    #     for rec in self:
    #         # if not rec:
    #         #     raise UserError(_("There's no contract set on payslip %(payslip)s for %(employee)s. Check that there is at least a contract set on the employee form.", payslip=payslip.name, employee=payslip.employee_id.name))
    #
    #         localdict = self.env.context.get('force_payslip_localdict', None)
    #         if localdict is None:
    #             localdict = rec._get_localdict()
    #
    #         # rules_dict = localdict['rules']
    #         # result_rules_dict = localdict['result_rules']
    #         #
    #         # blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])
    #
    #         result = {}
    #         for line in rec.assessment_criteria_ids:
    #             print('====>', line.criteria_id._compute_rule(localdict))
    #             result.update({self.partner_id.name:line.criteria_id._compute_rule(localdict)})
    #
    #         print("rsult:----:", result)
