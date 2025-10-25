from odoo import api, fields, models, _

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        copy=False,
        compute="compute_state",
        store=True,
        readonly=False
    )

    @api.depends('line_ids', 'line_ids.state','request_type')
    def compute_state(self):
        for record in self:
            record_state = 'draft'
            if record.request_type == 'order_analysis':
                if record.line_ids:
                    for state in ['approved', 'rejected', 'done']:
                        if len(record.line_ids.filtered(lambda s: s.state == state)) == len(record.line_ids):
                            record_state = state
            else:
                if record.state:
                    record_state = record.state
                else:
                    record_state = 'draft'
            record.state = record_state
