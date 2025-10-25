##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################
from odoo.tests import tagged
from odoo.exceptions import AccessError, ValidationError
from .test_common import TestCommon


@tagged('-at_install', 'post_install')
class TestPurchase(TestCommon):

    def test_template(self):
        self.assertEqual(self.assessment.template_id, self.template_default)
        self.assessment.partner_id.category_id = self.categor_1
        self.assessment._compute_template()
        self.assertEqual(self.assessment.template_id, self.template_1)

    def test_duplicate(self):
        with self.assertRaises(ValidationError):
            assessment = self.assessment.copy({
                "purchase_id": self.assessment.purchase_id.id
            })
        self.assessment.action_cancel()
        self.assertEqual(self.po.assessment_purchase_id, self.assessment)
        self.assertEqual(self.po.assessment_purchase_state, "canceled")
        assessment = self.assessment.copy({
            "purchase_id": self.assessment.purchase_id.id
        })
        self.assertTrue(assessment)
        self.assertEqual(self.po.assessment_purchase_id, assessment)
        self.assertEqual(self.po.assessment_purchase_state, "draft")

    def test_action_start(self):
        self.assessment.action_start()
        self.assertEqual(self.assessment.state, "wip")
        self.assertEqual(self.po.assessment_purchase_state, "wip")
        criterias = self.assessment.line_ids.mapped("criteria_id.id").sort()
        criterias_2 = self.template_default.line_ids.mapped("criteria_id.id").sort()
        self.assertEqual(criterias, criterias_2)
        with self.assertRaises(ValidationError):
            self.assessment.line_ids[0].point = 50
        with self.assertRaises(ValidationError):
            self.assessment.line_ids[0].point = -1

    def test_action_submit(self):
        self.assessment.action_submit()
        self.assertEqual(self.assessment.state, "draft")
        self.assessment.action_start()
        self.assessment.line_ids.update({"point": 10})
        self.assertEqual(self.assessment.point, 50)
        self.assessment.action_submit()
        self.assertEqual(self.assessment.state, "waiting")
        self.assertEqual(self.assessment.result_id, self.purchase_result_4)

    def test_action_submit2(self):
        self.assessment.action_start()
        self.assessment.template_id.result_ids = None
        with self.assertRaises(ValidationError):
            self.assessment.action_submit()

    def test_action_approve(self):
        self.assessment.action_start()
        self.assessment.line_ids.update({"point": 10})
        self.assessment.action_approve()
        self.assertEqual(self.assessment.state, "wip")
        self.assessment.action_submit()
        self.assessment.action_approve()
        self.assertEqual(self.assessment.state, "done")

    def test_action_refuse(self):
        self.assessment.action_start()
        self.assessment.line_ids.update({"point": 10})
        action = self.assessment.action_refuse()
        self.assertFalse(action["context"]["active_id"])
        # retry
        self.assessment.action_submit()
        action = self.assessment.action_refuse()
        reason = self.env[action["res_model"]].with_context(action["context"]).create({
            "reason": "test refuse"
        })
        reason.action_reason_apply()
        self.assertEqual(self.assessment.state, "refused")

    def test_action_cancel(self):
        self.assessment.action_cancel()
        self.assertEqual(self.assessment.state, "canceled")
        self.assessment.action_reset()
        self.assertEqual(self.assessment.state, "draft")
        self.assessment.action_cancel()
        new = self.assessment.copy({
            "purchase_id": self.assessment.purchase_id.id})
        with self.assertRaises(ValidationError):
            self.assessment.action_reset()
        new.action_start()
        new.action_submit()
        new.action_approve()
        new.action_cancel()
        self.assertEqual(self.assessment.state, "canceled")

    def test_unlink(self):
        self.assessment.action_start()
        self.assessment.line_ids.update({"point": 10})
        self.assessment.action_submit()
        self.assessment.action_approve()
        with self.assertRaises(AccessError):
            self.assessment.unlink()
