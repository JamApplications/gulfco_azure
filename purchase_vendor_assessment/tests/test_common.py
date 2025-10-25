##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################
from odoo.tests import Form, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install')
class TestCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.categor_1 = cls.env["res.partner.category"].create({
            "name": "Category 1"
        })
        cls.categor_2 = cls.env["res.partner.category"].create({
            "name": "Category 2"
        })
        cls.purchase_result_1 = cls.env["assessment.purchase.result"].create([
            {
                "name": "result 1",
                "sequence": 1,
                "code": "result_1"
            }
        ])
        cls.purchase_result_2 = cls.env["assessment.purchase.result"].create([
            {
                "name": "result 2",
                "sequence": 2,
                "code": "result_2"
            }
        ])
        cls.purchase_result_3 = cls.env["assessment.purchase.result"].create([
            {
                "name": "result 3",
                "sequence": 3,
                "code": "result_3"
            }
        ])
        cls.purchase_result_4 = cls.env["assessment.purchase.result"].create([
            {
                "name": "result 4",
                "sequence": 4,
                "code": "result_4"
            }
        ])
        cls.purchase_result_5 = cls.env["assessment.purchase.result"].create([
            {
                "name": "result 5",
                "sequence": 5,
                "code": "result_5"
            }
        ])
        cls.purchase_criteria_1 = cls.env["assessment.criteria"].create([
            {
                "name": "Criteria 1",
                "sequence": 1
            }
        ])
        cls.purchase_criteria_2 = cls.env["assessment.criteria"].create([
            {
                "name": "Criteria 2",
                "sequence": 2
            }
        ])
        cls.purchase_criteria_3 = cls.env["assessment.criteria"].create([
            {
                "name": "Criteria 3",
                "sequence": 3
            }
        ])
        cls.purchase_criteria_4 = cls.env["assessment.criteria"].create([
            {
                "name": "Criteria 4",
                "sequence": 4
            }
        ])
        cls.purchase_criteria_5 = cls.env["assessment.criteria"].create([
            {
                "name": "Criteria 5",
                "sequence": 5
            }
        ])
        cls.template_default = cls.env["assessment.purchase.template"].create({
            "name": "default",
            "sequence": -1,
            "result_ids": [
                (0, 0, {"result_id": cls.purchase_result_1.id, "point_max": 100}),
                (0, 0, {"result_id": cls.purchase_result_2.id, "point_max": 90}),
                (0, 0, {"result_id": cls.purchase_result_3.id, "point_max": 80}),
                (0, 0, {"result_id": cls.purchase_result_4.id, "point_max": 60}),
                (0, 0, {"result_id": cls.purchase_result_5.id, "point_max": 40}),
            ],
            "line_ids": [
                (0, 0, {"sequence": 1, "criteria_id": cls.purchase_criteria_1.id, "point_min": 0, "point_max": 20}),
                (0, 0, {"sequence": 1, "criteria_id": cls.purchase_criteria_1.id, "point_min": 0, "point_max": 20}),
                (0, 0, {"sequence": 1, "criteria_id": cls.purchase_criteria_1.id, "point_min": 0, "point_max": 20}),
                (0, 0, {"sequence": 1, "criteria_id": cls.purchase_criteria_1.id, "point_min": 0, "point_max": 20}),
                (0, 0, {"sequence": 1, "criteria_id": cls.purchase_criteria_1.id, "point_min": 0, "point_max": 20}),
            ]
        })
        cls.template_1 = cls.template_default.copy({"partner_categ_ids": cls.categor_1})
        po = Form(cls.env['purchase.order'])
        po.partner_id = cls.partner_a
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = cls.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        po = po.save()
        po.state = "purchase"
        cls.po = po
        cls.assessment = cls.env["assessment.purchase"].create({
            "purchase_id": cls.po.id
        })
