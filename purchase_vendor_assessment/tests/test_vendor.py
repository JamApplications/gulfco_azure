##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################
from datetime import date, timedelta
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.exceptions import AccessError, ValidationError, UserError
from .test_common import TestCommon


@tagged('-at_install', 'post_install')
class TestVendor(TestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.po2 = cls.po.copy()
        cls.po3 = cls.po.copy()
        cls.po4 = cls.po.copy()
        cls.po5 = cls.po.copy()
        cls.po6 = cls.po.copy()
        cls.ass_below_average = cls.env["assessment.purchase"].create({
            "purchase_id": cls.po2.id
        })
        cls.ass_average = cls.env["assessment.purchase"].create({
            "purchase_id": cls.po3.id
        })
        cls.ass_good = cls.env["assessment.purchase"].create({
            "purchase_id": cls.po4.id
        })
        cls.ass_very_good = cls.env["assessment.purchase"].create({
            "purchase_id": cls.po5.id
        })
        cls.assessment_excellent = cls.env["assessment.purchase"].create({
            "purchase_id": cls.po6.id
        })
        cls.vendor_result_1 = cls.env["assessment.vendor.result"].create({
            "sequence": 1,
            "name": "Keep buying and mark as a Strategy Partnership",
            "criteria": "['&', '&', '&', ['x_result_5', '=', 0], ['x_result_4', '=', 0], ['x_result_3', '=', 0], ['x_result_1', '>=', 0.05]]",
            "decision": "1",
        })
        cls.vendor_result_2 = cls.env["assessment.vendor.result"].create({
            "sequence": 2,
            "name": "Keep buying",
            "criteria": "['&', '&', ['x_result_5', '=', 0], ['x_result_4', '=', 0], ['order_count', '>=', 1]]",
            "decision": "0",
        })
        cls.vendor_result_3 = cls.env["assessment.vendor.result"].create({
            "sequence": 3,
            "name": "Warning and looking for the alternative vendor",
            "criteria": "['&', ['order_count', '>', 0], ['x_result_5', '<', 0.1]]",
            "decision": "2",
        })
        cls.vendor_result_4 = cls.env["assessment.vendor.result"].create({
            "sequence": 4,
            "name": "Stop buying",
            "criteria": "[['x_result_5', '>=', 0.1]]",
            "decision": "3",
        })
        cls.vendor_result_5 = cls.env["assessment.vendor.result"].create({
            "sequence": 5,
            "name": "Default",
            "criteria": "[]",
            "decision": "0",
        })
        cls.vendor_assessments = (cls.ass_below_average | cls.ass_average | \
                       cls.ass_good | cls.ass_very_good | cls.assessment_excellent)
        cls.process_purchase_assessments(cls, cls.vendor_assessments)
        cls.vendor_assessment = cls.env["assessment.vendor"].create({
            "partner_id": cls.partner_a.id,
            "date_from": date.today() - timedelta(days=10),
            "date_to": date.today()
        })

    def process_purchase_assessments(self, assessments):
        assessments.action_start()
        assessments.action_submit()
        assessments.action_approve()

    def do_action(self, assessments, level=1):
        assessments.action_load()
        if level > 1:
            assessments.action_submit()
        if level > 2:
            assessments.action_approve()

    def test_template(self):
        self.assertEqual(self.vendor_assessment.template_id, self.template_default)
        self.vendor_assessment.partner_id.category_id = self.categor_1
        self.vendor_assessment._compute_template()
        self.assertEqual(self.vendor_assessment.template_id, self.template_1)

    def test_dates(self):
        with self.assertRaises(ValidationError):
            self.vendor_assessment.date_from = self.vendor_assessment.date_to + timedelta(days=2)
        self.vendor_assessment.action_cancel()
        self.vendor_assessment.copy()
        with self.assertRaises(ValidationError):
            self.vendor_assessment.action_reset()

    def test_action_load(self):
        self.vendor_assessment.action_load()
        self.assertEqual(len(self.vendor_assessment.assessment_purchase_ids), 5)
        self.assertEqual(len(self.vendor_assessment.result_ratio_ids), 5)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[0].count, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[1].count, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[2].count, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[3].count, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[4].count, 5)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[0].ratio, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[1].ratio, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[2].ratio, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[3].ratio, 0)
        self.assertEqual(self.vendor_assessment.result_ratio_ids[4].ratio, 1)

    def test_action_submit(self):
        self.do_action(self.vendor_assessment, 2)
        self.assertTrue(self.vendor_assessment.domain_id)
        self.assertEqual(self.vendor_assessment.domain_id.order_count, 5)
        self.assertEqual(self.vendor_assessment.domain_id.x_result_5, 1)
        self.assertFalse(self.vendor_assessment.domain_id.x_result_1)
        self.assertFalse(self.vendor_assessment.domain_id.x_result_2)
        self.assertFalse(self.vendor_assessment.domain_id.x_result_2)
        self.assertFalse(self.vendor_assessment.domain_id.x_result_4)
        self.assertEqual(self.vendor_assessment.state, "waiting")
        self.assertEqual(self.vendor_assessment.result_id, self.vendor_result_4)

    def test_action_approve(self):
        self.do_action(self.vendor_assessment, 3)
        self.assertEqual(self.vendor_assessment.state, "done")
        self.assertEqual(self.vendor_assessment.partner_id.vendor_decision,
                         self.vendor_assessment.result_id.decision)

    def test_action_refuse(self):
        action = self.vendor_assessment.action_refuse()
        self.assertFalse(action["context"]["active_id"])
        # retry
        self.do_action(self.vendor_assessment, 2)
        action = self.vendor_assessment.action_refuse()
        reason = self.env[action["res_model"]].with_context(action["context"]).create({
            "reason": "test refuse"
        })
        reason.action_reason_apply()
        self.assertEqual(self.vendor_assessment.state, "refused")

    def test_action_cancel_and_reset(self):
        self.do_action(self.vendor_assessment, 2)
        self.assertTrue(self.vendor_assessment.domain_id)
        self.vendor_assessment.action_cancel()
        self.assertEqual(self.vendor_assessment.state, "canceled")
        self.assertFalse(self.vendor_assessment.domain_id)
        self.assertTrue(self.vendor_assessment.result_id)
        self.vendor_assessment.action_reset()
        self.assertEqual(self.vendor_assessment.state, "draft")
        self.assertFalse(self.vendor_assessment.result_id)

    def test_unlink(self):
        self.do_action(self.vendor_assessment, 3)
        with self.assertRaises(AccessError):
            self.vendor_assessment.unlink()

    @users('demo')
    def test_group_approver(self):
        self.do_action(self.vendor_assessment, 2)
        with self.assertRaises(UserError):
            self.vendor_assessment.with_user(self.env.user).action_approve()

    def test_submit_result_1(self):
        self.vendor_assessments.update({"result_id": self.purchase_result_1})
        self.do_action(self.vendor_assessment, 2)
        self.assertEqual(self.vendor_assessment.result_id, self.vendor_result_1)

    def test_submit_result_2(self):
        self.vendor_assessments.update({"result_id": self.purchase_result_3})
        self.do_action(self.vendor_assessment, 2)
        self.assertEqual(self.vendor_assessment.result_id, self.vendor_result_2)

    def test_submit_result_3(self):
        self.vendor_assessments.update({"result_id": self.purchase_result_3})
        i = 0
        while i < 10:
            i += 1
            new_po = self.po.copy()
            new_assessment = self.env["assessment.purchase"].create({
                "purchase_id": new_po.id
            })
            self.process_purchase_assessments(new_assessment)
            new_assessment.update({"result_id": self.purchase_result_3})
        self.vendor_assessments[0].result_id = self.purchase_result_5
        self.do_action(self.vendor_assessment, 2)
        self.assertEqual(self.vendor_assessment.result_id, self.vendor_result_3)
