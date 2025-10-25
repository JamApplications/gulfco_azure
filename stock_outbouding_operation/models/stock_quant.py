# Part of Odoo. See LICENSE file for full copyright and licensing details.
import heapq
import logging
from collections import namedtuple

from ast import literal_eval
from collections import defaultdict
from markupsafe import escape
from psycopg2 import Error

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import SQL, check_barcode_encoding, format_list, groupby
from odoo.tools.float_utils import float_compare, float_is_zero
from datetime import date
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, qty=0):
        if self.env.context.get('product_shelf_partner'):
            partner = self.env.context.get('product_shelf_partner')
            product_shelf_line = partner.product_shelf_life_ids.filtered(
                lambda s: s.product_id == product_id and not s.product_category)
            if not product_shelf_line:
                product_shelf_line = partner.product_shelf_life_ids.filtered(
                    lambda s: s.product_category == product_id.categ_id)
            if not product_shelf_line and product_id.division:
                product_shelf_line = partner.product_shelf_life_ids.filtered(
                    lambda s: s.division == product_id.division)
            if product_id.country_of_origin and product_shelf_line.mapped('country_of_origin_ids'):
                product_shelf_line = product_shelf_line.filtered(
                    lambda s: product_id.country_of_origin.id in s.country_of_origin_ids.ids)
            if product_shelf_line:
                res = super(StockQuant,self.with_context(product_shelf_line=product_shelf_line))._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, qty=qty)
                reservation_threshold = product_shelf_line[0].percentage
                if reservation_threshold:
                    today = date.today()
                    res = res.filtered(lambda q: (
                            q.lot_id and q.lot_id.production_date and q.lot_id.expiration_date and
                            (q.lot_id.expiration_date.date() - today).days > 0 and
                            (q.lot_id.expiration_date.date() - q.lot_id.production_date).days > 0 and
                            ((
                                     (q.lot_id.expiration_date.date() - today).days /
                                     (q.lot_id.expiration_date.date() - q.lot_id.production_date).days
                             ) * 100) > reservation_threshold
                    ))
                return res.sorted(key=lambda r: (not r.expiration_date, r.expiration_date or False))
                # return res.sorted(lambda s:s.expiration_date)
        return super(StockQuant, self)._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                                              strict=strict, qty=qty)
    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = [('product_id', '=', product_id.id)]
        if not strict:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)] if lot_id else [('lot_id', '=', False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])
        if self.env.context.get('with_expiration'):
            domain = expression.AND([['|', ('expiration_date', '>=', self.env.context['with_expiration']), ('expiration_date', '=', False)], domain])
        if self.env.context.get('product_shelf_life_expiration'):
            domain = expression.AND([[('expiration_date', '>', self.env.context['product_shelf_life_expiration'])], domain])
        if self.env.context.get('product_shelf_partner') or self.env.context.get('stock_request_reserve_saleable'):
            domain = expression.AND([[('location_id.is_saleable_location', '=', True)], domain])
        if self.env.context.get('product_shelf_line'):
            product_shelf_line = self.env.context.get('product_shelf_line')
            if product_shelf_line:
                product_shelf_line = product_shelf_line[0]
                shelf_expiration_date = date.today() + relativedelta(months=product_shelf_line.shelf_life)
                domain = expression.AND(
                    [[('expiration_date', '>', shelf_expiration_date)], domain])
                if product_shelf_line.production_year:
                    domain = expression.AND(
                        [[('lot_id.production_year', '=', product_shelf_line.production_year)], domain])
        return domain

