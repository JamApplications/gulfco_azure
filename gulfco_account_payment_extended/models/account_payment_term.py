from odoo import models, fields
from odoo.tools import date_utils
from dateutil.relativedelta import relativedelta

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    calculation_based_on = fields.Selection(
        [
            ("days", "Days"),
            ("months", "Months"),
        ],
        string="Calculation Based On",
        default="days",
    )

    is_cach = fields.Boolean('Is Cash')


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    def _get_due_date(self, date_ref):
        """If payment term is set to calculate based on "months", move to end of the month"""
        res_dt = super()._get_due_date(date_ref)
        due_date = fields.Date.from_string(date_ref) or fields.Date.today()
        # if res_dt and self.payment_id.calculation_based_on == "months":
        #     res_dt = date_utils.end_of(res_dt, 'month')
        if self.payment_id.calculation_based_on == "months": 
            if self.delay_type == 'days_after':
                # return last day of the selected date month
                return date_utils.end_of(due_date, 'month')
            elif self.delay_type == 'days_after_end_of_month':
                # return last day of the next month of selected date
                return date_utils.end_of(due_date + relativedelta(months=1), 'month')
            elif self.delay_type == 'days_after_end_of_next_month':
                return date_utils.end_of(due_date + relativedelta(months=2), 'month')
            
        return res_dt