from odoo import models, api
from datetime import date

class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            matched_time = date.today()
            rec.debit_move_id.matched_date = matched_time
            rec.credit_move_id.matched_date = matched_time
        return records

    def unlink(self):
        for rec in self:
            rec.debit_move_id.matched_date = False
            rec.credit_move_id.matched_date = False
        return super().unlink()
