# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
from dateutil.relativedelta import relativedelta


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.depends('product_id')
    def _compute_expiration_date(self):
        self.expiration_date = False
        for lot in self:
            if lot.product_id.use_expiration_date: # and not lot.expiration_date:
                duration = lot.product_id.product_tmpl_id.expiration_time

                if lot.product_id.product_tmpl_id.division == 'food':
                    duration = 3
                elif lot.product_id.product_tmpl_id.division == 'non_food':
                    duration = 6
                elif lot.product_id.product_tmpl_id.division == 'mars':
                    duration = 2
                else:
                    duration = lot.product_id.product_tmpl_id.expiration_time

                lot.expiration_date = datetime.datetime.now() + relativedelta(months=duration)

                # if self.env.context.get('mrp_lot')
                # lot.expiration_date = datetime.datetime.now() + relativedelta(months=duration)
                # else:
                #     duration = lot.product_id.product_tmpl_id.expiration_time
                #     lot.expiration_date = datetime.datetime.now() + datetime.timedelta(days=duration)
