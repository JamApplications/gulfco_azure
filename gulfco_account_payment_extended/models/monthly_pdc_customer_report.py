# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api,  _, tools



class MonthlyPdcCustomerReport(models.Model):
    _name = "monthly.pdc.customer.report"
    _description = "Monthly PDC Customer Report"
    _auto = False

    customer_code = fields.Char(string="Customer No")
    name = fields.Char(string="Customer Name")
    uncovered_amount = fields.Float(string="Uncovered Amount")
    # amount_due = fields.Float(string="Uncovered Amount")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'monthly_pdc_customer_report')
        self._cr.execute("""
               CREATE OR REPLACE VIEW monthly_pdc_customer_report AS (
                   SELECT
                       rp.id AS id,
                       rp.customer_code,
                       rp.name,
                       COALESCE(SUM(am.uncovered_balance), 0.0) AS uncovered_amount
                   FROM res_partner rp
                   LEFT JOIN account_payment_method pm ON rp.media_id = pm.id
                   LEFT JOIN account_move am ON am.partner_id = rp.id
                   WHERE rp.is_credit_hold = TRUE
                     AND pm.is_pdc_method = TRUE
                     AND am.move_type = 'out_invoice'
                     AND am.state = 'posted'
                     AND am.payment_state != 'paid'
                   GROUP BY rp.id, rp.customer_code, rp.name
               )
           """)