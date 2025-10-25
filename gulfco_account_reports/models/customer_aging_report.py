#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models,fields, api, _, tools
from odoo.tools.sql import drop_view_if_exists, SQL

class AccountCustomerAgingReport(models.Model):
    _name = 'account.customer.aging.report'
    _auto = False
    _description = 'Customer Aging Report'

    partner_id = fields.Many2one('res.partner')
    customer_name = fields.Char()
    customer_number = fields.Char()
    customer_class = fields.Char()
    customer_category = fields.Char()
    status = fields.Boolean()
    branch = fields.Char()
    # payment_term = fields.Many2one('account.payment.term')
    # payment_method = fields.Many2one('account.payment.method.line')
    # credit_limit_data = fields.Float('Credit Limit')
    # outstanding = fields.Float()
    # uncovered = fields.Float()
    # current = fields.Float()
    # b_31_60 = fields.Float()
    # collector_name = fields.Char()
    # collection_status = fields.Char()

    def init(self):
        query = """
               
                   SELECT
                       row_number() OVER () AS id,
                       rp.id AS partner_id,
                       rp.name AS customer_name,
                        rp.customer_code AS customer_number,
                        customer_group.name AS customer_class,
                        rp.category AS customer_category,
                        rp.active AS status,
                        rp.city AS branch
                    FROM res_partner rp
                    LEFT JOIN customer_group ON customer_group.id = rp.customer_group_id
                    WHERE rp.customer_rank > 0                         
                    GROUP BY
                    rp.id, rp.name, rp.customer_code, rp.customer_group_id,
                    rp.category, rp.active, rp.city            
           """

        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""CREATE or REPLACE VIEW %s as (%s)""", SQL.identifier(self._table), SQL(query)))