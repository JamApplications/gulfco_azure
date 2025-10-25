# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools import file_open


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        return res

    def _set_lot_producing(self):
        self.ensure_one()
        date_as_int = int(self.date_finished.strftime('%Y%m'))
        exist_lot = not date_as_int or self.env['stock.lot'].search([
            ('product_id', '=', self.product_id.id),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
            ('name', '=', date_as_int),
        ], limit=1)
        if not exist_lot:
            self.lot_producing_id = self.env['stock.lot'].with_context({'mrp_lot': True}).create(self._prepare_stock_lot_values())
        else:
            self.lot_producing_id = exist_lot

            for lot in self.lot_producing_id:
                if lot.product_id.use_expiration_date:  # and not lot.expiration_date:
                    if lot.product_id.product_tmpl_id.division == 'food':
                        duration = 3
                    elif lot.product_id.product_tmpl_id.division == 'non_food':
                        duration = 6
                    elif lot.product_id.product_tmpl_id.division == 'mars':
                        duration = 2
                    else:
                        duration = lot.product_id.product_tmpl_id.expiration_time

                    lot.expiration_date = datetime.now() + relativedelta(months=duration)


    def _prepare_stock_lot_values(self):

        res = super()._prepare_stock_lot_values()
        if self.product_id.tracking == 'lot':
            date_as_int = int(self.date_finished.strftime('%Y%m'))
            res['name'] = date_as_int
        return res
