
from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class AssessmentCriteria(models.Model):
    _name = "assessment.criteria"
    _description = "Assessment Criteria"
    _order = "sequence"

    sequence = fields.Integer(default=1)
    name = fields.Char(required=True)
    description = fields.Text()
    python_code = fields.Text('Formula')
    weightage_point = fields.Float()

    def _raise_error(self, localdict, error_type, e):
        raise UserError(_("""%(error_type)s
    - criteria: %(criteria)s
    - purchase: %(purchase)s
    - vendore: %(vendore)s
    - Error: %(error_message)s""",
                          error_type=error_type,
                          criteria=localdict['criteria'].name,
                          vendore=localdict['vendore'].name,
                          purchase=localdict['purchase'].name,
                          error_message=e))

    def _compute_rule(self, localdict):
        try:
            safe_eval(self.python_code or 0.0, localdict, mode='exec', nocopy=True)
            return float(localdict['result'])
            # return float(localdict['result']), localdict.get('result_qty', 1.0), localdict.get('result_rate', 100.0)
        except Exception as e:
            self._raise_error(localdict, _("Wrong python code defined for:"), e)





"""
===::RDD Criteria Code:====
+
# 
result_day = 0
for poline in purchase_line:
    for asn in poline.order_id.asn_ids:
        for asnline in asn.line_ids:
            if poline == asnline.purchase_order_line_id and asnline.asn_request_id.dispatched_date and  poline.rdd :
                diff = (asnline.asn_request_id.dispatched_date - poline.rdd.date())
                result_day = diff.days

result = result_day

===::ETA Criteria Code:=====

result_day = 0
for poline in purchase_line:
    for asn in poline.order_id.asn_ids:
        for asnline in asn.line_ids:
            if poline == asnline.purchase_order_line_id and asnline.asn_request_id.actual_arrived_port_date and poline.date_planned:
                diff = (asnline.asn_request_id.actual_arrived_port_date - poline.date_planned.date())
                result_day += diff.days

result = result_day

# result_day = 0
# for poline in purchase_line:
#     for asn in poline.order_id.asn_ids:
#         for asnline in asn.line_ids:
#             if poline == asnline.purchase_order_line_id:
#                 diff = (asnline.asn_request_id.actual_arrived_port_date - poline.date_planned.date())
#                 result_day = diff.days
# 
# result = result_day



===::Case to Fill::=====
result_qty = 0
for poline in purchase_line:
    result_qty = poline.qty_received / poline.product_qty

result = result_qty



===::Price Difference::=====
result = purchase.no_price_diff



===::Damage::=====
result = purchase.has_return_receipt



===::Shortage/Excess::=====
result = purchase.received_less_qty




===::Quality Issue::=====
result = purchase.quality_check_fail



====::Late Receipt of Document::======
result_day = 0 
for asnline in asn_line:
    if asnline.asn_request_id.actual_arrived_port_date and asnline.asn_request_id.document_receipt_date:
        diff = asnline.asn_request_id.actual_arrived_port_date  - asnline.asn_request_id.document_receipt_date
        result_day += diff.days

result = result_day



====::Demurrage & Storage::======
result = sum([asnline.asn_request_id.demurrage_amount for asnline in asn_line])
"""