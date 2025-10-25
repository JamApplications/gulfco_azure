# -*- coding: utf-8 -*-
import requests
from pytz import country_timezones
from datetime import date, timedelta
from collections import defaultdict
from odoo import http
from odoo.exceptions import AccessError, MissingError
import calendar
import imghdr
from odoo.fields import Command
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.addons.web.controllers.home import CREDENTIAL_PARAMS
from urllib.parse import parse_qs
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Datetime
from datetime import datetime, timedelta, date
import copy
import itertools
SIGN_UP_PARAMS = ['name', 'login', 'password', 'confirm_password']
from odoo.http import content_disposition, request
import random
import string
import io
from PIL import Image
import base64
from datetime import datetime
import logging
from itertools import groupby
_logger = logging.getLogger("============API Authenticate========")
from odoo.tools import float_round
default_token_size = 16
import time
from collections import OrderedDict
import re
from odoo.tools.safe_eval import safe_eval


def _default_app_unique_key(size, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class PlennixMobileAppAPI(http.Controller):

    def _check_authentication_generalize_for_apis(self):
        response = {}
        values = request.httprequest.json
        if not values.get('user_id', False) or not values.get('auth_token', False):
            response.update({
                "success": False,
                "success_msg": False,
                "error_msg": "Mandatory keys(user_id,auth_token) are not passed in this api, Thanks!"
            })
            return response, {}
        verify_access = self._verify_auth_token(
            values.get('user_id', False), values.get('auth_token', False))
        if not verify_access.get('status'):
            response.update({
                "success": False,
                "success_msg": "Invalid token",
                "error_msg": "Invalid token",
                "user_id": values.get('user_id', False)
            })
            return response, verify_access
        return response, verify_access
    def _get_image_url_dynamic(self, model, record_id, field_name):
        return f"/web/image/{model}/{record_id}/{field_name}"
    def _verify_auth_token(self, user_id=False, token=False):
        result = {'status': False}
        # domain = [('id', '=', int(user_id)), ('ft_auth_token', '=', token)]
        domain = [('id', '=', int(user_id))]
        public_user = request.env.ref('base.public_user')
        if public_user.id == int(user_id):
            domain.append(('active', 'in', [True, False]))
        user_found = request.env['res.users'].sudo().with_user(SUPERUSER_ID).search(domain, limit=1)
        # if user_found:
        if user_found and user_found.mobile_auth_token_ids.filtered(lambda x: x.mobile_app_auth_token == token):
            result = {'status': True, 'user': user_found}
        return result

    @http.route('/api/v1/sign_in', type='json', auth='none', methods=['POST'])
    def app_sign_in_api(self, **kwargs):
        response = {}
        credential = {
            key: value for key, value in request.httprequest.json.items()
            if key in CREDENTIAL_PARAMS and value
        }
        credential.setdefault('type', 'password')
        login_user = False
        mpartner = False

        try:
            mobile_app_auth_token = ''
            user_email_or_mobile = credential.get('login')
            password = credential.get('password')


            try:
                auth_info = request.session.authenticate(request.db, credential)
            except Exception:
                auth_info = {}

            if auth_info and auth_info.get('uid'):
                login_user = request.env['res.users'].sudo().browse(int(auth_info['uid']))
            else:
                partner = request.env['res.partner'].sudo().search([
                    '|', ('email', '=', user_email_or_mobile), ('mobile', '=', user_email_or_mobile)
                ], limit=1)

                if partner and partner.worker_password_data and password == partner.worker_password_data:
                    if not partner.internal_user:
                        raise Exception("No linked portal user found for this partner.")
                    login_user = partner.internal_user if partner.internal_user else False
                    auth_info = {
                        'uid': login_user.id,
                        'auth_method': 'portal'
                    }
                    mpartner = partner
                else:
                    raise Exception("Invalid login or password.")

            if not login_user:
                raise Exception("Login failed — user not found.")
            mobile_app_auth_token = _default_app_unique_key(default_token_size)

            if not login_user:
                raise Exception("login_user is empty")
            if len(login_user) > 1:
                _logger.warning("Multiple users found: %s", login_user)
                login_user = login_user[0]
            user = request.env['res.users'].sudo().browse(login_user)
            login_user = login_user.with_user(user.id).sudo()
            login_user.write({
                'mobile_auth_token_ids': [Command.create({
                    'user_id': login_user.id,
                    'last_login_time': fields.Datetime.now(),
                    'mobile_app_auth_token': mobile_app_auth_token
                })]
            })
            name = login_user.name
            email = login_user.email
            reset_password_uid = login_user.email
            mobile = login_user.mobile
            user_type = login_user.user_type
            image = self._get_image_url_dynamic(
                model=login_user._name, record_id=login_user.id, field_name='image_512'
            )

            if mpartner:
                name = mpartner.name
                email = mpartner.email
                reset_password_uid = mpartner.email
                mobile = mpartner.mobile
                user_type = login_user.user_type
                image = self._get_image_url_dynamic(model=mpartner._name, record_id=mpartner.id, field_name='image_512')

            if login_user.user_type == 'sales_user' or not mpartner:
                mpartner = login_user.partner_id

                name = login_user.name
                email = login_user.email
                reset_password_uid = login_user.email
                mobile = login_user.mobile
                user_type = login_user.user_type
                image = self._get_image_url_dynamic(
                    model=login_user._name, record_id=login_user.id, field_name='image_512'
                )

            response.update({
                "success": True,
                "success_msg": "Signed In Successfully",
                'user_id': auth_info['uid'],
                # 'partner_id': login_user.partner_id.id,
                'partner_id': mpartner.id,
                'auth_token': mobile_app_auth_token,
                'auth_method': auth_info['auth_method'],
                'name': name,
                'email': email,
                'mobile': mobile,
                'type': user_type,
                'image': image,
                'reset_password_uid': reset_password_uid,
                'delivery_user': login_user.has_group('plnx_sales_team.group_sales_team_delivery'),
                'van_sale_user': login_user.has_group('plnx_sales_team.group_sales_team_van_sale'),
                'pre_sale_user': login_user.has_group('plnx_sales_team.group_sales_team_pre_sales'),
                'merchandiser_user': login_user.has_group('plnx_sales_team.group_sales_team_merchandiser')
            })

        except Exception as e:
            response.update({
                "success": False,
                "success_msg": str(e),
                'user_id': False,
                'auth_method': False,
                'auth_token': False,
            })
            _logger.exception('Login Exception')

        return response

    @http.route('/api/v1/reset_password', type='json', auth='none', methods=['POST'])
    def submit_password(self, **kwargs):
        response = {}
        try:
            values = request.httprequest.json
            email = values.get('email')
            if not email:
                return {
                    "success": False,
                    "success_msg": "Email is required."
                }

            reset_user = request.env['res.users'].sudo().with_user(SUPERUSER_ID).search(
                [('login', '=', email)],
                limit=1
            )
            if reset_user:
                if reset_user.has_group('base.group_portal') and not reset_user.has_group('base.group_user'):
                    reset_user.sudo().action_reset_password()
                    response.update({
                        "success": True,
                        "success_msg": "Reset password link sent successfully to portal user.",

                    })
                else:
                    reset_user.sudo().action_reset_password()
                    response.update({
                        "success": True,
                        "success_msg": "Reset password link sent successfully!"
                    })
            else:
                partner = request.env['res.partner'].sudo().search([
                    '|', ('email', '=', email), ('mobile', '=', email)
                ], limit=1)

                if partner:
                    partner.auto_generate_password()
                    response.update({
                        "success": True,
                        "success_msg": "Reset password link sent successfully to portal user.",
                    })
                else:
                    response.update({
                        "success": False,
                        "success_msg": "User not found with provided email or mobile."
                    })

        except Exception as e:
            _logger.exception("Exception in forget password API:")
            response.update({
                "success": False,
                "success_msg": str(e)
            })

        return response

    @http.route('/api/v1/logout/<int:user_id>', type='json', auth='none', methods=['POST'])
    def app_user_logout(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(kwargs.get('user_id', 0))
            token = values.get('auth_token')

            user = request.env['res.users'].sudo().with_user(SUPERUSER_ID).browse(user_id)

            if user and user.id == int(values.get('user_id', 0)):
                matching_tokens = user.mobile_auth_token_ids.filtered(lambda x: x.mobile_app_auth_token == token)

                if matching_tokens:
                    matching_tokens.unlink()
                    response.update({
                        "success": True,
                        "success_msg": "User logged out successfully!",
                        'user_id': user_id,
                    })
                else:
                    response.update({
                        "success": True,
                        "success_msg": "User already logged out or invalid token!",
                        'user_id': user_id,
                    })
            else:
                response.update({
                    "success": False,
                    "success_msg": "Invalid user ID or mismatch!",
                    'user_id': False,
                })

        except Exception as e:
            _logger.exception("Logout error:")
            response.update({
                "success": False,
                "success_msg": str(e),
                'user_id': False,
            })

        return response

    @http.route('/public/image/<string:model>/<int:record_id>/<string:field_name>', type='http', auth='public',
                website=True)
    def public_image(self, model, record_id, field_name, **kwargs):
        try:
            record = request.env[model].sudo().browse(record_id)
            image_base64 = getattr(record, field_name, False)
            if not record.exists() or not image_base64:
                raise ValueError("Record or image not found.")

            image_data = base64.b64decode(image_base64)
            image_type = imghdr.what(None, h=image_data) or 'png'

            return request.make_response(
                image_data,
                headers=[('Content-Type', f'image/{image_type}'), ('Content-Disposition', 'inline')]
            )
        except Exception as e:
            return self._error_page(str(e))

    def _error_page(self, message):
        return request.make_response(
            f"<html><body style='background:#1a1a1a;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;'>{message}</body></html>",
            headers=[('Content-Type', 'text/html')]
        )

    def _get_image_url_dynamic(self, model, record_id, field_name):
        ICP = request.env['ir.config_parameter'].sudo()
        base_url = ICP.get_param('web.base.url') or request.httprequest.host_url[:-1]
        return "{}/public/image/{}/{}/{}".format(base_url, model, record_id, field_name)

    @http.route('/api/v1/dashboard_sale', type='json', auth='none', methods=['POST'])
    def customer_dashboard_sale(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {
                    'success': False,
                    'error_msg': 'Invalid or expired auth token.'
                }


            today = fields.Datetime.today()
            start_date = today
            date_end = start_date.replace(hour=23, minute=59, second=59)

            user = request.env['res.users'].sudo().browse(user_id)
            total_sales = request.env['sale.order'].sudo().with_user(SUPERUSER_ID).search_count(
                [('assign_to', '=', user.partner_id.id), ('state', '=', 'sale'),
                 ('date_order', '>=', start_date),
                 ('date_order', '<=', date_end)
                 ])


            fsm_orders = request.env['fsm.order'].sudo().with_user(SUPERUSER_ID).search(
                [('person_id_partner', '=', user.partner_id.id), ('scheduled_date_start', '>=', start_date), ('scheduled_date_start', '<=', date_end)])
            total_visits = len(fsm_orders)

            completed_stage = request.env['fsm.stage'].sudo().search([('name', '=', 'Completed')], limit=1)
            completed_visits = fsm_orders.filtered(lambda o: o.stage_id.id == completed_stage.id)

            completed_visits_count = len(completed_visits)
            remaining_visits = total_visits - completed_visits_count

            response.update({
                'success': True,
                'data': {
                    'user_id': user.id,
                    'user_name': user.name,
                    'total_sales': total_sales,
                    'total_visits': total_visits,
                    'remaining_visits': remaining_visits,
                    'completed_visits': len(completed_visits),
                }
            })

        except Exception as e:
            response.update({
                'success': False,
                'error_msg': str(e)
            })
            _logger.info('Failed to open the dashboard.')
        return response

    @http.route('/api/v1/brand', type='json', auth='none', methods=['POST'], csrf=False)
    def product_brand_api(self, **kwargs):
        # 1. Payload validation (no significant changes)
        values = request.httprequest.json or {}
        user_id = values.get('user_id')
        auth_token = values.get('auth_token')

        if not all([user_id, auth_token]):
            return {'success': False, 'error_msg': 'Missing required parameters.'}
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return {'success': False, 'error_msg': 'Invalid user_id format.'}

        # 2. Auth token validation
        is_valid = request.env['mobile.auth.token'].sudo().search_count([
            ('user_id', '=', user_id),
            ('mobile_app_auth_token', '=', auth_token)
        ])
        if not is_valid:
            return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

        try:
            # 3. Get user's allowed divisions (RESTORED LOGIC)
            user = request.env['res.users'].sudo().browse(user_id)
            partner = user.partner_id

            # This was the key part from your original code. It collects a list of codes, not IDs.
            div_ids = [div.type for div in partner.division_ids]

            # ADDED FOR DEBUGGING: Check the logs to see what divisions are found
            _logger.info(f"Attempting to find products for user '{user.login}' with divisions: {div_ids}")

            # 4. Fetch all products in a SINGLE query
            Product = request.env['product.product'].sudo()
            domain = [
                ('sale_ok', '=', True),
                ('type', '=', 'consu'),
                ('active', '=', True),
                ('brand_id', '!=', False),
                ('division', 'in', div_ids),  # This will now work correctly
            ]

            # ADDED FOR DEBUGGING: Check the logs to see the final search domain
            _logger.info(f"Database search domain: {domain}")

            # Order by brand_id to prepare for grouping
            all_products_rs = Product.search(domain, order='brand_id, name')

            # ADDED FOR DEBUGGING: Check how many products were found
            _logger.info(f"Found {len(all_products_rs)} products matching the criteria.")

            # 5. Pre-fetch related data for the entire recordset to avoid N+1 queries
            all_products_rs.mapped('packaging_ids')
            all_products_rs.mapped('taxes_id')

            _logger.info(all_products_rs)

            # 6. Group products by brand in memory (highly efficient)
            all_products_data = []
            brand_list = []

            for brand, products_iter in groupby(all_products_rs, key=lambda p: p.brand_id):
                product_list = []
                # products_iter is an iterator, so we process it here
                for prod in products_iter:
                    # Packaging data is now fast because of pre-fetching
                    packaging_data = [{
                        'id': pack.id,
                        'name': pack.name,
                        'uom': pack.product_uom_id.name,
                        'uom_id': pack.product_uom_id.id,
                        'qty_per_pack': pack.qty,
                        'on_hand_qty': int(prod.qty_available // pack.qty) if pack.qty > 0 else 0,
                    } for pack in prod.packaging_ids]

                    product_data = {
                        'id': prod.id,
                        'name': prod.name,
                        'barcode': prod.barcode or '',
                        'uom': prod.uom_id.name,
                        'uom_id': prod.uom_id.id,
                        'lst_price': prod.list_price,
                        'taxes_id': prod.taxes_id.id if prod.taxes_id else False,
                        'taxes_name': prod.taxes_id.name if prod.taxes_id else '',
                        'item_no': prod.default_code or '',
                        'description': prod.description_sale or '',
                        'division': prod.division,
                        'image': f'/web/image/{prod._name}/{prod.id}/image_512',
                        'quantity_on_hand': prod.qty_available,
                        'product_packaging': packaging_data,
                    }
                    product_list.append(product_data)
                    all_products_data.append(product_data)

                if product_list:
                    brand_list.append({
                        'id': brand.id,
                        'name': brand.name,
                        'products': product_list,
                    })

            # 7. Final response assembly
            brand_list.insert(0, {
                'id': -1,
                'name': 'ALL',
                'products': all_products_data,
            })

            # Fetch auxiliary data using efficient search_read
            uom_details = request.env['uom.uom'].sudo().search_read([], ['name'])

            return {
                'success': True,
                'data': {'categories': brand_list, 'uom': uom_details}
            }

        except Exception as e:
            _logger.exception('Error in /api/v1/brand:')
            return {'success': False, 'error_msg': str(e)}


    @http.route('/api/v1/load_brand_location', type='json', auth='user', methods=['POST'], csrf=False)
    def load_brand_location(self, **kwargs):
        # 1) Payload validation
        values = request.httprequest.json or {}
        user_id = values.get('user_id')
        auth_token = values.get('auth_token')

        if not user_id or not auth_token:
            return {'success': False, 'error_msg': 'Missing required parameters.'}
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return {'success': False, 'error_msg': 'Invalid user_id format.'}

        # 2) Auth token validation
        is_valid = request.env['mobile.auth.token'].sudo().search_count([
            ('user_id', '=', user_id),
            ('mobile_app_auth_token', '=', auth_token)
        ])
        if not is_valid:
            return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

        try:
            # 3) Context: divisions + van location
            user = request.env['res.users'].sudo().browse(user_id)
            partner = user.partner_id
            div_ids = [div.type for div in partner.division_ids]  # list of division codes
            van_location = partner.van_location

            _logger.info(
                "load_brand_location: user=%s divisions=%s van_location=%s",
                user.login, div_ids, van_location and van_location.display_name
            )

            # 4) Fetch products with extra fields (ordered by brand then name)
            Product = request.env['product.product'].sudo()
            product_domain = [
                ('sale_ok', '=', True),
                ('type', '=', 'consu'),
                ('active', '=', True),
                ('brand_id', '!=', False),
                ('division', 'in', div_ids),
            ]
            product_fields = [
                # already used
                'name', 'barcode', 'uom_id', 'list_price', 'taxes_id', 'default_code',
                'description_sale', 'division', 'brand_id', 'packaging_ids', 'qty_available',

                # NEW details
                'categ_id', 'company_id', 'tracking', 'purchase_ok', 'sale_ok',
                'uom_po_id', 'standard_price', 'weight', 'volume',
                'currency_id', 'description_purchase',
                'product_template_attribute_value_ids',
            ]
            products_rs = Product.search(product_domain, order='brand_id, name')
            products = products_rs.read(product_fields)  # list of dicts
            _logger.info("load_brand_location: products found=%s", len(products))

            if not products:
                uom_details = request.env['uom.uom'].sudo().search_read([], ['name'])
                return {'success': True, 'data': {'categories': [], 'uom': uom_details}}

            product_ids = [p['id'] for p in products]

            # ---------------------------------------------------------------------
            # 5) VAN quants: totals + per-lot lines (single fetch)
            # ---------------------------------------------------------------------
            totals_by_product = {}                     # pid -> {'quantity': float, 'reserved': float}
            lots_by_product = defaultdict(list)        # pid -> [lot_line, ...]

            if van_location:
                Quant = request.env['stock.quant'].sudo()
                quant_domain = [
                    ('product_id', 'in', product_ids),
                    ('location_id', 'child_of', van_location.id),
                    # don't filter by quantity: we want accurate available (qty - reserved)
                ]
                quant_fields = ['product_id', 'quantity', 'reserved_quantity', 'lot_id', 'in_date', 'location_id']
                quants = Quant.search(quant_domain).read(quant_fields)

                _logger.info("load_brand_location: quants=%s at %s", len(quants), van_location.display_name)

                # Collect ids for lots and locations to enrich
                lot_ids, loc_ids = set(), set()
                for q in quants:
                    if q.get('lot_id'):
                        lot_ids.add(q['lot_id'][0])
                    if q.get('location_id'):
                        loc_ids.add(q['location_id'][0])

                lot_map = {}
                if lot_ids:
                    lot_fields = ['name', 'expiration_date', 'use_date', 'removal_date', 'alert_date']
                    lot_map = {
                        rec['id']: rec
                        for rec in request.env['stock.lot'].sudo().browse(list(lot_ids)).read(lot_fields)
                    }

                loc_map = {}
                if loc_ids:
                    loc_fields = ['complete_name']
                    loc_map = {
                        rec['id']: rec
                        for rec in request.env['stock.location'].sudo().browse(list(loc_ids)).read(loc_fields)
                    }

                # Build totals + per-lot list
                for q in quants:
                    pid = q['product_id'][0]
                    qty = float(q.get('quantity') or 0.0)
                    rsv = float(q.get('reserved_quantity') or 0.0)
                    avail = float(q.get('available_quantity') or 0.0)

                    if pid not in totals_by_product:
                        totals_by_product[pid] = {'quantity': 0.0, 'reserved': 0.0}
                    totals_by_product[pid]['quantity'] += qty
                    totals_by_product[pid]['reserved'] += rsv

                    lot_id = q['lot_id'][0] if q.get('lot_id') else False
                    lot_rec = lot_map.get(lot_id, {}) if lot_id else {}
                    lotObj = False
                    if lot_id:
                        lotObj = request.env['stock.lot'].sudo().browse(int(lot_id))
                    lot_line = {
                        'lot_id'            : lot_id or False,
                        'lot_name'          : (q['lot_id'][1] if q.get('lot_id') else False) or False,
                        'expiration_date'   : fields.Datetime.to_string(lot_rec.get('expiration_date')) if lot_rec.get('expiration_date') else False,
                        'use_date'          : fields.Datetime.to_string(lot_rec.get('use_date')) if lot_rec.get('use_date') else False,
                        'removal_date'      : fields.Datetime.to_string(lot_rec.get('removal_date')) if lot_rec.get('removal_date') else False,
                        'alert_date'        : fields.Datetime.to_string(lot_rec.get('alert_date')) if lot_rec.get('alert_date') else False,
                        'in_date'           : fields.Datetime.to_string(q.get('in_date')) if q.get('in_date') else False,
                        'quantity'          : qty,
                        'reserved_quantity' : rsv,
                        'available_quantity': avail,  # this is what the app should use
                        'location_id'       : q['location_id'][0] if q.get('location_id') else False,
                        'location_name'     : loc_map.get(q['location_id'][0], {}).get('complete_name') if q.get('location_id') else False,
                        'is_salable'        : lotObj.is_salable if lotObj else True,

                    }
                    lots_by_product[pid].append(lot_line)
            else:
                _logger.info("load_brand_location: no van_location for user -> skipping quants")

            # ---------------------------------------------------------------------
            # 6) Packaging (batch): fetch once, attach with on_hand by available
            # ---------------------------------------------------------------------
            packaging_ids = set()
            for p in products:
                for pack_id in (p.get('packaging_ids') or []):
                    packaging_ids.add(pack_id)

            packs_by_product = defaultdict(list)  # pid -> [pack_template, ...]
            if packaging_ids:
                Pack = request.env['product.packaging'].sudo()
                pack_fields = ['name', 'product_uom_id', 'qty', 'product_id']
                for rec in Pack.browse(list(packaging_ids)).read(pack_fields):
                    uom_id, uom_name = (rec['product_uom_id'] or [False, False])
                    pid = rec['product_id'][0] if rec.get('product_id') else False
                    if not pid:
                        continue
                    packs_by_product[pid].append({
                        'id'          : rec['id'],
                        'name'        : rec['name'],
                        'uom'         : uom_name,
                        'uom_id'      : uom_id,
                        'qty_per_pack': rec['qty'] or 0.0,
                    })

            # ---------------------------------------------------------------------
            # 7) Taxes (first tax name)
            # ---------------------------------------------------------------------
            first_tax_ids = set()
            for p in products:
                tax_ids = p.get('taxes_id') or []
                if tax_ids:
                    first_tax_ids.add(tax_ids[0])
            tax_name_by_id = {}
            if first_tax_ids:
                for rec in request.env['account.tax'].sudo().browse(list(first_tax_ids)).read(['name']):
                    tax_name_by_id[rec['id']] = rec['name']

            # ---------------------------------------------------------------------
            # 8) Variant attributes (read once to strings)
            # ---------------------------------------------------------------------
            all_ptav_ids = set()
            for p in products:
                for vid in (p.get('product_template_attribute_value_ids') or []):
                    all_ptav_ids.add(vid)
            attr_values_map = {}  # ptav_id -> {'attribute': name, 'value': name}
            if all_ptav_ids:
                PTAV = request.env['product.template.attribute.value'].sudo()
                for rec in PTAV.browse(list(all_ptav_ids)).read(['name', 'attribute_id']):
                    attr_values_map[rec['id']] = {
                        'attribute': (rec['attribute_id'] and rec['attribute_id'][1]) or '',
                        'value'    : rec['name'] or '',
                    }

            # ---------------------------------------------------------------------
            # 9) Build payloads & brand buckets
            # ---------------------------------------------------------------------
            brand_buckets = OrderedDict()  # brand_id -> {'id','name','products':[]}
            all_products_payload = []

            for p in products:
                pid = p['id']
                brand_id, brand_name = (p['brand_id'] or [False, 'Unknown'])
                if brand_id not in brand_buckets:
                    brand_buckets[brand_id] = {'id': brand_id, 'name': brand_name, 'products': []}

                # Available at van (fallback to global qty if no van totals)
                totals = totals_by_product.get(pid)
                if totals:
                    available_at_van = max(0.0, (totals['quantity'] - totals['reserved']))
                    location_id = van_location.id
                    location_name = van_location.complete_name
                    qty_at_location = float(totals['quantity'])
                else:
                    available_at_van = float(p.get('qty_available') or 0.0)
                    location_id = van_location.id if van_location else None
                    location_name = van_location.complete_name if van_location else None
                    qty_at_location = None

                # Packaging on-hand from available
                packaging_data = []
                for tmpl in packs_by_product.get(pid, []):
                    qpp = float(tmpl['qty_per_pack'] or 0.0)
                    on_hand = int(available_at_van // qpp) if qpp > 0.0 else 0
                    packaging_data.append({
                        'id'          : tmpl['id'],
                        'name'        : tmpl['name'],
                        'uom'         : tmpl['uom'],
                        'uom_id'      : tmpl['uom_id'],
                        'qty_per_pack': qpp,
                        'on_hand_qty' : on_hand,
                    })

                # First tax only
                tax_ids = p.get('taxes_id') or []
                tax_id = tax_ids[0] if tax_ids else False
                tax_name = tax_name_by_id.get(tax_id, '') if tax_id else ''

                # Pairs
                uom_id, uom_name       = (p['uom_id'] or [False, ''])
                uom_po_id, uom_po_name = (p.get('uom_po_id') or [False, ''])
                categ_id, categ_name   = (p.get('categ_id') or [False, ''])
                company_id, comp_name  = (p.get('company_id') or [False, ''])
                currency_id, curr_name = (p.get('currency_id') or [False, ''])

                # Variant attribute strings (small list)
                attr_list = []
                for vid in (p.get('product_template_attribute_value_ids') or []):
                    av = attr_values_map.get(vid)
                    if av:
                        attr_list.append(av)

                product_payload = {
                    # identity & base
                    'id'               : pid,
                    'name'             : p.get('name') or '',
                    'barcode'          : p.get('barcode') or '',
                    'default_code'     : p.get('default_code') or '',
                    'item_no'          : p.get('default_code') or '',
                    'division'         : p.get('division') or '',
                    'brand_id'         : brand_id or 0,
                    'brand_name'       : brand_name or 'Unknown',
                    'image'            : f"/web/image/product.product/{pid}/image_512",

                    # categorization / company / tracking
                    'categ_id'         : categ_id or False,
                    'categ_name'       : categ_name or '',
                    'company_id'       : company_id or False,
                    'company_name'     : comp_name or '',
                    'tracking'         : p.get('tracking') or 'none',   # none/lot/serial

                    # uoms
                    'uom'              : uom_name,
                    'uom_id'           : uom_id,
                    'uom_po'           : uom_po_name,
                    'uom_po_id'        : uom_po_id,

                    # prices & currency
                    'lst_price'        : p.get('list_price') or 0.0,
                    'standard_price'   : p.get('standard_price') or 0.0,  # remove if you don’t want to expose cost
                    'currency_id'      : currency_id or False,
                    'currency'         : curr_name or '',

                    # taxes (first)
                    'taxes_id'         : tax_id or False,
                    'taxes_name'       : tax_name,

                    # flags
                    'sale_ok'          : bool(p.get('sale_ok')),
                    'purchase_ok'      : bool(p.get('purchase_ok')),
                    'active'           : True,  # filtered already

                    # logistics
                    'weight'           : p.get('weight') or 0.0,
                    'volume'           : p.get('volume') or 0.0,

                    # descriptions
                    'description'          : p.get('description_sale') or '',
                    'description_purchase' : p.get('description_purchase') or '',

                    # global quantity (kept for back-compat)
                    'quantity_on_hand' : p.get('qty_available') or 0.0,

                    # VAN/location specifics
                    'quantity_on_hand_at_location' : qty_at_location,
                    'available_qty_at_location'    : float(available_at_van),
                    'location_id'                  : location_id,
                    'location_name'                : location_name,

                    # lots at van (may be empty list)
                    'lots'             : lots_by_product.get(pid, []),

                    # packaging from available
                    'product_packaging': packaging_data,

                    # variant attribute summary
                    'attribute_values' : attr_list,   # [{attribute, value}, ...]
                }

                brand_buckets[brand_id]['products'].append(product_payload)
                all_products_payload.append(product_payload)

            # 10) Assemble response
            brand_list = [{'id': -1, 'name': 'ALL', 'products': all_products_payload}]
            for b in brand_buckets.values():
                if b['products']:
                    brand_list.append(b)

            # UoM list for dropdowns
            uom_details = request.env['uom.uom'].sudo().search_read([], ['name'])

            return {'success': True, 'data': {'categories': brand_list, 'uom': uom_details}}

        except Exception as e:
            _logger.exception('Error in /api/v1/load_brand_location:')
            return {'success': False, 'error_msg': str(e)}
    # @http.route('/api/v1/load_brand_location', type='json', auth='user', methods=['POST'], csrf=False)
    # def load_brand_location(self, **kwargs):
    #     # 1) Payload validation
    #     values = request.httprequest.json or {}
    #     user_id = values.get('user_id')
    #     auth_token = values.get('auth_token')
    #
    #     if not user_id or not auth_token:
    #         return {'success': False, 'error_msg': 'Missing required parameters.'}
    #     try:
    #         user_id = int(user_id)
    #     except (ValueError, TypeError):
    #         return {'success': False, 'error_msg': 'Invalid user_id format.'}
    #
    #     # 2) Token validation
    #     is_valid = request.env['mobile.auth.token'].sudo().search_count([
    #         ('user_id', '=', user_id),
    #         ('mobile_app_auth_token', '=', auth_token)
    #     ])
    #     if not is_valid:
    #         return {'success': False, 'error_msg': 'Invalid or expired auth token.'}
    #
    #     try:
    #         # 3) User context: divisions + van location
    #         user = request.env['res.users'].sudo().browse(user_id)
    #         partner = user.partner_id
    #         div_ids = [div.type for div in partner.division_ids]  # list of codes
    #         van_location = partner.van_location
    #
    #         _logger.info("load_brand_location: user=%s divisions=%s van_location=%s",
    #                      user.login, div_ids, van_location and van_location.display_name)
    #
    #         # 4) Fetch products (brand wise), minimal fields + order for stable brand sections
    #         Product = request.env['product.product'].sudo()
    #         product_domain = [
    #             ('sale_ok', '=', True),
    #             ('type', '=', 'consu'),
    #             ('active', '=', True),
    #             ('brand_id', '!=', False),
    #             ('division', 'in', div_ids),
    #         ]
    #         product_fields = [
    #             'name', 'barcode', 'uom_id', 'list_price', 'taxes_id', 'default_code',
    #             'description_sale', 'division', 'brand_id', 'packaging_ids', 'qty_available'
    #         ]
    #         products_rs = Product.search(product_domain, order='brand_id, name')
    #         products = products_rs.read(product_fields)  # list of dicts
    #
    #         _logger.info("load_brand_location: products found=%s", len(products))
    #
    #         if not products:
    #             # keep shape: return empty categories + uom
    #             uom_details = request.env['uom.uom'].sudo().search_read([], ['name'])
    #             return {'success': True, 'data': {'categories': [], 'uom': uom_details}}
    #
    #         product_ids = [p['id'] for p in products]
    #
    #         # ---------------------------------------------------------------------
    #         # 5) VAN quants: totals + per-lot lines (single fetch, then maps)
    #         # ---------------------------------------------------------------------
    #         totals_by_product = {}    # pid -> {'quantity': float, 'reserved': float}
    #         lots_by_product = defaultdict(list)  # pid -> [lot_line, ...]
    #
    #         if van_location:
    #             Quant = request.env['stock.quant'].sudo()
    #             quant_domain = [
    #                 ('product_id', 'in', product_ids),
    #                 ('location_id', 'child_of', van_location.id),
    #                 ('quantity', '>', 0),
    #             ]
    #             quant_fields = ['product_id', 'quantity', 'reserved_quantity', 'lot_id', 'in_date', 'location_id']
    #             quants = Quant.search(quant_domain).read(quant_fields)  # list of dicts
    #
    #             _logger.info("load_brand_location: quants=%s at %s", len(quants), van_location.display_name)
    #
    #             # Collect ids for lots and locations to enrich later
    #             lot_ids = set()
    #             loc_ids = set()
    #             for q in quants:
    #                 if q.get('lot_id'):
    #                     lot_ids.add(q['lot_id'][0])
    #                 if q.get('location_id'):
    #                     loc_ids.add(q['location_id'][0])
    #
    #             # Read lots (dates) and locations (complete_name) once
    #             lot_map = {}
    #             if lot_ids:
    #                 lot_fields = ['name', 'expiration_date', 'use_date', 'removal_date', 'alert_date']
    #                 lot_map = {rec['id']: rec for rec in request.env['stock.lot'].sudo().browse(list(lot_ids)).read(lot_fields)}
    #
    #             loc_map = {}
    #             if loc_ids:
    #                 loc_fields = ['complete_name']
    #                 loc_map = {rec['id']: rec for rec in request.env['stock.location'].sudo().browse(list(loc_ids)).read(loc_fields)}
    #
    #             # Build totals + per-lot list
    #             for q in quants:
    #                 pid = q['product_id'][0]
    #                 qty = float(q.get('quantity') or 0.0)
    #                 rsv = float(q.get('reserved_quantity') or 0.0)
    #                 avail = qty - rsv
    #
    #                 if pid not in totals_by_product:
    #                     totals_by_product[pid] = {'quantity': 0.0, 'reserved': 0.0}
    #                 totals_by_product[pid]['quantity'] += qty
    #                 totals_by_product[pid]['reserved'] += rsv
    #
    #                 lot_id = q['lot_id'][0] if q.get('lot_id') else False
    #                 lot_name = q['lot_id'][1] if q.get('lot_id') else False
    #                 lot_rec = lot_map.get(lot_id, {}) if lot_id else {}
    #
    #                 # Date normalization to strings (safe for JSON)
    #                 exp_date = lot_rec.get('expiration_date')
    #                 lot_line = {
    #                     'lot_id': lot_id or False,
    #                     'lot_name': lot_name or False,
    #                     'expiration_date': fields.Datetime.to_string(exp_date) if exp_date else False,
    #                     'use_date': fields.Datetime.to_string(lot_rec.get('use_date')) if lot_rec.get('use_date') else False,
    #                     'removal_date': fields.Datetime.to_string(lot_rec.get('removal_date')) if lot_rec.get('removal_date') else False,
    #                     'alert_date': fields.Datetime.to_string(lot_rec.get('alert_date')) if lot_rec.get('alert_date') else False,
    #                     'in_date': fields.Datetime.to_string(q.get('in_date')) if q.get('in_date') else False,
    #                     'quantity': qty,
    #                     'reserved_quantity': rsv,
    #                     'available_quantity': avail,
    #                     'location_id': q['location_id'][0] if q.get('location_id') else False,
    #                     'location_name': loc_map.get(q['location_id'][0], {}).get('complete_name') if q.get('location_id') else False,
    #                 }
    #                 lots_by_product[pid].append(lot_line)
    #         else:
    #             _logger.info("load_brand_location: no van_location for user -> skipping quants")
    #
    #         # ---------------------------------------------------------------------
    #         # 6) Packaging (batch): fetch all once, attach later with computed on_hand
    #         # ---------------------------------------------------------------------
    #         packaging_ids = set()
    #         for p in products:
    #             for pack_id in (p.get('packaging_ids') or []):
    #                 packaging_ids.add(pack_id)
    #
    #         packs_by_product = defaultdict(list)  # pid -> [pack_template, ...]
    #         if packaging_ids:
    #             Pack = request.env['product.packaging'].sudo()
    #             pack_fields = ['name', 'product_uom_id', 'qty', 'product_id']
    #             for rec in Pack.browse(list(packaging_ids)).read(pack_fields):
    #                 uom_id, uom_name = (rec['product_uom_id'] or [False, False])
    #                 pid = rec['product_id'][0] if rec.get('product_id') else False
    #                 if not pid:
    #                     continue
    #                 packs_by_product[pid].append({
    #                     'id': rec['id'],
    #                     'name': rec['name'],
    #                     'uom': uom_name,
    #                     'uom_id': uom_id,
    #                     'qty_per_pack': rec['qty'] or 0.0,  # on_hand_qty computed per product below
    #                 })
    #
    #         # ---------------------------------------------------------------------
    #         # 7) Taxes (first tax only, to match your previous behavior)
    #         # ---------------------------------------------------------------------
    #         first_tax_ids = set()
    #         for p in products:
    #             tax_ids = p.get('taxes_id') or []
    #             if tax_ids:
    #                 first_tax_ids.add(tax_ids[0])
    #
    #         tax_name_by_id = {}
    #         if first_tax_ids:
    #             for rec in request.env['account.tax'].sudo().browse(list(first_tax_ids)).read(['name']):
    #                 tax_name_by_id[rec['id']] = rec['name']
    #
    #         # ---------------------------------------------------------------------
    #         # 8) Build product payloads in one pass & bucket by brand
    #         # ---------------------------------------------------------------------
    #         brand_buckets = OrderedDict()  # brand_id -> {'id','name','products':[]}
    #         all_products_payload = []
    #
    #         for p in products:
    #             pid = p['id']
    #             brand_id, brand_name = (p['brand_id'] or [False, 'Unknown'])
    #             if brand_id not in brand_buckets:
    #                 brand_buckets[brand_id] = {'id': brand_id, 'name': brand_name, 'products': []}
    #
    #             # VAN qty preference (fallback to global)
    #             totals = totals_by_product.get(pid)
    #             if totals:
    #                 available_at_van = max(0.0, totals['quantity'] - totals['reserved'])
    #             else:
    #                 available_at_van = float(p.get('qty_available') or 0.0)
    #
    #             # Packaging with computed on_hand based on available_at_van
    #             packs = packs_by_product.get(pid, [])
    #             # compute on_hand per pack (avoid div by zero)
    #             packaging_data = []
    #             for tmpl in packs:
    #                 qpp = float(tmpl['qty_per_pack'] or 0.0)
    #                 on_hand = int(available_at_van // qpp) if qpp > 0.0 else 0
    #                 packaging_data.append({
    #                     'id': tmpl['id'],
    #                     'name': tmpl['name'],
    #                     'uom': tmpl['uom'],
    #                     'uom_id': tmpl['uom_id'],
    #                     'qty_per_pack': qpp,
    #                     'on_hand_qty': on_hand,
    #                 })
    #
    #             # First tax only (same as your previous code)
    #             tax_ids = p.get('taxes_id') or []
    #             tax_id = tax_ids[0] if tax_ids else False
    #             tax_name = tax_name_by_id.get(tax_id, '') if tax_id else ''
    #
    #             uom_id, uom_name = (p['uom_id'] or [False, ''])
    #             product_payload = {
    #                 'id': pid,
    #                 'name': p.get('name') or '',
    #                 'barcode': p.get('barcode') or '',
    #                 'uom': uom_name,
    #                 'uom_id': uom_id,
    #                 'lst_price': p.get('list_price') or 0.0,
    #                 'taxes_id': tax_id or False,
    #                 'taxes_name': tax_name,
    #                 'item_no': p.get('default_code') or '',
    #                 'description': p.get('description_sale') or '',
    #                 'division': p.get('division') or '',
    #                 'image': f"/web/image/product.product/{pid}/image_512",
    #
    #                 # Global qty (for backward compatibility)
    #                 'quantity_on_hand': p.get('qty_available') or 0.0,
    #
    #                 # VAN/location specifics
    #                 'quantity_on_hand_at_location': float(totals['quantity']) if totals else None,
    #                 'available_qty_at_location': float(available_at_van) if totals else None,
    #                 'location_id': van_location.id if van_location else None,
    #                 'location_name': van_location.complete_name if van_location else None,
    #
    #                 # Per-lot breakdown at the van (or [])
    #                 'lots': lots_by_product.get(pid, []),
    #
    #                 'product_packaging': packaging_data,
    #             }
    #
    #             brand_buckets[brand_id]['products'].append(product_payload)
    #             all_products_payload.append(product_payload)
    #
    #         # 9) Assemble response categories
    #         brand_list = [  # ALL goes first
    #             {'id': -1, 'name': 'ALL', 'products': all_products_payload}
    #         ]
    #         # then each brand in sorted/insertion order
    #         for b in brand_buckets.values():
    #             # Only include non-empty brands (should be all, but just in case)
    #             if b['products']:
    #                 brand_list.append(b)
    #
    #         # 10) UoM list
    #         uom_details = request.env['uom.uom'].sudo().search_read([], ['name'])
    #
    #         return {'success': True, 'data': {'categories': brand_list, 'uom': uom_details}}
    #
    #     except Exception as e:
    #         _logger.exception('Error in /api/v1/load_brand_location:')
    #         return {'success': False, 'error_msg': str(e)}


    @http.route('/api/v1/pre_sale_brand', type='json', auth='none', methods=['POST'], csrf=False)
    def pre_sale_brand_api(self, **kwargs):
        response = {}
        values = request.httprequest.json or {}
        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            partner_id = values.get('partner_id')
            worker_id = values.get('worker_id')

            company = request.env['res.company'].sudo().search([], limit=1)
            partner = request.env['res.partner'].sudo().browse(partner_id) if partner_id else None
            pricelist = partner.with_company(company).property_product_pricelist if partner else None

            # 1. Auth check
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            # 2. Get mapping categories
            user = request.env['res.users'].sudo().browse(user_id)
            # cm = request.env['customer.mapping'].sudo().search([('customer_id', '=', int(partner_id))], limit=1)
            # if not cm:
            #     return {'success': False, 'error_msg': 'No customer mapping found.'}
            domain = [
                ('customer_map_id.customer_id', '=', int(partner_id)),
                ('categ_id', '!=', False)
            ]
            if not worker_id:
                domain.append(('worker_id', '=', user.partner_id.id))
            else:
                domain.append(('worker_id', '=', worker_id))
            worker_obj = request.env['res.partner'].sudo().browse(worker_id)
            divisions = []

            _logger.info(worker_obj)
            _logger.info(worker_id)
            if worker_obj.division_ids:
                divisions = worker_obj.division_ids.mapped('type')
            _logger.info(domain)
            _logger.info(divisions)
            lines = request.env['customer.mapping.line'].sudo().search(domain)
            _logger.info("LINESLLLLLLLLLLLLLLLLSSSSSSSSS")
            _logger.info(lines)
            category_ids = list(set(lines.mapped('categ_id.id')))

            # ... keep your imports, route, and auth exactly as-is ...

            # 3. Loyalty rules map (UNCHANGED start)
            product_to_rules = {}
            promo_groups = request.env['promo.customer.group'].sudo().search([('partner_ids', 'in', [partner_id])])

            if promo_groups:
                for rule in request.env['loyalty.rule'].sudo().search([
                    ('program_id.promo_customer_group_id', 'in', promo_groups.ids),
                    ('active', '=', True)
                ]):
                    for prod in rule.product_ids:
                        if prod.active:
                            product_to_rules.setdefault(prod.id, []).append(rule)

            # ---- NEW: program-level fallback (flat/slab/ladder) so we tag products even without explicit rules
            Program = request.env['loyalty.program'].sudo()

            def _partner_allowed(prog, cust_partner):
                if not cust_partner:
                    return False
                if prog.program_type == 'flat_discount':
                    if prog.flat_apply_customers_options == 'customer_group' and prog.promo_customer_group_id:
                        return cust_partner in prog.promo_customer_group_id.partner_ids
                    if prog.flat_apply_customers_options == 'customer':
                        return cust_partner in prog.flat_customer_ids
                    return True
                # slab/ladder: group-scope if set, else wide
                if prog.promo_customer_group_id:
                    return cust_partner in prog.promo_customer_group_id.partner_ids
                return True

            custom_programs = Program.search([
                ('program_type', 'in', ['ladder_promotion', 'slab_promotion', 'flat_discount']),
                ('active', '=', True),
            ])

            progs_by_product = {}
            progs_by_division = {}
            for prog in custom_programs:
                if not _partner_allowed(prog, partner):
                    continue
                if prog.program_type in ('slab_promotion', 'ladder_promotion'):
                    if prog.promo_product_group_id:
                        for p in prog.promo_product_group_id.product_ids:
                            progs_by_product.setdefault(p.id, []).append(prog)
                elif prog.program_type == 'flat_discount':
                    opt = prog.flat_discount_apply_options
                    if opt == 'products' and prog.flat_product_ids:
                        for p in prog.flat_product_ids:
                            progs_by_product.setdefault(p.id, []).append(prog)
                    elif opt == 'product_group' and prog.promo_product_group_id:
                        for p in prog.promo_product_group_id.product_ids:
                            progs_by_product.setdefault(p.id, []).append(prog)
                    elif opt == 'division' and getattr(prog, 'flat_division', False):
                        progs_by_division.setdefault(prog.flat_division, []).append(prog)
            # ---- END NEW

            # 4. UoM & packaging lookups
            uom_details = [{'id': u.id, 'name': u.name}
                           for u in request.env['uom.uom'].sudo().search([])]
            packaging_list = [{'id': p.id, 'name': p.name, 'uom': p.product_uom_id.name}
                              for p in request.env['product.packaging'].sudo().search([])]

            # 5. Build brand->products dict  (adjust the product search domain)
            brand_dict = {}

            variant_domain = [
                ('sale_ok', '=', True),
                ('product_tmpl_id.type', 'in', ['consu', 'product']),  # was only 'consu'
                ('active', '=', True),
            ]
            if divisions:  # only constrain if worker has divisions
                variant_domain.append(('division', 'in', divisions))

            variants = request.env['product.product'].sudo().search(variant_domain)
            for prod in variants:
                qty = prod.with_user(SUPERUSER_ID).qty_available
                qty = max(qty, 0)

                # packaging breakdown (unchanged)
                packs = []
                for pk in prod.product_tmpl_id.packaging_ids:
                    on_hand = int(qty // pk.qty) if pk.qty > 0 else 0
                    packs.append({
                        'id': pk.id, 'name': pk.name,
                        'uom': pk.product_uom_id.name,
                        'uom_id': pk.product_uom_id.id,
                        'qty_per_pack': pk.qty,
                        'on_hand_qty': on_hand,
                    })

                # --- loyalty info (merge rules + program-level like van endpoint) ---
                rules = product_to_rules.get(prod.id, [])
                fallback_programs = list(progs_by_product.get(prod.id, []) or [])
                prod_div = getattr(prod, 'division', False)
                if prod_div and progs_by_division.get(prod_div):
                    fallback_programs += progs_by_division[prod_div]

                seen_names = set()
                loyalty_info = []
                for r in rules:
                    name = r.program_id.name if r.program_id else False
                    if name and name not in seen_names:
                        loyalty_info.append({'program_name': name})
                        seen_names.add(name)
                for pg in fallback_programs:
                    name = pg.name
                    if name and name not in seen_names:
                        loyalty_info.append({'program_name': name})
                        seen_names.add(name)

                has_loyalty = bool(rules or fallback_programs)

                # price (keep your pricelist logic)
                lst_price = prod.list_price
                try:
                    if pricelist:
                        lst_price = pricelist.sudo()._get_product_price(prod, 1.0)
                except Exception as e:
                    _logger.info(str(e))

                pdata = {
                    'id': prod.id,
                    'name': prod.name,
                    'barcode': prod.barcode or '',
                    'uom': prod.uom_id.name,
                    'uom_id': prod.uom_id.id,
                    'lst_price': lst_price,
                    'taxes_id': prod.taxes_id[:1].id if prod.taxes_id else False,
                    'taxes_name': prod.taxes_id[:1].name if prod.taxes_id else '',
                    'item_no': prod.default_code or '',
                    'description': prod.description_sale or '',
                    'image': self._get_image_url_dynamic(prod._name, prod.id, 'image_512'),
                    'quantity_on_hand': qty,
                    'product_packaging': packs,
                    'is_loyalty_product': has_loyalty,
                    'loyalty_info': loyalty_info,
                }

                # --- don’t drop unbranded items ---
                bid = prod.brand_id.id if prod.brand_id else 0
                bname = prod.brand_id.name if prod.brand_id else 'Unbranded'
                brand_dict.setdefault(bid, {'id': bid, 'name': bname, 'products': []})
                brand_dict[bid]['products'].append(pdata)

            # 6. Convert to list (no stock filter change; keep as you had)
            brand_list = []
            for b in brand_dict.values():
                # filtered = [p for p in b['products'] if p['quantity_on_hand'] > 0]
                filtered = [p for p in b['products']]
                if filtered:
                    b['products'] = filtered
                    brand_list.append(b)

            # 7. Build ALL category (deduped) (unchanged)
            seen = set()
            all_prods = []
            for b in brand_list:
                for p in b['products']:
                    if p['id'] not in seen:
                        seen.add(p['id'])
                        all_prods.append(p)
            if all_prods:
                brand_list.insert(0, {'id': -1, 'name': 'ALL', 'products': all_prods})

            warehouse_ids = request.env['stock.warehouse'].sudo().search([])

            warehouses = []
            for warehouse in warehouse_ids:
                warehouses.append({"id": warehouse.id, "name": warehouse.name})

            # 8. Final response
            response = {
                'success': True,
                'data': {
                    'categories': brand_list,
                    'uom': uom_details,
                    'product_packaging': packaging_list,
                    'locations': warehouses,
                }
            }

        except Exception as e:
            _logger.exception('Error in /api/v1/pre_sale_brand')
            response = {'success': False, 'error_msg': str(e)}

        return response


    @http.route('/api/v1/create_pre_sale_order_request', type='json', auth='public', methods=['POST'], csrf=False)
    def create_pre_sale_order_request(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = values.get('sale_order_id')
            is_active = values.get('is_active', False)
            location_id = values.get('location_id', False)
            commitment_date = values.get('commitment_date', False)
            po_number = values.get('po_number', False)
            warehouse_id = values.get('warehouse_id', False)
            worker_id = values.get('worker_id', 0)

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': f'Invalid user_id: {user_id}'}
            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)

            if not sale_order.exists():
                return {'success': False, 'error_msg': f"Invalid sale_order_id: {sale_order_id}"}

            if worker_id != 0:
                sale_order.assign_to = worker_id
                sale_order.write({"assign_to": worker_id})
                crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [worker_id])],
                                                                 limit=1)
                if crm_team:
                    sale_order.write({'team_id': crm_team.id})

                # worker_obj = request.env['res.partner'].sudo().browse(worker_id)
                # if worker_obj:
                #     internal_user = worker_obj.internal_user
                #     if internal_user:
                #         sale_order.write({"user_id": internal_user.id})
            # if user:
            #     sale_order.sudo().write({'user_id': user.id})
            if warehouse_id:
                sale_order.warehouse_id = warehouse_id
            if po_number:
                sale_order.po_number = po_number

            if commitment_date:
                sale_order.commitment_date = commitment_date

            if is_active:
                sale_order.write({'active': True})
                # Confirm as the real user, with tracking & mail disabled to avoid message_post() paths
                if sale_order.is_discount_panding:
                    sale_order.approve_discount()

                sale_order.with_user(SUPERUSER_ID).with_context(
                    tracking_disable=True,  # disable _message_track
                    mail_notrack=True,  # belt
                    mail_create_nosubscribe=True,  # no auto-follow
                    mail_post_autofollow=False,  # no followers
                    mail_auto_delete=True,  # skip queue
                    mail_activity_automation_skip=True,
                ).sudo().action_confirm()
                # sale_order.with_user(user).sudo().action_confirm()

            line_info = [{
                'product_id': line.product_id.id,
                'product_name': line.name,
                'qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'uom_id': line.product_uom.id,
                'uom_name': line.product_uom.name,
                'code': line.product_id.default_code,
                'barcode': line.product_id.barcode,
                'tax_id': line.tax_id.id,
                'tax_name': line.tax_id.name,
                'product_packaging_qty': line.product_packaging_qty,
                'product_packaging_id': line.product_packaging_id.id,
                'product_packaging_name': line.product_packaging_id.name,
                'price_total': line.price_total,
                'is_reward_line': line.is_reward_line,
            } for line in sale_order.order_line]

            response = {
                'success': True,
                'message': f'Sale order {sale_order.name} activated and confirmed.',
                'sale_order': {
                    'id': sale_order.id,
                    'name': sale_order.name,
                    'amount_untaxed': sale_order.amount_untaxed,
                    'amount_tax': sale_order.amount_tax,
                    'amount_total': sale_order.amount_total,
                    'lines': line_info,
                }
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/create_pre_sale_order_request")
            response = {'success': False, 'error_msg': str(e)}

        return response

    @http.route('/api/v1/load_warehouses_vanlocation_location', type='json', auth='none', methods=['POST'])
    def load_warehouses_vanlocation_location(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {
                    'success': False,
                    'error_msg': 'Invalid or expired auth token.'
                }
            user = request.env['res.users'].sudo().browse(user_id)
            partner = user.partner_id
            van_sub_location = partner.van_location
            if van_sub_location:
                all_warehouses = request.env['stock.warehouse'].sudo().browse(van_sub_location.warehouse_id.id)
            else:
                all_warehouses = request.env['stock.warehouse'].sudo().search([])
            warehouse_details = [{'id': w.id, 'name': w.name} for w in all_warehouses]

            response.update({
                'success': True,
                'data': {
                    'warehouse_details': warehouse_details,

                }
            })

        except Exception as e:
            response.update({
                'success': False,
                'error_msg': str(e)
            })
            _logger.exception('Failed to load product/warehouse/location data.')

        return response
    @http.route('/api/v1/dashboard_load_screen', type='json', auth='none', methods=['POST'])
    def customer_dashboard_load_screen(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            query_params = parse_qs(request.httprequest.query_string.decode('utf-8'))

            page = int(query_params.get('page', [1])[0])
            limit = 10
            offset = (page - 1) * limit

            user_id = values.get('user_id')
            auth_token = values.get('auth_token')

            # Token validation
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {
                    'success': False,
                    'error_msg': 'Invalid or expired auth token.'
                }

            user = request.env['res.users'].sudo().browse(user_id)
            all_sales = request.env['sale.order'].sudo().search([
                ('user_id', '=', user.id),
                ('state', '=', 'sale')
            ])
            total_sales = len(all_sales)
            paged_sales = all_sales[offset:offset + limit]

            sale_details = []
            for order in paged_sales:
                for line in order.order_line:
                    order = line.order_id
                    product = line.product_id
                    warehouse = order.warehouse_id
                    location = product.property_stock_inventory

                    sale_details.append({
                        'order_id': order.id,
                        'order_name': order.name,
                        'partner_id': order.partner_id.id if order.partner_id else False,
                        'product_id': product.id,
                        'product_name': product.name,
                        'warehouse_id': warehouse.id if warehouse else False,
                        'warehouse_name': warehouse.name if warehouse else 'No Warehouse',
                        'location_id': location.id if location else False,
                        'location_name': location.display_name if location else 'No Location',
                        'quantity': line.product_uom_qty,
                    })

            # Build response
            response.update({
                'success': True,
                'data': {
                    'user_id': user.id,
                    'user_name': user.name,
                    'total_sales': total_sales,
                    'sale_order_details': sale_details,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'offset': offset,
                        'total_sales': total_sales,
                    }
                }
            })

        except Exception as e:
            response.update({
                'success': False,
                'error_msg': str(e)
            })
            _logger.exception('Failed to load dashboard.')

        return response

    @http.route('/api/v1/dashboard_offload', type='json', auth='none', methods=['POST'])
    def dashboard_offload(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)

            van_locations = request.env['stock.location'].sudo().search([
                ('usage', '=', 'internal'),
                ('responsible_id', '=', user.id)
            ])
            van_location_ids = van_locations.ids

            if not van_location_ids:
                return {'success': False, 'error_msg': 'No van locations assigned to user.'}

            sale_orders = request.env['sale.order'].sudo().search([
                ('state', '=', 'sale'),
                ('picking_ids.state', '=', 'done'),
                ('picking_ids.location_id', 'in', van_location_ids),
            ])

            warehouses = request.env['stock.warehouse'].sudo().search([])

            def find_warehouse(location):
                while location:
                    for wh in warehouses:
                        if location == wh.view_location_id:
                            return wh
                    location = location.location_id
                return None

            sale_orders_data = []

            for order in sale_orders:
                product_lines = []
                product_ids = order.order_line.mapped('product_id').ids

                quants = request.env['stock.quant'].sudo().search([
                    ('product_id', 'in', product_ids),
                    ('location_id', 'in', van_location_ids)
                ])
                quant_map = {}
                for quant in quants:
                    quant_map[quant.product_id.id] = quant_map.get(quant.product_id.id, 0) + quant.quantity

                for line in order.order_line:
                    product = line.product_id
                    product_lines.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'on_hand_qty': quant_map.get(product.id, 0),
                    })

                delivered_locations = []
                for picking in order.picking_ids.filtered(
                        lambda p: p.state == 'done' and p.location_id.id in van_location_ids):
                    location = picking.location_id
                    warehouse = find_warehouse(location)
                    delivered_locations.append({
                        'location_id': location.id,
                        'location_name': location.display_name,
                        'warehouse_id': warehouse.id if warehouse else False,
                        'warehouse_name': warehouse.name if warehouse else False
                    })

                sale_orders_data.append({
                    'order_id': order.id,
                    'order_name': order.name,
                    'customer_name': order.partner_id.name,
                    'delivered_locations': delivered_locations,
                    'product_lines': product_lines,
                })
            stock_quant = request.env['stock.quant']._get_available_quantity(product, location)
            response.update({
                'success': True,
                'data': {
                    'user_id': user.id,
                    'user_name': user.name,
                    'sale_orders': sale_orders_data
                }
            })

        except Exception as e:
            _logger.exception("Failed to load dashboard_offload data.")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    @http.route('/api/v1/dashboard_merchandise', type='json', auth='none', methods=['POST'])
    def dashboard_merchandise(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {
                    'success': False,
                    'error_msg': 'Invalid or expired auth token.'
                }

            user = request.env['res.users'].sudo().browse(user_id)
            fsm_orders = request.env['fsm.order'].sudo().with_user(SUPERUSER_ID).search(
                [('person_id_partner', '=', user.partner_id.id)])
            total_visits = len(fsm_orders)

            completed_stage = request.env['fsm.stage'].sudo().search([('name', '=', 'Completed')], limit=1)
            completed_visits = fsm_orders.filtered(lambda o: o.stage_id.id == completed_stage.id)

            completed_visits_count = len(completed_visits)
            remaining_visits = total_visits - completed_visits_count

            response.update({
                'success': True,
                'data': {
                    'user_id': user.id,
                    'user_name': user.name,
                    'total_visits': total_visits,
                    'pending_visits': remaining_visits,
                    'completed_visits': len(completed_visits),
                }
            })

        except Exception as e:
            response.update({
                'success': False,
                'error_msg': str(e)
            })
            _logger.info('Failed to open the dashboard.')
        return response


    @http.route('/api/v1/product/details', type='json', auth='none', methods=['POST'])
    def product_details_api(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            product_id = values.get('product_id')

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {
                    'success': False,
                    'error_msg': 'Invalid or expired auth token.'
                }

            if not product_id:
                return {
                    'success': False,
                    'error_msg': 'Missing product_id.'
                }

            product = request.env['product.template'].sudo().browse(int(product_id))
            if not product.exists() or not product.active:
                return {
                    'success': False,
                    'error_msg': 'Product not found.'
                }
            main_image = ''
            if product.image_1920:
                main_image = self._get_image_url_dynamic(model=product._name, record_id=product.id,
                                                         field_name='image_128'),

            product_data = {
                'name': product.name or '',
                'serial_no': product.default_code or '',
                'item_no': product.id,
                'description': product.description_sale or '',
                'main_image': main_image,
                'thumbnails': [main_image] if main_image else []
            }

            response.update({
                'success': True,
                'data': product_data
            })

        except Exception as e:
            _logger.exception('Error in product details API.')
            response.update({
                'success': False,
                'error_msg': str(e)
            })

        return response

    @http.route('/api/v1/create_stock_request', type='json', auth='none', methods=['POST'])
    def create_stock_request(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            warehouse_id = values.get('warehouse_id')
            partner_id = user.partner_id
            product_lines = values.get('products', [])

            if not warehouse_id:
                return {'success': False, 'error_msg': 'Warehouse ID is required.'}

            warehouse = request.env['stock.warehouse'].sudo().browse(warehouse_id)
            source_location = warehouse.lot_stock_id

            if not source_location:
                return {'success': False, 'error_msg': 'No lot stock location defined for the warehouse.'}

            destination_location = request.env['stock.location'].sudo().search([
                ('responsible_id', '=', user.id),
                ('usage', '=', 'internal'),
                ('location_id', '=', source_location.id)
            ])

            if not destination_location:
                destination_location = request.env['stock.location'].sudo().search([
                    ('responsible_id', '=', user.id),
                    ('usage', '=', 'internal'),
                    ('location_id', 'child_of', source_location.id)
                ])

            if not destination_location:
                destination_location = request.env['stock.location'].sudo().search([
                    ('location_id', '=', source_location.id),
                    ('usage', '=', 'internal')
                ])

            if not destination_location:
                destination_location = source_location

            if destination_location and len(destination_location) > 1:
                destination_location = destination_location[0]

            stock_request_lines = []

            for line in product_lines:
                if not all(k in line for k in ('product_id', 'quantity')):
                    return {'success': False, 'error_msg': 'Each product line must include product_id and quantity.'}

                product_id = line['product_id']
                quantity = line['quantity']
                packaging_id = line.get('product_packaging_id')
                uom_id = line.get('product_uom_id')
                product_packaging_id = line.get('product_packaging_id')
                product_packaging_qty = line.get('product_packaging_qty')

                product = request.env['product.product'].sudo().browse(product_id)
                if not product or not product.exists() or not product.active:
                    # Try resolving from product template
                    template = request.env['product.template'].sudo().browse(product_id)
                    if template.exists() and template.product_variant_ids and template.active:
                        product = template.product_variant_ids[0]
                    else:
                        return {
                            'success': False,
                            'error_msg': f"Invalid product ID: {product_id}"
                        }
                final_quantity = quantity
                final_uom_id = uom_id
                product_packaging = None

                if packaging_id:
                    if isinstance(packaging_id, str):
                        packaging_id = int(packaging_id.split(',')[0])
                    elif isinstance(packaging_id, list):
                        packaging_id = packaging_id[0]
                    product_packaging = request.env['product.packaging'].sudo().browse(packaging_id)
                    if product_packaging.exists():
                        final_quantity = quantity * product_packaging.qty
                        final_uom_id = product_packaging.product_uom_id.id
                    else:
                        return {
                            'success': False,
                            'error_msg': f"Invalid packaging ID {packaging_id} for product {product.id}"
                        }
                else:
                    if not final_uom_id:
                        return {
                            'success': False,
                            'error_msg': 'Missing product_uom_id when no product_packaging_id is given.'
                        }
                line_vals = {
                    'product_id': product.id,
                    'product_uom_qty': final_quantity,
                    'qty_done': final_quantity,
                    'product_uom_id': final_uom_id,
                    'warehouse_id': warehouse.id,
                    'location_id': source_location.id,
                    'requested_by': user.id,
                    'company_id': warehouse.company_id.id,
                }
                if product_packaging_id:
                    line_vals['product_packaging_id'] = product_packaging_id
                if product_packaging_qty:
                    line_vals['product_packaging_qty'] = product_packaging_qty

                if 'product_packaging_id' in request.env['stock.request']._fields and product_packaging:
                    line_vals['product_packaging_id'] = product_packaging.id

                stock_request_lines.append((0, 0, line_vals))

            stock_request = request.env['stock.request.order'].with_user(user.id).sudo().create({
                'direction': 'van_load',
                'customer_id': partner_id.id,
                'requested_by': user.id,
                'warehouse_id': warehouse.id,
                'location_id': source_location.id,
                'company_id': warehouse.company_id.id,
                'destination_id': destination_location.id,
                'stock_request_ids': stock_request_lines,
            })

            try:
                stock_request.action_submit()
            except Exception as confirm_err:
                _logger.warning("Stock request created but failed to confirm: %s", str(confirm_err))
                response.update({
                    'success': True,
                    'message': 'Stock request created but not auto-confirmed.',
                    'stock_request_id': stock_request.id,
                    'stock_request_name': stock_request.name,
                    'warning': 'Could not auto-confirm stock request.'
                })
                return response

            response.update({
                'user_id': user.id,
                'user_name': user.name,
                'partner_id':partner_id.id,
                'partner_name':partner_id.name,
                'success': True,
                'message': 'Stock request order created and confirmed successfully.',
                'stock_request_id': stock_request.id,
                'stock_request_name': stock_request.name,
            })

        except Exception as e:
            response.update({'success': False, 'error_msg': str(e)})
            _logger.exception("Error in /create_stock_request")

        return response

    @http.route('/api/v1/in_route', type='json', auth='none', methods=['POST'], csrf=False)
    def get_in_route(self, **kwargs):
        values = request.httprequest.json
        user_id = values.get('user_id')
        worker_id = values.get('worker_id')
        auth_token = values.get('auth_token')

        token_valid = request.env['mobile.auth.token'].sudo().search([
            ('user_id', '=', user_id),
            ('mobile_app_auth_token', '=', auth_token)
        ], limit=1)

        if not token_valid:
            return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

        user = request.env['res.users'].sudo().browse(user_id)
        env = request.env(user=user)
        company_ctx = {
            'company_id': user.company_id.id,
            'allowed_company_ids': [user.company_id.id],
        }

        fsm_order_obj = env['fsm.order'].sudo().with_context(company_ctx)
        if worker_id and user.user_type != 'sales_user':
            partner = request.env['res.partner'].sudo().browse(worker_id)
        else:
            partner = user.partner_id

        in_route = fsm_order_obj.search([
            ('route_status', '=', 'inRoute'),
            ('person_id_partner', '=', partner.id)
        ])
        van_locations = request.env['stock.location'].sudo().search([
            ('responsible_id', '=', user.id),
            ('usage', '=', 'internal')
        ])

        warehouse_ids = []
        warehouse_id = van_locations.warehouse_id
        if len(warehouse_id) > 1:
            warehouse_id = warehouse_id[0]
        today = Datetime.now()
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = []
        for order in in_route:
            customer = order.customer_id.with_context(company_ctx)
            pickings = request.env['stock.picking'].sudo().search([
                ('picking_driver_id', '=', partner.id),
                ('partner_id','child_of',customer.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'not in', ['cancel', 'done']),
                ('scheduled_date', '>=', start),
                ('scheduled_date', '<', end),
            ], limit=1)
            picking_list = []
            for picking in pickings:
                sale_order = request.env['sale.order'].sudo().search([
                    ('procurement_group_id', '=', picking.group_id.id)
                ], limit=1) if picking.group_id else None
                if sale_order:
                    picking_list.append({
                        'picking_id': picking.id,
                        # 'picking_name': picking.name,
                        # 'state': picking.state,
                        # 'scheduled_date': picking.scheduled_date,
                        # 'sale_order_id': sale_order.id if sale_order else False,
                        # 'sale_order_name': sale_order.name if sale_order else '',
                    })
            credit_hold_reason = ""
            if customer.customer_type == 'credit' and customer.is_credit_hold and customer.credit_hold_reason_id:
                credit_hold_reason = customer.credit_hold_reason_id.name
            result.append({
                'InRoutes': order.id,
                'visit_id': order.id,
                'fsm_order_id': order.id,
                'id': order.id,
                'customer_name': customer.name or '',
                'customer_id': customer.id,
                'customer_code': customer.customer_code or '',
                'followup_status': dict(customer._fields['followup_status'].selection).get(customer.followup_status, ''),
                "trn_no": customer.vat_trn,
                "reference":customer.ref,
                "external_reference": customer.external_ref,
                "outlet_code": customer.outlet_code,
                "outlet_short_name": customer.outlet_short_name,
                "trx_ref": customer.id,
                "latitude": customer.latitude,
                "longitude": customer.longitude,
                "partner_latitude": customer.partner_latitude,
                "partner_longitude": customer.partner_longitude,
                'street': customer.street or '',
                'street2': customer.street2 or '',
                'city': customer.city or '',
                'customer_type': customer.customer_type or '',
                "contact_address": customer.contact_address,
                "contact_address_complete": customer.contact_address_complete,
                "contact_address_inline": customer.contact_address_inline,
                "detailed_address": customer.detailed_address,
                "peppol_eas": customer.peppol_eas,
                'state_id': customer.state_id.id if customer.state_id else 0,
                'state_name': customer.state_id.name if customer.state_id else '',
                'state_code': customer.state_id.code if customer.state_id else '',
                'country_id': customer.country_id.id if customer.country_id else 0,
                'country_name': customer.country_id.name if customer.country_id else '',
                'country_code': customer.country_id.code if customer.country_id else '',
                'zip': customer.zip or '',
                'ref': order.order_activity_ids[:1].ref or '',
                "department_id": customer.department.id,
                "department_name": customer.department.name,
                'order_number': order.name,
                'credit_limit': customer.credit_limit or 0,
                'is_credit_hold': customer.is_credit_hold,
                'credit_hold_reason': credit_hold_reason,
                'total_overdue': customer.total_overdue or 0,
                'department': customer.department.name if customer.department else '',
                'visits': order.customer_visits or 0,
                'date_start': order.date_start,
                'date_end': order.date_end,
                'duration': order.duration,
                'picking_id': picking_list[0]['picking_id'] if picking_list else False,
                'location_to_name': order.location_id.name if order.location_id else "",
                'location_to_street': order.location_id.street if order.location_id.street else "",
                'ship_to_name': order.location_id.shipping_address_id.name if order.location_id and order.location_id.shipping_address_id.name else "",
                'ship_to_id': order.location_id.shipping_address_id.id if order.location_id else "",
                'ship_to_street': order.location_id.shipping_address_id.street if order.location_id.shipping_address_id.street else "",
                'ship_to_customer_code': order.location_id.shipping_address_id.customer_code if order.location_id.shipping_address_id.customer_code else "",
            })

        return {
            'success': True,
            'total_count': len(result),
            'warehouse_id':warehouse_id.id,
            'data': result
        }

    @http.route('/api/v1/out_route', type='json', auth='none', methods=['POST'], csrf=False)
    def get_out_route(self, **kwargs):
        """
        New flow:
        1. Validate user / token (unchanged).
        2. Grab partner (driver) from user.
        3. Pull all customer.mapping.line where worker_id == partner.
        4. From each line’s header (customer_map_id) collect the customer_id.
        5. For every customer build the payload + first open picking (if any).
        """
        values = request.httprequest.json or {}
        user_id     = values.get('user_id')
        auth_token  = values.get('auth_token')
        partner_id  = values.get('partner_id', 0)

        # 1️⃣  Auth check – don’t touch.
        token_ok = request.env['mobile.auth.token'].sudo().search([
            ('user_id', '=', user_id),
            ('mobile_app_auth_token', '=', auth_token)
        ], limit=1)
        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            return {'success': False, 'error_msg': 'User not found.'}
        if not token_ok:
            return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

        # Build an env as *that* user, but still super-powered.
        env = request.env(user=user)
        company_ctx = {
            'company_id': user.company_id.id,
            'allowed_company_ids': [user.company_id.id],
        }

        if user.user_type != 'sales_user' and partner_id != 0:
            partner = request.env['res.partner'].sudo().browse(partner_id)

        else:
            partner = user.partner_id                     # 👈 driver / merchandiser
        today = Datetime.now()
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = start + timedelta(days=1)

        # 2️⃣  NEW SECTION – map lines ➜ customers
        line_obj = env['customer.mapping.line'].sudo().with_context(company_ctx)
        lines = line_obj.search([('worker_id', '=', partner.id)])

        # Map header → customer(s)
        customers = lines.mapped('customer_map_id.customer_id').sudo().with_context(company_ctx)

        # Warehouse – same trick you already used.
        van_locations = request.env['stock.location'].sudo().search([
            ('responsible_id', '=', user.id),
            ('usage', '=', 'internal')
        ], limit=1)              # usually one van per driver
        warehouse_id = False
        if van_locations and len(van_locations) > 0:
            warehouse_id = van_locations.warehouse_id
            if len(warehouse_id) > 1:
                warehouse_id = warehouse_id[0]

        picking_obj = request.env['stock.picking'].sudo()

        result = []

        i = 0
        for cust in customers.sorted(key=lambda c: c.name.lower()):
            # 🔍 Find the mapping line that links this customer to its header (customer_map)
            mapping_line = lines.filtered(lambda l: l.customer_map_id.customer_id.id == cust.id)
            customer_map = mapping_line.customer_map_id if mapping_line else None

            i += 1

            # 💥 Fetch header details
            # location_id = customer_map.location_id[0].id if customer_map and customer_map.location_id else i
            # customer_map_id = customer_map[0].id if customer_map else False

            # Grab *one* outstanding outgoing picking for today (if any)
            picking = picking_obj.search([
                ('picking_driver_id', '=', partner.id),
                ('partner_id', 'child_of', cust.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'not in', ['cancel', 'done']),
                ('scheduled_date', '>=', start),
                ('scheduled_date', '<', end),
            ], limit=1)
            credit_hold_reason = ""
            if cust.customer_type == 'credit' and cust.is_credit_hold and cust.credit_hold_reason_id:
                credit_hold_reason = cust.credit_hold_reason_id.name
            for customer_map_id in customer_map:
                for location_id in customer_map_id.location_id:
                    result.append({
                        # Basic customer profile
                        'customer_id': cust.id,
                        'customer_name': cust.name or '',
                        'customer_code': cust.customer_code or '',
                        'followup_status': dict(cust._fields['followup_status'].selection).get(cust.followup_status, ''),
                        'trn_no': cust.vat_trn,
                        'reference': cust.ref,
                        'external_reference': cust.external_ref,
                        'outlet_code': cust.outlet_code,
                        'outlet_short_name': cust.outlet_short_name,
                        'trx_ref': cust.id,
                        'latitude': cust.latitude,
                        'longitude': cust.longitude,
                        'partner_latitude': cust.partner_latitude,
                        'partner_longitude': cust.partner_longitude,
                        'street': f"{cust.street or ''} {cust.street2 or ''}".strip(),
                        'city': cust.city or '',
                        'contact_address': cust.contact_address,
                        'contact_address_complete': cust.contact_address_complete,
                        'contact_address_inline': cust.contact_address_inline,
                        'detailed_address': cust.detailed_address,
                        'peppol_eas': cust.peppol_eas,
                        'customer_type': cust.customer_type or '',
                        'state_id': cust.state_id.id if cust.state_id else 0,
                        'state_name': cust.state_id.name if cust.state_id else '',
                        'state_code': cust.state_id.code if cust.state_id else '',
                        'country_id': cust.country_id.id if cust.country_id else 0,
                        'country_name': cust.country_id.name if cust.country_id else '',
                        'country_code': cust.country_code or '',
                        'zip': cust.zip or '',
                        # Department & credit bits
                        'department_id': cust.department.id if cust.department else 0,
                        'department_name': cust.department.name if cust.department else '',
                        'credit_limit': cust.credit_limit or 0,
                        'is_credit_hold': cust.is_credit_hold,
                        'credit_hold_reason': credit_hold_reason,
                        'total_overdue': cust.total_overdue or 0,
                        # Today’s first open picking (or False)
                        'picking_id': picking.id if picking else False,
                        # ✅ Newly added fields:
                        'customer_map_id': customer_map_id,
                        'location_id': location_id,
                        'id': location_id,
                        'location_to_name': location_id.location_name if location_id and location_id.location_name else "",
                        'location_to_street': location_id.street if location_id.street else "",
                        'ship_to_name': location_id.shipping_address_id.name if location_id and location_id.shipping_address_id.name else "",
                        'location_to_id': location_id.id if location_id else "",
                        'ship_to_id': location_id.shipping_address_id.id if location_id else "",
                        'ship_to_street': location_id.shipping_address_id.street if location_id.shipping_address_id.street else "",
                        'ship_to_customer_code': location_id.shipping_address_id.customer_code if location_id.shipping_address_id.customer_code else "",
                    })

        return {
            'success': True,
            'warehouse_id': warehouse_id.id if warehouse_id else False,
            'total_count': len(result),
            'data': result,
        }


    @http.route('/api/v1/product_category_deliver_to', type='json', auth='none', methods=['POST'])
    def load_current_stock_only(self, **kwargs):
        response = {}
        values = request.httprequest.json or {}

        def _date_to_str(d):
            return d.strftime('%Y-%m-%d') if d else False

        try:
            # --- Auth check ---
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            # --- Prepare user & locations ---
            user = request.env['res.users'].sudo().browse(user_id)
            user_locations = request.env['stock.location'].sudo().search([
                ('usage', '=', 'internal'),
                ('responsible_id', '=', user.id)
            ])

            delivery_location_data = []
            total_product_count = 0

            # --- Warehouses list ---
            all_warehouses = request.env['stock.warehouse'].sudo().search([])
            warehouse_details = [{'id': w.id, 'name': w.name} for w in all_warehouses]

            # --- Loop each location ---
            for loc in user_locations:
                quants = request.env['stock.quant'].sudo().search([('location_id', '=', loc.id)])

                # Map: product_id -> {'product': rec, 'quants': [quant,...],
                #                     'by_lot': {lot_id: [quant,...]},
                #                     'by_package': {package_id: [quant,...]},
                #                     'by_lot_package': {lot_id: {package_id: [quant,...]}}}
                product_map = {}

                for q in quants:
                    product = q.product_id
                    # keep your original filters
                    if not (product.sale_ok and product.type == 'consu' and product.active):
                        continue

                    entry = product_map.setdefault(product.id, {
                        'product': product,
                        'quants': [],
                        'by_lot': {},
                        'by_package': {},
                        'by_lot_package': {},
                    })
                    entry['quants'].append(q)

                    # lot grouping
                    if q.lot_id:
                        entry['by_lot'].setdefault(q.lot_id.id, []).append(q)

                    # package grouping
                    if q.package_id:
                        entry['by_package'].setdefault(q.package_id.id, []).append(q)
                        if q.lot_id:
                            entry['by_lot_package'].setdefault(q.lot_id.id, {}).setdefault(q.package_id.id, []).append(
                                q)

                product_totals = {}

                # --- Build per-product totals, packaging, lots, and packages ---
                for pid, payload in product_map.items():
                    product = payload['product']
                    p_quants = payload['quants']  # Python list

                    # totals (use python sums)
                    qty_available = sum(q.quantity for q in p_quants)
                    reserved_total = sum(q.reserved_quantity for q in p_quants)
                    if qty_available <= 0:
                        continue

                    # Product packaging (product.packaging)
                    packaging_data = []
                    for packaging in product.packaging_ids:
                        qty_in_packaging = int(qty_available // packaging.qty) if packaging.qty > 0 else 0
                        packaging_data.append({
                            'id': packaging.id,
                            'name': packaging.name,
                            'uom': packaging.product_uom_id.name,
                            'uom_id': packaging.product_uom_id.id,
                            'qty_per_pack': packaging.qty,
                            'on_hand_qty': qty_in_packaging,
                        })

                    # Helper to serialize a package group
                    def _serialize_package_group(package, quant_list, lot=None):
                        qty = sum(lq.quantity for lq in quant_list)
                        reserved = sum(lq.reserved_quantity for lq in quant_list)
                        available = qty - reserved
                        return {
                            'package_id': package.id,
                            'package_name': getattr(package, 'name', '') or getattr(package, 'display_name', ''),
                            'package_type': package.package_type_id.display_name if getattr(package, 'package_type_id',
                                                                                            False) else '',
                            'package_type_id': package.package_type_id.id if getattr(package, 'package_type_id',
                                                                                     False) else False,
                            'lot_id': lot.id if lot else False,
                            'lot_name': lot.name if lot else '',
                            'qty': qty,
                            'reserved_qty': reserved,
                            'available_qty': available,
                            'location_id': loc.id,
                            'location_name': loc.complete_name,
                        }

                    # Per-lot data (with nested packages for tracked products)
                    lots_data = []
                    if product.tracking != 'none':
                        for lot_id, lot_quants in payload['by_lot'].items():
                            lot = lot_quants[0].lot_id
                            qty = sum(lq.quantity for lq in lot_quants)
                            reserved = sum(lq.reserved_quantity for lq in lot_quants)
                            available = qty - reserved

                            # packages under this lot
                            lot_packages = []
                            lot_pkg_map = payload['by_lot_package'].get(lot_id, {})
                            for pkg_id, pkg_quants in lot_pkg_map.items():
                                package = pkg_quants[0].package_id
                                lot_packages.append(_serialize_package_group(package, pkg_quants, lot=lot))

                            # NEW: add unpackaged remainder inside this lot (if any)
                            unpkg_quants_lot = [lq for lq in lot_quants if not lq.package_id]
                            if unpkg_quants_lot:
                                unpkg_qty = sum(lq.quantity for lq in unpkg_quants_lot)
                                unpkg_reserved = sum(lq.reserved_quantity for lq in unpkg_quants_lot)
                                lot_packages.append({
                                    'package_id': False,
                                    'package_name': 'Unpackaged',
                                    'package_type': '',
                                    'package_type_id': False,
                                    'lot_id': lot.id,
                                    'lot_name': lot.name,
                                    'qty': unpkg_qty,
                                    'reserved_qty': unpkg_reserved,
                                    'available_qty': unpkg_qty - unpkg_reserved,
                                    'location_id': loc.id,
                                    'location_name': loc.complete_name,
                                })

                            lots_data.append({
                                'lot_id': lot.id,
                                'lot_name': lot.name,
                                'tracking': product.tracking,
                                'qty': qty,
                                'reserved_qty': reserved,
                                'available_qty': available,
                                'use_date': _date_to_str(getattr(lot, 'use_date', False)),
                                'removal_date': _date_to_str(getattr(lot, 'removal_date', False)),
                                'alert_date': _date_to_str(getattr(lot, 'alert_date', False)),
                                'expiration_date': _date_to_str(getattr(lot, 'expiration_date', False)),
                                'is_salable': lot.is_salable,
                                'packages': lot_packages,
                            })

                        # soonest expiry first
                        lots_data.sort(key=lambda l: (l['expiration_date'] or '9999-12-31', l['lot_name'] or ''))

                    # Product-level packages (aggregated across all lots/untracked)
                    packages_data = []
                    for pkg_id, pkg_quants in payload['by_package'].items():
                        package = pkg_quants[0].package_id
                        packages_data.append(_serialize_package_group(package, pkg_quants, lot=None))

                    # NEW: add product-level unpackaged remainder if any
                    unpkg_quants_prod = [q for q in p_quants if not q.package_id]
                    if unpkg_quants_prod:
                        unpkg_qty_prod = sum(q.quantity for q in unpkg_quants_prod)
                        unpkg_reserved_prod = sum(q.reserved_quantity for q in unpkg_quants_prod)
                        packages_data.append({
                            'package_id': False,
                            'package_name': 'Unpackaged',
                            'package_type': '',
                            'package_type_id': False,
                            'lot_id': False,
                            'lot_name': '',
                            'qty': unpkg_qty_prod,
                            'reserved_qty': unpkg_reserved_prod,
                            'available_qty': unpkg_qty_prod - unpkg_reserved_prod,
                            'location_id': loc.id,
                            'location_name': loc.complete_name,
                        })

                    brand_id = product.brand_id.id if product.brand_id else 0
                    brand_name = product.brand_id.name if product.brand_id else "Unbranded"

                    product_totals[product.id] = {
                        'id': product.id,
                        'name': product.name,
                        'barcode': product.barcode or '',
                        'uom': product.uom_id.name,
                        'uom_id': product.uom_id.id,
                        'lst_price': product.list_price,
                        'taxes_id': product.taxes_id.id if product.taxes_id else False,
                        'taxes_name': product.taxes_id.name if product.taxes_id else '',
                        'item_no': product.default_code or '',
                        'description': product.description_sale or '',
                        'image': self._get_image_url_dynamic(
                            model=product._name,
                            record_id=product.id,
                            field_name='image_512'
                        ),
                        'quantity_on_hand': qty_available,
                        'product_packaging': packaging_data,
                        'lots': lots_data,
                        'packages': packages_data,
                        'location_id': loc.id,
                        'location_name': loc.complete_name,
                        'category_id': brand_id,
                        'category_name': brand_name,
                    }

                # --- Organize brands + collect ALL ---
                brand_map = {}
                all_products = []

                for prod in product_totals.values():
                    b_id = prod['category_id']
                    b_name = prod['category_name']
                    brand_map.setdefault(b_id, {
                        'category_id': b_id,
                        'category_name': b_name,
                        'products': []
                    })['products'].append(prod)

                    all_products.append(prod)
                    total_product_count += 1

                categories = []
                if all_products:
                    categories.append({
                        'category_id': -1,
                        'category_name': 'ALL',
                        'products': all_products
                    })
                for group in brand_map.values():
                    categories.append(group)

                if categories:
                    delivery_location_data.append({
                        'id': loc.id,
                        'name': loc.complete_name,
                        'categories': categories
                    })

            response.update({
                'success': True,
                'data': {
                    'total_product_count': total_product_count,
                    'delivery_locations': delivery_location_data,
                    'warehouse_details': warehouse_details
                }
            })

        except Exception as e:
            _logger.exception('Error in product_category_deliver_to')
            response.update({'success': False, 'error_msg': str(e)})

        return response

    @http.route('/api/v1/create_offload_request', type='json', auth='none', methods=['POST'])
    def create_offload_request(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            partner_id = values.get('partner_id')
            warehouse_id = values.get('warehouse_id')
            product_lines = values.get('products', [])

            if not user_id or not auth_token:
                return {'success': False, 'error_msg': 'Missing user_id or auth_token'}

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            partner = request.env['res.partner'].sudo().browse(partner_id)
            warehouse = request.env['stock.warehouse'].sudo().browse(warehouse_id)

            if not partner.exists():
                return {'success': False, 'error_msg': f'Invalid partner_id: {partner_id}'}
            if not warehouse.exists():
                return {'success': False, 'error_msg': f'Invalid warehouse_id: {warehouse_id}'}

            destination_location = request.env['stock.location'].sudo().search([
                ('responsible_id', '=', user.id),
                ('usage', '=', 'internal')
            ], limit=1)

            if not destination_location:
                return {'success': False, 'error_msg': 'No van location found for this user.'}

            stock_request_lines = []
            warnings = []

            for line in product_lines:
                if not all(k in line for k in ('product_id', 'quantity', 'location_id')):
                    return {
                        'success': False,
                        'error_msg': 'Each product line must include product_id, quantity, and location_id.'
                    }

                raw_product_id = line['product_id']
                quantity = line['quantity']
                location_id = line['location_id']
                packaging_id = line.get('product_packaging_id')
                uom_id = line.get('product_uom_id')
                product_packaging_id = line.get('product_packaging_id')
                product_packaging_qty = line.get('product_packaging_qty')
                package_id = line.get('package_id')
                lot_id = line.get('lot_id')

                location = request.env['stock.location'].sudo().browse(location_id)
                if not location.exists():
                    return {
                        'success': False,
                        'error_msg': f"Invalid location_id {location_id} for product {raw_product_id}"
                    }

                product = request.env['product.product'].sudo().browse(raw_product_id)
                if not product.exists() or not product.active:
                    template = request.env['product.template'].sudo().browse(raw_product_id)
                    product = template.product_variant_ids[:1] if template.exists() else False
                    if not product or not product.active:
                        warnings.append(f"Skipped product ID {raw_product_id}: not found.")
                        continue

                final_quantity = quantity
                final_uom_id = uom_id

                if packaging_id:
                    if isinstance(packaging_id, str):
                        packaging_id = int(packaging_id.split(',')[0])
                    elif isinstance(packaging_id, list):
                        packaging_id = packaging_id[0]

                    product_packaging = request.env['product.packaging'].sudo().browse(packaging_id)
                    if product_packaging.exists():
                        final_quantity = quantity * product_packaging.qty
                        final_uom_id = product_packaging.product_uom_id.id
                    else:
                        return {
                            'success': False,
                            'error_msg': f"Invalid packaging ID {packaging_id} for product {product.id}"
                        }
                else:
                    if not final_uom_id:
                        return {
                            'success': False,
                            'error_msg': 'Missing product_uom_id when no product_packaging_id is given.'
                        }

                # ---------------------------
                # DEDUP FIX:
                # Keep previous behavior (no duplicate lines), but now consider lot_id and package_id.
                # This allows same product/location to appear multiple times if lot/package differs.
                # ---------------------------
                key_product = product.id
                key_location = location.id
                key_lot = lot_id or False
                key_package = package_id or False

                already_added = any(
                    (ln[2].get('product_id') == key_product) and
                    (ln[2].get('location_id') == key_location) and
                    ((ln[2].get('lot_id') or False) == key_lot) and
                    ((ln[2].get('package_id') or False) == key_package)
                    for ln in stock_request_lines
                )
                if already_added:
                    continue

                stk_req_li = {
                    'product_id': product.id,
                    'product_uom_qty': final_quantity,
                    'qty_done': final_quantity,
                    'product_uom_id': final_uom_id,
                    'warehouse_id': warehouse.id,
                    'location_id': location.id,
                    'requested_by': user.id,
                    'lot_id': lot_id,
                    'package_id': package_id,
                    'company_id': warehouse.company_id.id,
                }

                if product_packaging_id:
                    stk_req_li['product_packaging_id'] = product_packaging_id
                if product_packaging_qty:
                    stk_req_li['product_packaging_qty'] = product_packaging_qty

                stock_request_lines.append((0, 0, stk_req_li))

            if not stock_request_lines:
                return {'success': False, 'error_msg': 'No valid product lines found to create request.'}

            request_obj = request.env['stock.request.order'].sudo().create({
                'direction': 'van_off_load',
                'customer_id': partner.id,
                'requested_by': user.id,
                'company_id': warehouse.company_id.id,
                'warehouse_id': warehouse.id,
                'destination_id': destination_location.id,
                'stock_request_ids': stock_request_lines
            })

            try:
                request_obj.action_submit()
            except Exception as confirm_err:
                _logger.warning("Offload stock request created but failed to confirm: %s", str(confirm_err))
                response.update({
                    'success': True,
                    'message': 'Offload stock request created but not auto-confirmed.',
                    'stock_request_id': request_obj.id,
                    'stock_request_name': request_obj.name,
                    'warning': 'Could not auto-confirm stock request.'
                })
                return response

            response.update({
                'user_id': user.id,
                'user_name': user.name,
                'partner_id': partner_id,
                'partner': request.env['res.partner'].sudo().browse(partner_id).name if partner_id else '',
                'success': True,
                'message': 'Offload stock request created and confirmed successfully.',
                'stock_request_id': request_obj.id,
                'stock_request_name': request_obj.name,
            })

        except Exception as e:
            response.update({
                'success': False,
                'error_msg': str(e)
            })
            _logger.exception('Error in create_cd ..request API')

        return response

    @http.route('/api/v1/van_stock', type='json', auth='none', methods=['POST'], csrf=False)
    def get_van_stock(self, **kwargs):
        res = {}
        values = request.httprequest.json or {}

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            if not user_id or not auth_token:
                return {'success': False, 'error_msg': 'Missing required parameters.'}

            # Auth
            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(int(user_id))
            if not user.exists():
                return {'success': False, 'error_msg': 'User not found.'}

            # All internal “van” locations owned by this user (and their children)
            van_locations = request.env['stock.location'].sudo().search([
                ('responsible_id', '=', user.id),
                ('usage', '=', 'internal'),
            ])
            if not van_locations:
                return {'success': False, 'error_msg': 'No van location assigned to this user.'}

            van_location_ids = van_locations.ids

            # Pull all quants at/under these locations in one go
            Quant = request.env['stock.quant'].sudo()
            domain = [
                ('location_id', 'child_of', van_location_ids),
                # we’ll compute available in python; don’t filter here to not miss negative/edge quants
            ]
            quants = Quant.search(domain)
            # Prefetch to avoid N+1
            quants.mapped('product_id')
            quants.mapped('lot_id')
            quants.mapped('location_id')

            # Build product -> info
            products_map = {}  # pid -> dict
            now = fields.Datetime.now()

            def _image_url(model, record_id, field='image_1920'):
                # Use your helper if you have it; fallback to /web/image
                return f'/web/image/{model}/{record_id}/{field}'

            # Group per product and lot, summing available (quantity - reserved)
            for q in quants:
                p = q.product_id
                if not p or not p.active:
                    continue

                pid = p.id
                # robust available computation (works across versions)
                q_qty = float(q.quantity or 0)
                q_res = float(q.reserved_quantity or 0)
                q_avl = float(q.available_quantity or 0)

                # initialize product bucket
                info = products_map.get(pid)
                if not info:
                    # packaging counts computed later after we know available total
                    info = {
                        'product_id'   : pid,
                        'product_name' : p.name,
                        'image'        : _image_url(p._name, p.id, 'image_1920'),
                        'item_no'      : p.default_code or "",
                        'barcode'      : p.barcode or "",
                        'lst_price'    : p.list_price,
                        'uom'          : p.uom_id.name,
                        'uom_id'       : p.uom_id.id,
                        'taxes_id'     : p.taxes_id.id if p.taxes_id else False,
                        'taxes_name'   : p.taxes_id.name if p.taxes_id else '',
                        'description'  : p.description_sale or '',
                        'brand_id'     : p.brand_id.id if p.brand_id else 0,
                        'brand_name'   : p.brand_id.name if p.brand_id else 'Unbranded',

                        # totals — **available-based**
                        'available_total' : 0.0,
                        'quantity_total'  : 0.0,   # raw on-hand if you still want to see it
                        'reserved_total'  : 0.0,

                        # per-lot breakdown
                        'lots' : [],

                        # filled after totals are known
                        'product_packaging': [],
                    }
                    products_map[pid] = info

                info['available_total'] += q_avl
                info['quantity_total']  += q_qty
                info['reserved_total']  += q_res

                lot = q.lot_id
                # Lot details (include even if q_avl is zero; front-end can decide to show/grey)
                lot_dict = {
                    'lot_id'             : lot.id if lot else False,
                    'lot_name'           : lot.name if lot else False,
                    'expiration_date'    : lot.expiration_date or False,
                    'use_date'           : lot.use_date or False,
                    'removal_date'       : lot.removal_date or False,
                    'alert_date'         : lot.alert_date or False,
                    'in_date'            : q.in_date or False,
                    'quantity'           : q_qty,
                    'reserved_quantity'  : q_res,
                    # **the one you asked for**
                    'available_quantity' : q_avl,
                    'location_id'        : q.location_id.id,
                    'location_name'      : q.location_id.complete_name,
                    'is_salable'         : lot.is_salable,
                }
                info['lots'].append(lot_dict)

            # Compute packaging “on hand” using AVAILABLE totals (floor div by pack qty)
            for pid, info in products_map.items():
                p = request.env['product.product'].sudo().browse(pid)
                # Build packaging rows
                pkg_rows = []
                for pack in p.packaging_ids:
                    qty_per_pack = float(pack.qty or 0.0)
                    packs_on_hand = int(info['available_total'] // qty_per_pack) if qty_per_pack > 0 else 0
                    pkg_rows.append({
                        'id'          : pack.id,
                        'name'        : pack.name,
                        'uom'         : pack.product_uom_id.name,
                        'uom_id'      : pack.product_uom_id.id,
                        'qty_per_pack': qty_per_pack,
                        'on_hand_qty' : packs_on_hand,
                    })
                info['product_packaging'] = pkg_rows

            # Only keep products with available > 0 (change if you want zeros too)
            filtered_products = [v for v in products_map.values() if v['available_total'] > 0]

            # Group brand-wise
            brand_dict = {}
            unbranded = []
            for pr in filtered_products:
                b_id = pr['brand_id']
                b_nm = pr['brand_name']
                if not b_id or b_nm == 'Unbranded':
                    unbranded.append(pr)
                else:
                    brand_dict.setdefault((b_id, b_nm), []).append(pr)

            brand_wise = [
                {'brand_id': bid, 'brand_name': bnm, 'products': plist}
                for (bid, bnm), plist in brand_dict.items()
            ]
            if unbranded:
                brand_wise.append({'brand_id': 0, 'brand_name': 'Unbranded', 'products': unbranded})

            # Add ALL bucket first
            if filtered_products:
                brand_wise.insert(0, {'brand_id': -1, 'brand_name': 'ALL', 'products': filtered_products})

            # Optional: warehouses list you had
            all_wh = request.env['stock.warehouse'].sudo().search([])
            warehouse_details = [{'id': w.id, 'name': w.name} for w in all_wh]

            res.update({
                'success': True,
                'product_total': len(filtered_products),
                'van_stock': brand_wise,
                'warehouse_details': warehouse_details,
            })
            return res

        except Exception as e:
            _logger.exception("Error in /api/v1/van_stock")
            return {'success': False, 'error_msg': str(e)}

    # @http.route('/api/v1/van_stock', type='json', auth='none', methods=['POST'], csrf=False)
    # def get_van_stock(self, **kwargs):
    #     response = {}
    #     values = request.httprequest.json
    #
    #     try:
    #         user_id = values.get('user_id')
    #         auth_token = values.get('auth_token')
    #
    #         token_valid = request.env['mobile.auth.token'].sudo().search([
    #             ('user_id', '=', user_id),
    #             ('mobile_app_auth_token', '=', auth_token)
    #         ], limit=1)
    #
    #         if not token_valid:
    #             return {'success': False, 'error_msg': 'Invalid or expired auth token.'}
    #
    #         user = request.env['res.users'].sudo().browse(user_id)
    #
    #         van_locations = request.env['stock.location'].sudo().search([
    #             ('responsible_id', '=', user.id),
    #             ('usage', '=', 'internal')
    #         ])
    #         all_warehouses = request.env['stock.warehouse'].sudo().search([])
    #         warehouse_details = [{'id': w.id, 'name': w.name} for w in all_warehouses]
    #         if not van_locations:
    #             return {'success': False, 'error_msg': 'No van location assigned to this user.'}
    #
    #         product_totals = {}
    #         Quant = request.env['stock.quant'].sudo()
    #         now = fields.Datetime.now()
    #         for location in van_locations:
    #             domain = [('location_id', '=', location.id)]
    #             # If you have a custom expiration field on quant, prefer it
    #             if 'expiration_date' in Quant._fields:
    #                 # keep quants with no expiry or future/now expiry
    #                 domain += ['|', ('expiration_date', '=', False), ('expiration_date', '>=', now)]
    #             else:
    #                 # Standard Odoo: expiry is on the lot/serial (stock.production.lot)
    #                 # Include:
    #                 # - quants without lot (untracked), OR
    #                 # - quants whose lot is NOT expired by any of life/use/removal dates
    #                 domain += [
    #                     '|', ('lot_id', '=', False),
    #                     '&', '&',
    #                     '|', ('lot_id.expiration_date', '=', False), ('lot_id.expiration_date', '>=', now),
    #                     '|', ('lot_id.use_date', '=', False), ('lot_id.use_date', '>=', now),
    #                     '|', ('lot_id.removal_date', '=', False), ('lot_id.removal_date', '>=', now),
    #                 ]
    #             quants = Quant.search(domain)
    #             for quant in quants:
    #                 if quant.product_id.active != True:
    #                     continue
    #
    #                 product = quant.product_id
    #                 product_id = product.id
    #
    #                 on_hand_qty = product.with_context(location=location.id).qty_available
    #
    #                 qty_available = sum(
    #                     quants.filtered(lambda q: q.product_id.id == product.id).mapped('quantity')
    #                 )
    #                 packaging = request.env['product.packaging'].sudo().search([
    #                     ('product_id', '=', product_id)
    #                 ], limit=1)
    #
    #                 packaging_data = []
    #                 for packaging in product.packaging_ids:
    #                     qty_in_packaging = int(qty_available // packaging.qty) if packaging.qty > 0 else 0
    #                     packaging_data.append({
    #                         'id': packaging.id,
    #                         'name': packaging.name,
    #                         'uom': packaging.product_uom_id.name,
    #                         'uom_id': packaging.product_uom_id.id,
    #                         'qty_per_pack': packaging.qty,
    #                         'on_hand_qty': qty_in_packaging
    #                     })
    #
    #                 if product_id not in product_totals:
    #                     product_totals[product_id] = {
    #                         'product_id': product_id,
    #                         'product_name': product.name,
    #                         'image': self._get_image_url_dynamic(
    #                             model=product._name,
    #                             record_id=product.id,
    #                             field_name='image_1920'
    #                         ),
    #                         'item_no': product.default_code or "",
    #                         'barcode': product.barcode or "",
    #                         'lst_price': product.list_price,
    #                         'uom': quant.product_uom_id.name,
    #                         'uom_id': quant.product_uom_id.id,
    #                         'taxes_id': product.taxes_id.id if product.taxes_id else False,
    #                         'taxes_name': product.taxes_id.name if product.taxes_id else '',
    #                         'item_no': product.default_code,
    #                         'description': product.description_sale or '',
    #                         'quantity': quant.quantity,
    #                         # 'on_hand_qty': on_hand_qty,
    #                         'product_packaging': packaging_data,
    #                         'brand_id': product.brand_id.id if product.brand_id else 0,
    #                         'brand_name': product.brand_id.name if product.brand_id else 'Unbranded',
    #                     }
    #                 else:
    #                     product_totals[product_id]['quantity'] += quant.quantity
    #                     # product_totals[product_id]['on_hand_qty'] += on_hand_qty
    #
    #         brand_dict = {}
    #         unbranded_products = []
    #
    #         for product in product_totals.values():
    #             if product['quantity'] <= 0:
    #                 continue
    #
    #             brand_id = product['brand_id']
    #             brand_name = product['brand_name']
    #
    #             if brand_name == 'Unbranded' or brand_id == 0:
    #                 unbranded_products.append(product)
    #             else:
    #                 brand_key = (brand_id, brand_name)
    #                 if brand_key not in brand_dict:
    #                     brand_dict[brand_key] = []
    #                 brand_dict[brand_key].append(product)
    #
    #         brand_wise_products = [
    #             {
    #                 'brand_id': brand_id,
    #                 'brand_name': brand_name,
    #                 'products': products
    #             }
    #             for (brand_id, brand_name), products in brand_dict.items()
    #         ]
    #
    #         if unbranded_products:
    #             brand_wise_products.append({
    #                 'brand_id': 0,
    #                 'brand_name': 'Unbranded',
    #                 'products': unbranded_products
    #             })
    #         product_total = len(product_totals)
    #         # Add "ALL" brand that includes copies of all products
    #         # AFTER – only include items with quantity > 0
    #         # --- with this new block ---
    #         seen = set()
    #         all_products = []
    #         for prod in product_totals.values():
    #             qty = prod.get('quantity', 0)
    #             pid = prod.get('product_id')
    #             if qty > 0 and pid not in seen:
    #                 seen.add(pid)
    #                 all_products.append(prod)
    #
    #         if all_products:
    #             brand_wise_products.insert(0, {
    #                 'brand_id': -1,
    #                 'brand_name': 'ALL',
    #                 'products': all_products,
    #             })
    #         response.update({
    #             'success': True,
    #             'product_total': product_total,
    #             'van_stock': brand_wise_products,
    #             'warehouse_details':warehouse_details,
    #
    #         })
    #
    #     except Exception as e:
    #         _logger.exception("Error in /api/v1/van_stock")
    #         response.update({'success': False, 'error_msg': str(e)})
    #
    #     return response


    @http.route('/api/v1/van_stock_loyalty_product', type='json', auth='none', methods=['POST'], csrf=False)
    def get_van_stock_loyalty_product(self, **kwargs):
        response = {}
        values = request.httprequest.json or {}

        try:
            user_id     = values.get('user_id')
            auth_token  = values.get('auth_token')
            customer_id = values.get('customer_id')

            # --- Auth ---
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user     = request.env['res.users'].sudo().browse(int(user_id)) if user_id else None
            partner  = request.env['res.partner'].sudo().browse(int(customer_id)) if customer_id else None
            company  = request.env['res.company'].sudo().search([], limit=1)
            pricelist = partner.with_company(company).property_product_pricelist if partner else None

            promo_groups = request.env['promo.customer.group'].sudo().search([('partner_ids', 'in', [partner.id])]) if partner else request.env['promo.customer.group'].sudo()

            # -----------------------------
            # A) Loyalty via loyalty.rule (existing behavior)
            # -----------------------------
            product_to_rules = {}
            loyalty_product_ids = []
            if promo_groups:
                loyalty_rules = request.env['loyalty.rule'].sudo().search([
                    ('program_id.promo_customer_group_id', 'in', promo_groups.ids),
                    ('active', '=', True)
                ]) if customer_id else request.env['loyalty.rule'].sudo()

                loyalty_product_ids = list({p.id for r in loyalty_rules for p in r.product_ids})
                for r in loyalty_rules:
                    for p in r.product_ids:
                        if p.active:
                            product_to_rules.setdefault(p.id, []).append(r)

            # -----------------------------
            # B) NEW: Fallback from loyalty.program for flat/slab/ladder
            # -----------------------------
            Program = request.env['loyalty.program'].sudo()
            custom_programs = Program.search([
                ('program_type', 'in', ['ladder_promotion', 'slab_promotion', 'flat_discount']),
                ('active', '=', True),
            ])

            def _partner_allowed(prog, partner):
                """Mirror your program customer scoping without needing a sale.order."""
                if not partner:
                    return False
                if prog.program_type == 'flat_discount':
                    if prog.flat_apply_customers_options == 'customer_group' and prog.promo_customer_group_id:
                        return partner in prog.promo_customer_group_id.partner_ids
                    if prog.flat_apply_customers_options == 'customer':
                        return partner in prog.flat_customer_ids
                    return True
                # slab/ladder: reuse same logic as _is_customer_allowed but simplified
                if prog.promo_customer_group_id:
                    return partner in prog.promo_customer_group_id.partner_ids
                return True

            # Build indices for quick lookup per-product/per-division
            progs_by_product = defaultdict(list)  # product_id -> [programs]
            progs_by_division = defaultdict(list) # division string -> [programs]

            for prog in custom_programs:
                if not _partner_allowed(prog, partner):
                    continue

                if prog.program_type in ('slab_promotion', 'ladder_promotion'):
                    # Products come from promo_product_group_id
                    for p in prog.promo_product_group_id.product_ids:
                        progs_by_product[p.id].append(prog)

                elif prog.program_type == 'flat_discount':
                    opt = prog.flat_discount_apply_options
                    if opt == 'products' and prog.flat_product_ids:
                        for p in prog.flat_product_ids:
                            progs_by_product[p.id].append(prog)
                    elif opt == 'product_group' and prog.promo_product_group_id:
                        for p in prog.promo_product_group_id.product_ids:
                            progs_by_product[p.id].append(prog)
                    elif opt == 'division' and prog.flat_division:
                        progs_by_division[prog.flat_division].append(prog)
                    # else: nothing to index

            # --- Van locations for user ---
            van_locations = request.env['stock.location'].sudo().search([
                ('responsible_id', '=', user.id if user else False),
                ('usage', '=', 'internal')
            ])
            if not van_locations:
                return {'success': False, 'error_msg': 'No van location assigned to this user.'}

            # --- Warehouses list (unchanged) ---
            all_warehouses = request.env['stock.warehouse'].sudo().search([])
            warehouse_details = [{'id': w.id, 'name': w.name} for w in all_warehouses]

            # --- Models ---
            Quant   = request.env['stock.quant'].sudo()
            Product = request.env['product.product'].sudo()

            product_totals = {}
            now = fields.Datetime.now()

            for location in van_locations:
                # Base domain (unchanged) + lot salable guard if available
                base_domain = [('location_id', '=', location.id)]
                if 'expiration_date' in Quant._fields:
                    base_domain += ['|', ('expiration_date', '=', False), ('expiration_date', '>=', now)]
                else:
                    base_domain += [
                        '|', ('lot_id', '=', False),
                        '&', '&',
                            '|', ('lot_id.use_date', '=', False), ('lot_id.use_date', '>=', now),
                            '|', ('lot_id.expiration_date', '=', False), ('lot_id.expiration_date', '>=', now),
                            '|', ('lot_id.removal_date', '=', False), ('lot_id.removal_date', '>=', now),
                    ]
                if 'is_salable' in request.env['stock.lot']._fields:
                    base_domain += ['|', ('lot_id', '=', False), ('lot_id.is_salable', '=', True)]

                base_quants = Quant.search(base_domain)
                if not base_quants:
                    continue

                grouped = Quant.read_group(
                    domain=[('id', 'in', base_quants.ids), ('available_quantity', '>', 0)],
                    fields=['product_id'],
                    groupby=['product_id']
                )
                candidate_product_ids = [g['product_id'][0] for g in grouped if g.get('product_id')]

                base_quants_by_product = {}
                for q in base_quants:
                    if q.quantity <= 0:
                        continue
                    base_quants_by_product.setdefault(q.product_id.id, Quant.browse())
                    base_quants_by_product[q.product_id.id] |= q

                for pid in candidate_product_ids:
                    product = Product.browse(pid)

                    # If partner has shelf rules, keep your existing gather logic
                    partner_has_rules = bool(partner and partner.product_shelf_life_ids)
                    if partner_has_rules:
                        ctx_quant = Quant.with_context(product_shelf_partner=partner)
                        gathered = ctx_quant._gather(product, location, strict=False)
                        if not gathered:
                            continue
                        filtered_quants = gathered & base_quants_by_product.get(pid, Quant.browse())
                    else:
                        filtered_quants = base_quants_by_product.get(pid, Quant.browse())

                    if not filtered_quants:
                        continue

                    qty_available = sum(filtered_quants.mapped('available_quantity'))
                    if qty_available <= 0:
                        continue

                    # Packaging (unchanged)
                    packaging_data = []
                    for packaging in product.packaging_ids:
                        qty_in_pack = int(qty_available // packaging.qty) if packaging.qty > 0 else 0
                        packaging_data.append({
                            'id': packaging.id,
                            'name': packaging.name,
                            'uom': packaging.product_uom_id.name,
                            'uom_id': packaging.product_uom_id.id,
                            'qty_per_pack': packaging.qty,
                            'on_hand_qty': qty_in_pack
                        })

                    # -----------------------------
                    # Loyalty info (augmented)
                    # -----------------------------
                    rules_for_this = product_to_rules.get(pid, [])
                    fallback_programs = list(progs_by_product.get(pid, []))
                    # division-based flat discounts
                    prod_div = getattr(product, 'division', False)
                    if prod_div and progs_by_division.get(prod_div):
                        fallback_programs += progs_by_division[prod_div]

                    # Build a unified loyalty_info without duplicates
                    loyalty_info = []
                    seen_names = set()
                    for r in rules_for_this:
                        name = r.program_id.name if r.program_id else False
                        if name and name not in seen_names:
                            loyalty_info.append({'program_name': name})
                            seen_names.add(name)
                    for prog in fallback_programs:
                        name = prog.name
                        if name and name not in seen_names:
                            loyalty_info.append({'program_name': name})
                            seen_names.add(name)

                    # is_loyalty_* flags (keep keys, extend logic)
                    has_loyalty = bool(rules_for_this or fallback_programs)

                    # Price (unchanged)
                    lst_price = product.list_price
                    if pricelist:
                        lst_price = pricelist.sudo()._get_product_price(product, 1.0)

                    # Accumulate across locations (unchanged structure)
                    if pid not in product_totals:
                        product_totals[pid] = {
                            'product_id': pid,
                            'product_name': product.name,
                            'image': self._get_image_url_dynamic(
                                model=product._name,
                                record_id=product.id,
                                field_name='image_1920'
                            ),
                            'item_no': product.default_code or "",
                            'barcode': product.barcode or "",
                            'lst_price': lst_price,
                            'uom': product.uom_id.name,
                            'uom_id': product.uom_id.id,
                            'taxes_id': product.taxes_id.id if product.taxes_id else False,
                            'taxes_name': product.taxes_id.name if product.taxes_id else '',
                            'description': product.description_sale or '',
                            'quantity': qty_available,
                            'product_packaging': packaging_data,
                            'brand_id': product.brand_id.id if product.brand_id else 0,
                            'brand_name': product.brand_id.name if product.brand_id else 'Unbranded',
                            # >>> same keys, augmented logic
                            'is_loyalty_product': has_loyalty,
                            'is_loyalty_product_sec': has_loyalty,
                            'loyalty_info': loyalty_info,
                        }
                    else:
                        product_totals[pid]['quantity'] += qty_available
                        # keep the last computed loyalty flags/info (or merge if you prefer)
                        product_totals[pid].update({
                            'is_loyalty_product': product_totals[pid]['is_loyalty_product'] or has_loyalty,
                            'is_loyalty_product_sec': product_totals[pid]['is_loyalty_product_sec'] or has_loyalty,
                            'loyalty_info': product_totals[pid]['loyalty_info'] or loyalty_info or [],
                        })

            # --- Brand grouping + ALL (unchanged) ---
            branded_products, unbranded_products = [], []
            for p in product_totals.values():
                if p['brand_id'] and p['brand_name'] != 'Unbranded':
                    if p['quantity'] > 0:
                        branded_products.append(p)
                else:
                    if p['quantity'] > 0:
                        unbranded_products.append(p)

            brand_dict = {}
            for p in branded_products:
                key = (p['brand_id'], p['brand_name'])
                brand_dict.setdefault(key, []).append(p)

            brand_wise_products = [
                {'brand_id': bid, 'brand_name': bname, 'products': prods}
                for (bid, bname), prods in brand_dict.items()
            ]
            if unbranded_products:
                brand_wise_products.append({'brand_id': 0, 'brand_name': 'Unbranded', 'products': unbranded_products})

            all_products = branded_products + unbranded_products
            if all_products:
                brand_wise_products.insert(0, {'brand_id': -1, 'brand_name': 'ALL', 'products': all_products})

            response.update({
                'success': True,
                'product_total': len(product_totals),
                'van_stock': brand_wise_products,
                'warehouse_details': warehouse_details,
            })

        except Exception as e:
            _logger.exception("Error in /api/v1/van_stock_loyalty_product")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    # @http.route('/api/v1/van_stock_loyalty_product', type='json', auth='none', methods=['POST'], csrf=False)
    # def get_van_stock_loyalty_product(self, **kwargs):
    #     response = {}
    #     values = request.httprequest.json or {}
    #
    #     try:
    #         user_id     = values.get('user_id')
    #         auth_token  = values.get('auth_token')
    #         customer_id = values.get('customer_id')
    #
    #         # --- Auth ---
    #         token_valid = request.env['mobile.auth.token'].sudo().search([
    #             ('user_id', '=', user_id),
    #             ('mobile_app_auth_token', '=', auth_token)
    #         ], limit=1)
    #         if not token_valid:
    #             return {'success': False, 'error_msg': 'Invalid or expired auth token.'}
    #
    #         user     = request.env['res.users'].sudo().browse(int(user_id)) if user_id else None
    #         partner  = request.env['res.partner'].sudo().browse(int(customer_id)) if customer_id else None
    #         company  = request.env['res.company'].sudo().search([], limit=1)
    #         pricelist = partner.with_company(company).property_product_pricelist if partner else None
    #
    #
    #         promo_groups = request.env['promo.customer.group'].sudo().search([('partner_ids', 'in', [partner.id])])
    #
    #         product_to_rules = {}
    #         loyalty_product_ids = list()
    #         if promo_groups:
    #             # --- Loyalty rules -> product mapping ---
    #             loyalty_rules = request.env['loyalty.rule'].sudo().search([('program_id.promo_customer_group_id', 'in', promo_groups.ids), ('active','=', True)]) if customer_id else request.env['loyalty.rule'].sudo()
    #             loyalty_product_ids = list({p.id for r in loyalty_rules for p in r.product_ids})
    #
    #
    #             for r in loyalty_rules:
    #                 for p in r.product_ids:
    #                     if p.active == True:
    #                         product_to_rules.setdefault(p.id, []).append(r)
    #
    #         # --- Van locations for user ---
    #         van_locations = request.env['stock.location'].sudo().search([
    #             ('responsible_id', '=', user.id if user else False),
    #             ('usage', '=', 'internal')
    #         ])
    #         if not van_locations:
    #             return {'success': False, 'error_msg': 'No van location assigned to this user.'}
    #
    #         # --- Warehouses list (as you already had) ---
    #         all_warehouses = request.env['stock.warehouse'].sudo().search([])
    #         warehouse_details = [{'id': w.id, 'name': w.name} for w in all_warehouses]
    #
    #         # --- Models ---
    #         Quant   = request.env['stock.quant'].sudo()
    #         Product = request.env['product.product'].sudo()
    #
    #         product_totals = {}
    #         now = fields.Datetime.now()
    #
    #         # For each van location
    #         for location in van_locations:
    #
    #             # 1) Base domain — your original expiry/use/removal logic preserved
    #             #    If quant has its own expiration_date field, use it.
    #             base_domain = [('location_id', '=', location.id)]
    #             if 'expiration_date' in Quant._fields:
    #                 base_domain += [
    #                     '|', ('expiration_date', '=', False),
    #                          ('expiration_date', '>=', now),
    #                 ]
    #             else:
    #                 # Standard: lot-based expiry/use/removal checks, or allow untracked (lot_id=False)
    #                 base_domain += [
    #                     '|', ('lot_id', '=', False),
    #                     '&', '&',
    #                         # use_date ok or empty
    #                         '|', ('lot_id.use_date', '=', False), ('lot_id.use_date', '>=', now),
    #                         # expiration_date ok or empty
    #                         '|', ('lot_id.expiration_date', '=', False), ('lot_id.expiration_date', '>=', now),
    #                         # removal_date ok or empty
    #                         '|', ('lot_id.removal_date', '=', False), ('lot_id.removal_date', '>=', now),
    #                 ]
    #
    #             # 🔒 Lot salable guard (works in both branches):
    #             # “either no lot OR the lot is salable”
    #             lot_guard = ['|', ('lot_id', '=', False), ('lot_id.is_salable', '=', True)]
    #
    #             # 🔒 Lot salable guard: (lot_id is False) OR (lot_id.is_salable is True)
    #             # Appending this builds: BASE … AND (lot_id=False OR lot_id.is_salable=True)
    #             if 'is_salable' in request.env['stock.lot']._fields:
    #                 base_domain += lot_guard
    #
    #             base_quants = Quant.search(base_domain)
    #             if not base_quants:
    #                 continue
    #
    #             # Products with quantity > 0 in *non-expired* base quants
    #             grouped = request.env['stock.quant'].sudo().read_group(
    #                 domain=[('id', 'in', base_quants.ids), ('available_quantity', '>', 0)],
    #                 fields=['product_id'],
    #                 groupby=['product_id']
    #             )
    #             candidate_product_ids = [g['product_id'][0] for g in grouped if g.get('product_id')]
    #
    #             # Pre-index base quants per product for fast intersection
    #             base_quants_by_product = {}
    #             for q in base_quants:
    #                 if q.quantity <= 0:
    #                     continue
    #                 base_quants_by_product.setdefault(q.product_id.id, Quant.browse())
    #                 base_quants_by_product[q.product_id.id] |= q
    #
    #             # 2) Apply partner shelf-life rules ONLY if partner has them; otherwise use base quants as-is
    #             partner_has_rules = bool(partner and partner.product_shelf_life_ids)
    #
    #             for pid in candidate_product_ids:
    #                 product = Product.browse(pid)
    #
    #                 if partner_has_rules:
    #                     # Your customized _gather enforces product_shelf_line, saleable location, etc.
    #                     ctx_quant = Quant.with_context(product_shelf_partner=partner)
    #                     gathered = ctx_quant._gather(product, location, strict=False)
    #
    #                     if not gathered:
    #                         continue
    #
    #                     # Keep original expiry/use/removal behavior by intersecting with base quants
    #                     filtered_quants = gathered & base_quants_by_product.get(pid, Quant.browse())
    #                 else:
    #                     # No shelf rules: EXACT old behavior
    #                     filtered_quants = base_quants_by_product.get(pid, Quant.browse())
    #
    #                 if not filtered_quants:
    #                     continue
    #
    #                 # Sum quantities from filtered quants (keep behavior the same as before)
    #                 qty_available = sum(filtered_quants.mapped('available_quantity'))
    #                 if qty_available <= 0:
    #                     continue
    #
    #                 # Packaging info
    #                 packaging_data = []
    #                 for packaging in product.packaging_ids:
    #                     qty_in_pack = int(qty_available // packaging.qty) if packaging.qty > 0 else 0
    #                     packaging_data.append({
    #                         'id': packaging.id,
    #                         'name': packaging.name,
    #                         'uom': packaging.product_uom_id.name,
    #                         'uom_id': packaging.product_uom_id.id,
    #                         'qty_per_pack': packaging.qty,
    #                         'on_hand_qty': qty_in_pack
    #                     })
    #
    #                 # Loyalty info
    #                 rules_for_this = product_to_rules.get(pid, [])
    #                 is_loyalty_sec = bool(rules_for_this)
    #                 loyalty_info = [{'program_name': r.program_id.name if r.program_id else False}
    #                                 for r in rules_for_this]
    #                 is_loyalty = any(v.id in loyalty_product_ids for v in product.product_variant_ids)
    #
    #                 # Price
    #                 lst_price = product.list_price
    #                 if pricelist:
    #                     lst_price = pricelist.sudo()._get_product_price(product, 1.0)
    #
    #                 # Accumulate across locations
    #                 if pid not in product_totals:
    #                     product_totals[pid] = {
    #                         'product_id': pid,
    #                         'product_name': product.name,
    #                         'image': self._get_image_url_dynamic(
    #                             model=product._name,
    #                             record_id=product.id,
    #                             field_name='image_1920'
    #                         ),
    #                         'item_no': product.default_code or "",
    #                         'barcode': product.barcode or "",
    #                         'lst_price': lst_price,
    #                         'uom': product.uom_id.name,
    #                         'uom_id': product.uom_id.id,
    #                         'taxes_id': product.taxes_id.id if product.taxes_id else False,
    #                         'taxes_name': product.taxes_id.name if product.taxes_id else '',
    #                         'description': product.description_sale or '',
    #                         'quantity': qty_available,
    #                         'product_packaging': packaging_data,
    #                         'brand_id': product.brand_id.id if product.brand_id else 0,
    #                         'brand_name': product.brand_id.name if product.brand_id else 'Unbranded',
    #                         'is_loyalty_product': is_loyalty,
    #                         'is_loyalty_product_sec': is_loyalty_sec,
    #                         'loyalty_info': loyalty_info,
    #                     }
    #                 else:
    #                     product_totals[pid]['quantity'] += qty_available
    #                     product_totals[pid].update({
    #                         'is_loyalty_product': is_loyalty,
    #                         'is_loyalty_product_sec': is_loyalty_sec,
    #                         'loyalty_info': loyalty_info,
    #                     })
    #
    #         # --- Brand grouping + ALL group (unchanged) ---
    #         branded_products, unbranded_products = [], []
    #         for p in product_totals.values():
    #             if p['brand_id'] and p['brand_name'] != 'Unbranded':
    #                 if p['quantity'] > 0:
    #                     branded_products.append(p)
    #             else:
    #                 if p['quantity'] > 0:
    #                     unbranded_products.append(p)
    #
    #         brand_dict = {}
    #         for p in branded_products:
    #             key = (p['brand_id'], p['brand_name'])
    #             brand_dict.setdefault(key, []).append(p)
    #
    #         brand_wise_products = [
    #             {'brand_id': bid, 'brand_name': bname, 'products': prods}
    #             for (bid, bname), prods in brand_dict.items()
    #         ]
    #         if unbranded_products:
    #             brand_wise_products.append({'brand_id': 0, 'brand_name': 'Unbranded', 'products': unbranded_products})
    #
    #         all_products = branded_products + unbranded_products
    #         if all_products:
    #             brand_wise_products.insert(0, {'brand_id': -1, 'brand_name': 'ALL', 'products': all_products})
    #
    #         response.update({
    #             'success': True,
    #             'product_total': len(product_totals),
    #             'van_stock': brand_wise_products,
    #             'warehouse_details': warehouse_details,
    #         })
    #
    #     except Exception as e:
    #         _logger.exception("Error in /api/v1/van_stock_loyalty_product")
    #         response.update({'success': False, 'error_msg': str(e)})
    #
    #     return response

    @http.route('/api/v1/create_invoice_request', type='json', auth='none', methods=['POST'])
    def create_invoice_request(self, **kwargs):
        values = request.httprequest.json
        response = {}

        try:
            user_id = int(values.get('user_id', 0))
            user = request.env['res.users'].sudo().browse(user_id)

            if not user.exists() or len(user) != 1:
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            auth_token = values.get('auth_token')
            if not auth_token:
                return {'success': False, 'error_msg': 'Auth token is missing.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            partner_id = values.get('partner_id')
            partner = request.env['res.partner'].sudo().browse(partner_id)
            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid partner ID.'}

            product_lines = values.get('products', [])
            invoice_lines = []
            for line in product_lines:
                product_id = line.get('product_id')
                quantity = line.get('quantity')
                price_unit = line.get('price_unit')
                uom_id = line.get('uom_id')
                discount = line.get('discount', 0)
                packaging_id = line.get('product_packaging_id')

                if not all([product_id, quantity, price_unit, uom_id]):
                    return {'success': False, 'error_msg': 'Missing required product fields.'}

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists() or not product.active:
                    template = request.env['product.template'].sudo().browse(product_id)
                    product = template.product_variant_ids[:1] if template.exists() else False
                    if not product or not product.active:
                        return {
                            'success': False,
                            'error_msg': f"Invalid product ID: {product_id}"
                        }

                if packaging_id:
                    if isinstance(packaging_id, str):
                        packaging_id = int(packaging_id.split(',')[0])
                    elif isinstance(packaging_id, list):
                        packaging_id = packaging_id[0]

                    product_packaging = request.env['product.packaging'].sudo().browse(packaging_id)
                    if product_packaging.exists():
                        quantity *= product_packaging.qty
                        uom_id = product_packaging.product_uom_id.id
                    else:
                        return {
                            'success': False,
                            'error_msg': f"Invalid packaging ID {packaging_id} for product {product.id}"
                        }

                line_vals = {
                    'product_id': product.id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'product_uom_id': uom_id,
                    'name': product.name,
                }

                invoice_lines.append((0, 0, line_vals))

            if not invoice_lines:
                return {'success': False, 'error_msg': 'No valid invoice lines.'}

            invoice = request.env['account.move'].with_user(user.id).sudo().create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'company_id': user.sudo().company_id.id,
            })

            credit_limit = partner.credit_limit or 0
            total_overdue = partner.total_overdue or 0
            available_status = credit_limit - total_overdue

            response.update({
                'success': True,
                'message': 'Invoice created successfully.',
                'invoice_id': invoice.id,
                'invoice_name': invoice.name,
                'partner_info': {
                    'credit_limit': credit_limit,
                    'total_overdue': total_overdue,
                    'available_status': available_status,
                    'department': partner.department.name if partner.department else '',
                }
            })

        except Exception as e:
            _logger.exception("Error in /create_invoice_request")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    def download_invoice_report(self, user, invoice):
        access_token = invoice._portal_ensure_token()
        return invoice.get_base_url() + '/my/invoices/{}?access_token={}&report_type=pdf&download=true'.format(
            invoice.id, access_token)

    @http.route(['/api/v1/download/invoice/<int:invoice_id>'], type='json', auth='none', methods=['POST'])
    def download_invoice_pdf(self, **kwargs):
        response = {}
        values = request.httprequest.json
        check_authenticate = self._check_authentication_generalize_for_apis()

        if check_authenticate and check_authenticate[0]:
            return check_authenticate[0]

        try:
            user_id = int(values.get('user_id', 0))
            user = request.env['res.users'].sudo().browse(user_id)
            invoice = []
            if kwargs.get('invoice_id'):
                domain = int(kwargs.get('invoice_id'))
                invoice = request.env['account.move'].sudo().search([('id', '=', domain)])

            if not invoice.exists():
                return request.make_json_response({
                    'success': False,
                    'error_msg': 'Invoice not found.'
                })

            response.update({
                "success": False,
                "success_msg": "Pass the correct invoice number after the last / in the api url.",
                'user_id': user,
            })

            response.update({
                'invoice_pdf_url': self.download_invoice_report(user, invoice)
            })
        except Exception as e:
            response.update({
                "success": False,
                "success_msg": "{}".format(e),
                'user_id': user,
            })
            _logger.info('Some exception occurs')
        response.update({
            "success": True,
            "success_msg": "Records Fetched",
            "total_records_fetched": len(invoice),
            'user_id': user,
        })

        return response

    @http.route(['/api/v1/download/invoice/attachment/<int:invoice_id>'], type='json', auth='none', methods=['post'])
    def download_invoice_attachment(self, invoice_id, **kwargs):
        response = {}
        values = request.httprequest.json or {}

        check_authenticate = self._check_authentication_generalize_for_apis()
        if check_authenticate and check_authenticate[0]:
            return check_authenticate[0]

        try:
            user_id = int(values.get('user_id', 0))
            user = request.env['res.users'].sudo().browse(user_id)

            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists():
                return {
                    'success': False,
                    'error_msg': 'Invoice not found.',
                }
            report = request.env['ir.actions.report'].sudo().search([('report_name', '=', 'account.report_invoice')],
                                                                    limit=1)
            if not report:
                raise ValueError("Invoice report not found.")
            report = request.env['ir.actions.report'].with_user(user.id).sudo()._render_qweb_pdf(
                "account.report_invoice_with_payments", invoice.id)
            filename = f"{invoice.name or 'invoice'}_{invoice.id}.pdf"

            attachment = request.env['ir.attachment'].with_user(user.id).sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            })
            response.update({
                "success": True,
                "success_msg": "Invoice PDF saved as attachment.",
                "attachment_id": attachment.id,
                "file_name": filename,
                "user_id": user.id,
            })

        except Exception as e:
            _logger.exception("Error generating invoice PDF:")
            response.update({
                "success": False,
                "success_msg": str(e),
                "user_id": values.get('user_id', 0),
            })

        return response


    @http.route('/api/v1/create_delivery_for_sale_order', type='json', auth='none', methods=['POST'])
    def create_delivery_for_sale_order(self, **kwargs):
        values = request.httprequest.json
        response = {}
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = int(values.get('sale_order_id', 0))
            po_number = values.get('po_number')
            if not (user_id and auth_token and sale_order_id):
                return {'success': False, 'error_msg': 'Missing required parameters.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}


            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}
            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
            if po_number:
                sale_order.po_number = po_number
            if not sale_order.exists():
                return {'success': False, 'error_msg': 'Invalid sale order ID.'}
            if sale_order.state in ['draft', 'sent']:
                sale_order.action_confirm()
            steps = sale_order.warehouse_id.delivery_steps
            max_pickings = {
                'ship_only': 1,
                'pick_ship': 2,
                'pick_pack_ship': 3,
            }.get(steps, 1)
            pickings = sale_order.picking_ids.sorted(key=lambda p: p.picking_type_id.sequence)
            response['pickings'] = []
            for idx, picking in enumerate(pickings, start=1):
                if idx > max_pickings:
                    break
                if picking.state == 'draft':
                    picking.sudo().with_user(user.id).action_confirm()
                if not picking.picker_partner_id:
                    picking.picker_partner_id = sale_order.partner_id or request.env['res.partner'].sudo().search([],
                                                                                                                  limit=1)
                if picking.state in ['confirmed', 'assigned']:
                    picking.sudo().with_user(user.id).action_assign()
                    for move in picking.move_ids_without_package:
                        qty = move.product_uom_qty
                        if not move.move_line_ids:
                            vals = {
                                'picking_id': picking.id,
                                'move_id': move.id,
                                'product_id': move.product_id.id,
                                'product_uom_id': move.product_uom.id,
                                'qty_done': qty,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                            }
                            if move.product_id.tracking != 'none':
                                lot = request.env['stock.lot'].sudo().search(
                                    [('product_id', '=', move.product_id.id)], limit=1)
                                if not lot:
                                    raise UserError(
                                        f"Lot/Serial Number needed for product: {move.product_id.display_name}")
                                vals['lot_id'] = lot.id
                            request.env['stock.move.line'].sudo().create(vals)
                        else:
                            for ml in move.move_line_ids:
                                ml.sudo().with_user(user.id).qty_done = qty
                                if move.product_id.tracking != 'none' and not ml.lot_id:
                                    lot = request.env['stock.lot'].sudo().search(
                                        [('product_id', '=', move.product_id.id)], limit=1)
                                    if not lot:
                                        raise UserError(
                                            f"Lot/Serial Number needed for product: {move.product_id.display_name}")
                                    ml.lot_id = lot.id

                    picking.sudo().with_user(user.id).with_context(mail_create_nosubscribe=True).button_validate()

                response['pickings'].append({
                    'picking_id': picking.id,
                    'name': picking.name,
                    'step': idx,
                    'state': picking.state,
                    'type': picking.picking_type_id.name,
                })

            response.update({
                'success': True,
                'message': f"Processed {idx} / {max_pickings} steps ({steps}).",
                'sale_order': {
                    'id': sale_order.id,
                    'name': sale_order.name,
                }
            })

        except Exception as e:
            _logger.exception("Error in /create_delivery_for_sale_order")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    def download_payment_receipt(self, user, payment):
        access_token = payment._portal_ensure_token()
        return payment.get_base_url() + '/my/payment_method_id/{}?access_token={}&report_type=pdf&download=true'.format(
            payment.id, access_token)


    @http.route('/my/payment_method_id/<int:payment_id>', type='http', auth='public', website=True)
    def payment_receipt_download(self, payment_id, access_token=None, download=False, **kw):
        payment = request.env['account.payment'].sudo().browse(payment_id)
        if not payment or payment.access_token != access_token:
            raise AccessError("Invalid token or payment.")

        # pdf_content, _ = request.env.ref('account.report_payment_receipt').sudo()._render_qweb_pdf([payment.id])
        pdf_content, _ = request.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account.report_payment_receipt', res_ids=payment.id)
        headers = [('Content-Type', 'application/pdf')]
        if download:
            headers.append(('Content-Disposition', f'attachment; filename="Payment_Receipt_{payment.name}.pdf"'))
        return request.make_response(pdf_content, headers=headers)

    @http.route('/my/tax_invoice_4inch_pdf/<int:sale_order_id>', type='http', auth='public', website=True)
    def tax_invoice_4inch_report_download(self, sale_order_id, access_token=None, download=False, **kw):
        sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
        if not sale_order or sale_order.access_token != access_token:
            raise AccessError("Invalid token or Sale order.")

        # pdf_content, _ = request.env.ref('account.report_payment_receipt').sudo()._render_qweb_pdf([payment.id])
        pdf_content, _ = request.env['ir.actions.report'].with_context(force_report_rendering=True).sudo()._render_qweb_pdf('gulfco_sale_extanded.report_tax_invoice_4_inch_pdf', res_ids=sale_order.id)
        headers = [('Content-Type', 'application/pdf')]

        if download:
            headers.append(('Content-Disposition', f'attachment; filename="Tax Invoice(4inch)_{sale_order.name}.pdf"'))
        return request.make_response(pdf_content, headers=headers)


    # @http.route('/my/tax_invoice_4inch_pdf/<int:sale_order_id>', type='http', auth='public', website=True)
    # def tax_invoice_4inch_report_download(self, sale_order_id, access_token=None, download=False, **kw):
    #     SaleOrder = request.env['sale.order'].sudo()
    #     sale_order = SaleOrder.browse(sale_order_id)
    #
    #     if not sale_order or sale_order.access_token != access_token:
    #         raise AccessError("Invalid token or Sale order.")
    #
    #     attachment = sale_order.generate_tax_invoice_pdf_attachment(force=False)
    #
    #     headers = [('Content-Type', 'application/pdf')]
    #     if download:
    #         headers.append(('Content-Disposition', f'attachment; filename="Tax Invoice(4inch).pdf"'))
    #
    #     return request.make_response(base64.b64decode(attachment.datas), headers=headers)

    @http.route('/my/tax_credit_4inch_pdf/<int:credit_note_id>', type='http', auth='public', website=True)
    def tax_credit_4inch_report_download(self, credit_note_id, access_token=None, download=False, **kw):
        credit_note = request.env['account.move'].sudo().browse(credit_note_id)
        if not credit_note or credit_note.access_token != access_token:
            raise AccessError("Invalid token or account move.")

        # pdf_content, _ = request.env.ref('account.report_payment_receipt').sudo()._render_qweb_pdf([payment.id])
        pdf_content, _ = request.env['ir.actions.report'].with_context(force_report_rendering=True).sudo()._render_qweb_pdf('plnx_rma_extended.report_tax_credit_note_4_inch_pdf', res_ids=credit_note.id)
        headers = [('Content-Type', 'application/pdf')]
        if download:
            headers.append(('Content-Disposition', f'attachment; filename="Tax Credit(4inch)_{credit_note.name}.pdf"'))
        return request.make_response(pdf_content, headers=headers)

    @http.route('/my/receipt_voucher_4inch_pdf/<int:payment_id>', type='http', auth='public', website=True)
    def receipt_voucher_4inch_download(self, payment_id, access_token=None, download=False, **kw):
        receipt_voucher = request.env['account.payment'].sudo().browse(payment_id)
        if not receipt_voucher or receipt_voucher.access_token != access_token:
            raise AccessError("Invalid token or Sale order.")

        # pdf_content, _ = request.env.ref('account.report_payment_receipt').sudo()._render_qweb_pdf([payment.id])
        pdf_content, _ = request.env['ir.actions.report'].with_context(force_report_rendering=True).sudo()._render_qweb_pdf('fieldservice_account_extended.report_payment_receipt_voucher_pdf', res_ids=receipt_voucher.id)
        headers = [('Content-Type', 'application/pdf')]
        if download:
            headers.append(('Content-Disposition', f'attachment; filename="Receipt Voucher(4inch)_{receipt_voucher.name}.pdf"'))
        return request.make_response(pdf_content, headers=headers)

    # create sale order preview
    @http.route('/api/v1/create_sale_order_with_delivery', type='json', auth='user', methods=['POST'], csrf=False)
    def create_sale_order_with_delivery(self, **kwargs):
        response = {}
        values = request.httprequest.json
        sale_order_start_datetime = datetime.now()
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = values.get('sale_order_id')
            is_active = values.get('is_active', False)
            po_number = values.get('po_number', False)

            user = request.env['res.users'].browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search_count([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ])
            if token == 0:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            customer_payment_type = "cash"
            if sale_order_id and is_active:
                so_vals = {}
                sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
                if po_number:
                    so_vals.update({'po_number' : po_number})
                    # sale_order.po_number = po_number

                try:
                    van_location = user.partner_id.van_location
                    if van_location and van_location.warehouse_id:
                        # sale_order.warehouse_id = van_location.warehouse_id.id
                        so_vals.update({'warehouse_id' : van_location.warehouse_id.id})
                except Exception as e:
                    _logger.info("error into the warehouse")
                    _logger.info(str(e))
                if not sale_order.exists():
                    return {'success': False, 'error_msg': f"Sale Order ID {sale_order_id} not found."}
                try:
                    sale_order.order_line._compute_analytic_distribution()

                    if user.partner_id:
                        # sale_order.assign_to = user.partner_id.id
                        so_vals.update({'assign_to': user.partner_id.id})
                        crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [user.partner_id.id])],
                                                                         limit=1)
                        if crm_team:
                            so_vals.update({'team_id': crm_team.id})

                    worker_jr_cash_obj = request.env['worker.journal'].sudo().search_read([
                                                ('worker_ids', 'in', [user.partner_id.id]),
                                                ('active', '=', True),
                                                ('journal_type', '=', 'cash_van')
                                            ], ['journal_id'], limit=1)

                    worker_jr_credit_obj = request.env['worker.journal'].sudo().search_read([
                                ('worker_ids', 'in', [user.partner_id.id]),
                                ('active', '=', True),
                                ('journal_type', '=', 'presale')
                            ], ['journal_id'], limit=1)

                    if sale_order.partner_id.customer_type == "cash" or (
                            sale_order.partner_id.customer_type == "credit" and sale_order.partner_id.is_credit_hold == True):
                        # worker_jr_obj = worker_jr_cash_obj
                        worker_jr_obj = worker_jr_cash_obj[0]['journal_id'][0] if worker_jr_cash_obj else False
                    else:
                        # worker_jr_obj = worker_jr_credit_obj
                        worker_jr_obj =  worker_jr_credit_obj[0]['journal_id'][0] if worker_jr_credit_obj else False

                    if worker_jr_obj:
                        # sale_order.sale_journal = worker_jr_obj.journal_id.id
                        so_vals.update({'sale_journal': worker_jr_obj})


                except Exception as e:
                    _logger.info("Trying To Fix")
                    _logger.info(e)
                so_vals.update({'active': True})
                sale_order.write(so_vals)
                # sale_order.active = True
                if sale_order.is_discount_panding:
                    sale_order.approve_discount()
                if sale_order.state != 'sale':
                    start_time = time.time()  # capture start time
                    sale_order.with_user(user).sudo().action_confirm()
                    end_time = time.time()  # capture end time

                    elapsed_seconds = end_time - start_time
                    elapsed_minutes = elapsed_seconds / 60

                    _logger.info(f"Sale Order {sale_order.name} confirm time: "
                                 f"{elapsed_seconds:.2f} seconds "
                                 f"({elapsed_minutes:.2f} minutes)")


                delivery_result = []
                pending_pickings = sale_order.picking_ids.sorted(key=lambda p: p.picking_type_id.sequence)

                for picking in pending_pickings:
                    if picking.state != 'done':
                        picking.write({
                            'draft_trigger': True,
                            'custom_state_trigger': False,
                            'scheduled_date': picking.scheduled_date or fields.Datetime.now(),
                            'date_deadline': picking.date_deadline or fields.Datetime.now() + timedelta(days=3),
                        })

                processed_pickings = set()
                while pending_pickings:
                    picking = pending_pickings[0]
                    if picking.id in processed_pickings:
                        break
                    processed_pickings.add(picking.id)

                    if picking.state in ['draft', 'loaded_dispatched']:
                        start_time = time.time()  # capture start time
                        picking.with_user(user).sudo().action_confirm()
                        end_time = time.time()  # capture end time

                        elapsed_seconds = end_time - start_time
                        elapsed_minutes = elapsed_seconds / 60

                        _logger.info(f"Sale Order {sale_order.name} confirm time: "
                                     f"{elapsed_seconds:.2f} seconds "
                                     f"({elapsed_minutes:.2f} minutes)")



                    if not picking.picker_partner_id:
                        picking.picker_partner_id = sale_order.partner_id
                    # if not picking.picking_driver_id:
                    #     picking.picking_driver_id = sale_order.partner_id

                    if picking.state != 'done':
                        for move in picking.move_ids_without_package:
                            move.picker_partner_id = picking.picker_partner_id

                        _logger.info(">>>>>>>>>>>>>>>.......action_assign start......%s\n",datetime.now())
                        picking.with_user(user).sudo().action_assign()
                        _logger.info(">>>>>>>>>>>>>>>.......action_assign end......%s\n", datetime.now())
                        if not picking.has_packages:
                            try:
                                _logger.info(">>>>>>>>>>>>>>>.......action_put_in_pack start......%s\n", datetime.now())
                                picking.with_user(user).sudo().action_put_in_pack()
                                _logger.info(">>>>>>>>>>>>>>>.......action_put_in_pack end......%s\n", datetime.now())
                                picking.has_packages = True
                            except Exception as e:
                                _logger.info("can't put in pack")
                                _logger.info(str(e))
                                if 'There is nothing eligible to put in a pack' in str(e):
                                    for one_move in picking.move_ids_without_package:
                                        if one_move.quantity <= 0:
                                            one_move.quantity = one_move.product_uom_qty
                                    try:
                                        picking.with_user(user).sudo().action_put_in_pack()
                                        picking.has_packages = True
                                    except Exception as e:
                                        _logger.info("innner exception")
                                        _logger.info(str(e))


                        try:
                            custodian_id = request.env['custodian'].sudo().search_count(
                                [("responsible_custodian", "=", user.partner_id.id)])
                            if custodian_id == 0:
                                return {
                                    'success': False,
                                    'message': "You do not have a custodian call The IT department",
                                    'sale_order': {
                                        'id': sale_order.id,
                                        'name': sale_order.name,
                                    },
                                }
                            _logger.info(">>>>>>>>>>>>>>>.......button_validate start.....%s.\n", datetime.now())
                            is_partial = any(
                                line.quantity < line.product_uom_qty for line in picking.move_ids)
                            if not is_partial:
                                picking.with_user(user).with_context(
                                    mail_create_nosubscribe=False).sudo().button_validate()
                            else:
                                picking.action_cancel()
                            _logger.info(">>>>>>>>>>>>>>>.......button_validate end......%s\n", datetime.now())
                        except UserError as e:

                            error_message = str(e)

                            _logger.info("hhhhhhhhhhhhhhhhhhhhhh")
                            _logger.info(str(e))
                            # Detect missing-lot error
                            # if 'supply a Lot/Serial number' in error_message:
                            _logger.info('Auto‐assigning missing lots based on van_location quants...')
                            van_location = user.partner_id.van_location
                            # inside your “supply a Lot/Serial” handler…

                            for move in picking.move_ids_without_package.filtered(
                                    lambda m: m.product_id.tracking in ('lot', 'serial')
                            ):
                                # 1) Clear any bad or existing lines so you start fresh
                                if move.move_line_ids:
                                    _logger.info(">>>>>>>>>>>>>>>.......unlink end......%s\n", datetime.now())
                                    move.move_line_ids.sudo().unlink()
                                    _logger.info(">>>>>>>>>>>>>>>.......unlink end......%s\n", datetime.now())

                                # 2) Figure out exactly how much you still need
                                needed_qty = move.product_uom_qty

                                # 3) Grab quants, but assign smallest lots first so no single line ever exceeds needed
                                quants = request.env['stock.quant'].sudo().search([
                                    ('location_id', '=', van_location.id),
                                    ('product_id', '=', move.product_id.id),
                                    ('quantity', '>', 0),
                                ], order='quantity ASC')  # small->big

                                allocated = 0
                                for quant in quants:
                                    if allocated >= needed_qty:
                                        break

                                    # only take what you still need
                                    take = min(quant.quantity, needed_qty - allocated)
                                    if take <= 0:
                                        continue

                                    # 4) Create a brand-new line (no +=)
                                    request.env['stock.move.line'].sudo().create({
                                        'move_id': move.id,
                                        'location_id': move.location_id.id,
                                        'location_dest_id': move.location_dest_id.id,
                                        'product_id': move.product_id.id,
                                        'product_uom_id': move.product_uom.id,
                                        'lot_id': quant.lot_id.id,
                                        'qty_done': take,
                                    })

                                    allocated += take

                                if allocated < needed_qty:
                                    _logger.warning(
                                        "Picking %s move %s only got %.2f of %.2f",
                                        picking.name, move.id, allocated, needed_qty
                                    )

                            _logger.info(">>>>>>>>>>>>>>>.......button_validate end.....%s.\n", datetime.now())
                            is_partial = any(
                                line.quantity < line.product_uom_qty for line in picking.move_ids)
                            if not is_partial:
                                picking.with_user(user).with_context(
                                    mail_create_nosubscribe=False).sudo().button_validate()
                            else:
                                picking.action_cancel()
                            _logger.info(">>>>>>>>>>>>>>>.......button_validate end......%s\n", datetime.now())

                    delivery_result.append({
                        'picking_id': picking.id,
                        'name': picking.name,
                        'state': picking.state,
                        'type': picking.picking_type_id.name,
                    })

                    pending_pickings = sale_order.picking_ids.with_user(user).sudo().filtered(
                        lambda p: p.state not in ['done', 'cancel', 'loaded_dispatched']
                    ).sorted(key=lambda p: p.picking_type_id.sequence)

                invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                payment_result = []

                for invoice in invoices:
                    partner_is_credit = False
                    if invoice.partner_id.customer_type == 'credit':
                    # if invoice.partner_id.customer_type == 'credit' and not invoice.partner_id.is_credit_hold:
                        partner_is_credit = True
                    if invoice.payment_state not in ['paid', 'in_payment'] and not partner_is_credit:

                        ctx = {
                            'active_model': 'account.move',
                            'active_ids': [invoice.id],
                            'active_id': invoice.id,
                        }
                        journal = False

                        custodian_id = request.env['custodian'].sudo().search(
                            [("responsible_custodian", "=", user.partner_id.id)], limit=1)
                        for one in custodian_id.journal_ids:
                            if one.type == "cash":
                                journal = one
                        if not journal or not custodian_id:
                            return {
                                'success': False,
                                'message': "You do not have a custodian call The IT department",
                                'sale_order': {
                                    'id': sale_order.id,
                                    'name': sale_order.name,
                                },
                            }

                        # if sale_order.sale_journal:
                        #     journal = sale_order.sale_journal
                        # else:
                        #     journal = request.env['account.journal'].sudo().search([('name', '=', 'Cash')], limit=1)
                        journal_id = journal.id
                        payment_wizard = request.env['account.payment.register'].with_user(user).with_context(
                            ctx).sudo().create({
                            'journal_id': journal_id,
                            'amount': invoice.amount_residual,
                            'payment_date': fields.Date.to_string(date.today()),
                            # 'payment_date': fields.Date.context_today(invoice),
                        })

                        action_result = payment_wizard.with_user(user).sudo().action_create_payments()
                        payment_result = []
                        if action_result.get('res_id'):
                            payment = request.env['account.payment'].sudo().browse(action_result['res_id'])
                            payment.sudo().collector_name = user.partner_id.name
                            if payment.exists():
                                access_token = payment._ensure_portal_token()
                                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                                receipt_url = f"{base_url}/my/payment_method_id/{payment.id}?access_token={access_token}&report_type=pdf&download=true"
                                payment_result.append({
                                    'payment_id': payment.id,
                                    'name': payment.name,
                                    'amount': payment.amount,
                                    'receipt_pdf_download': receipt_url,
                                })
                if not invoices or len(invoices) <= 0:
                    customer_payment_type = "credit"
                tax_invoice_4inch_pdf_url = None
                if sale_order_id and customer_payment_type == "cash":
                    print("Inside SLA EODER API:", sale_order_id)
                    sale_order = request.env['sale.order'].browse(sale_order_id)
                    access_token = sale_order._ensure_portal_token()
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{sale_order.id}?access_token={access_token}&report_type=pdf&download=true"
                sale_order_end_datetime = datetime.now()

                delta = sale_order_end_datetime - sale_order_start_datetime
                # Convert timedelta to string (HH:MM:SS)
                hours, remainder = divmod(delta.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                sale_order.api_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

                return {
                    'success': True,
                    'message': 'Sale Order activated and delivery created.',
                    'sale_order': {
                        'id': sale_order.id,
                        'name': sale_order.name,
                    },
                    'delivery': delivery_result,
                    'payment': payment_result,
                    'customer_payment_type': customer_payment_type,
                    'tax_invoice_4inch_pdf': tax_invoice_4inch_pdf_url,

                }


            # ✅ Else: Normal create + delivery process
            partner_id = values.get('partner_id')
            customer_id = values.get('customer_id')
            order_creation_source = values.get('order_creation_source')
            product_lines = values.get('products', [])

            partner = request.env['res.partner'].sudo().browse(partner_id)
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid partner ID.'}
            if not customer.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            order_lines = []
            for line in product_lines:
                product_id = line.get('product_id')
                quantity = line.get('quantity')
                price_unit = line.get('price_unit')
                uom_id = line.get('uom_id')
                discount = line.get('discount', 0)
                packaging_id = line.get('product_packaging_id')

                if not all([product_id, quantity, price_unit, uom_id]):
                    return {'success': False, 'error_msg': 'Missing required product fields.'}

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists() or not product.active:
                    template = request.env['product.template'].sudo().browse(product_id)
                    product = template.product_variant_ids[:1] if template.exists() else False
                    if not product or not product.active:
                        return {'success': False, 'error_msg': f"Invalid product ID: {product_id}"}

                if packaging_id:
                    packaging = request.env['product.packaging'].sudo().browse(int(packaging_id))
                    if packaging.exists():
                        quantity *= packaging.qty
                        uom_id = packaging.product_uom_id.id

                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'product_uom': uom_id,
                    'name': product.name,
                }))

            if not order_lines:
                return {'success': False, 'error_msg': 'No valid order lines.'}

            sale_order = request.env['sale.order'].with_user(user).sudo().create({
                'partner_id': customer.id,
                'order_creation_source': order_creation_source,
                'date_order': fields.Datetime.now(),
                'commitment_date': fields.Datetime.now(),
                'order_line': order_lines,
                'company_id': user.company_id.id,
            })

            worker_jr_cash_obj = request.env['worker.journal'].sudo().search([
                ('worker_ids','in',user.partner_id.id),
                ('active','=',True),
                ('journal_type','=','cash_van')
            ],limit=1)

            worker_jr_credit_obj = request.env['worker.journal'].sudo().search([
                ('worker_ids','in',user.partner_id.id),
                ('active','=',True),
                ('journal_type','=','presale')
            ],limit=1)

            if customer.customer_type == "cash" or (customer.customer_type == "credit" and customer.is_credit_hold == True):
                worker_jr_obj = worker_jr_cash_obj
            else:
                worker_jr_obj = worker_jr_credit_obj

            if worker_jr_obj and worker_jr_obj.journal_id:
                sale_order.sale_journal = worker_jr_obj.journal_id.id

            sale_order.with_user(user).sudo().action_confirm()

            delivery_result = []
            pending_pickings = sale_order.picking_ids.sorted(key=lambda p: p.picking_type_id.sequence)

            for picking in sale_order.picking_ids:
                picking.draft_trigger = True
                picking.custom_state_trigger = False
                picking.scheduled_date = picking.scheduled_date or fields.Datetime.now()
                picking.date_deadline = picking.date_deadline or fields.Datetime.now() + timedelta(days=3)

            processed_pickings = set()
            while pending_pickings:
                picking = pending_pickings[0]
                if picking.id in processed_pickings:
                    break
                processed_pickings.add(picking.id)

                if picking.state in ['draft', 'loaded_dispatched']:
                    picking.sudo().with_user(user).action_confirm()

                if not picking.picker_partner_id:
                    picking.picker_partner_id = sale_order.partner_id
                if not picking.picking_driver_id:
                    picking.picking_driver_id = sale_order.partner_id

                picking.sudo().with_user(user).action_assign()

                for move in picking.move_ids_without_package:
                    qty = move.product_uom_qty
                    # if not move.move_line_ids:
                    #     vals = {
                    #         'picking_id': picking.id,
                    #         'move_id': move.id,
                    #         'product_id': move.product_id.id,
                    #         'product_uom_id': move.product_uom.id,
                    #         'qty_done': qty,
                    #         'location_id': move.location_id.id,
                    #         'location_dest_id': move.location_dest_id.id,
                    #     }
                        # if move.product_id.tracking != 'none':
                        #     lot = request.env['stock.lot'].sudo().search([
                        #         ('product_id', '=', move.product_id.id)
                        #     ], limit=1)
                        #     if not lot:
                        #         raise UserError(
                        #             f"Lot/Serial Number required for product: {move.product_id.display_name}")
                        #     vals['lot_id'] = lot.id
                        # request.env['stock.move.line'].sudo().create(vals)
                    # else:
                    #     for ml in move.move_line_ids:
                    #         ml.qty_done = qty
                    #         if move.product_id.tracking != 'none' and not ml.lot_id:
                    #             lot = request.env['stock.lot'].sudo().search([
                    #                 ('product_id', '=', move.product_id.id)
                    #             ], limit=1)
                    #             if not lot:
                    #                 raise UserError(
                    #                     f"Lot/Serial Number required for product: {move.product_id.display_name}")
                    #             ml.lot_id = lot.id
                    move.picker_partner_id = picking.picker_partner_id

                picking.sudo().with_user(user).action_assign()
                if not picking.has_packages:
                    picking.sudo().with_user(user).action_put_in_pack()
                    picking.has_packages = True
                is_partial = any(
                    line.quantity < line.product_uom_qty for line in picking.move_ids)
                if not is_partial:
                    picking.with_context(mail_create_nosubscribe=False).sudo().with_user(user).button_validate()
                else:
                    picking.action_cancel()
                # picking.with_context(mail_create_nosubscribe=False).sudo().with_user(user).button_validate()

                delivery_result.append({
                    'picking_id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'type': picking.picking_type_id.name,
                })

                pending_pickings = sale_order.picking_ids.sudo().with_user(user).filtered(
                    lambda p: p.state not in ['done', 'cancel', 'loaded_dispatched']
                ).sorted(key=lambda p: p.picking_type_id.sequence)
            invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            payment_result = []

            for invoice in invoices:
                if invoice.payment_state not in ['paid', 'in_payment']:

                    ctx = {
                        'active_model': 'account.move',
                        'active_ids': [invoice.id],
                        'active_id': invoice.id,
                    }
                    journal = False
                    if sale_order.sale_journal:
                        journal = sale_order.sale_journal
                    else:
                        journal = request.env['account.journal'].sudo().search([('type', '=', 'Cash')], limit=1)
                    journal_id = journal.id if journal else 29
                    payment_wizard = request.env['account.payment.register'].with_user(user).with_context(
                        ctx).sudo().create({
                        'journal_id': journal_id,
                        'amount': invoice.amount_residual,
                        'payment_date': fields.Date.to_string(date.today()),
                        # 'payment_date': fields.Date.context_today(invoice),
                    })

                    action_result = payment_wizard.with_user(user).sudo().action_create_payments()
                    payment_result = []
                    if action_result.get('res_id'):
                        payment = request.env['account.payment'].sudo().browse(action_result['res_id'])
                        if payment.exists():
                            access_token = payment._ensure_portal_token()
                            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                            receipt_url = f"{base_url}/my/payment_method_id/{payment.id}?access_token={access_token}&report_type=pdf&download=true"
                            payment_result.append({
                                'payment_id': payment.id,
                                'name': payment.name,
                                'amount': payment.amount,
                                'receipt_pdf_download': receipt_url,
                            })

            tax_invoice_4inch_pdf_url = None
            if sale_order:
                access_token = sale_order._ensure_portal_token()
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{sale_order.id}?access_token={access_token}&report_type=pdf&download=true"

            response = {
                'success': True,
                'message': 'Sale Order and Delivery created successfully.',
                'sale_order': {
                    'id': sale_order.id,
                    'name': sale_order.name,
                },
                'delivery': delivery_result,
                'payment': payment_result,
                'tax_invoice_4inch_pdf': tax_invoice_4inch_pdf_url
            }

        except Exception as e:
            _logger.exception("Error in /create_sale_order_with_delivery")
            response = {'success': False, 'error_msg': str(e)}

        return response

    @http.route('/api/v1/fix_sale_order_with_delivery', type='json', auth='public', methods=['POST'], csrf=False)
    def fix_sale_order_with_delivery(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = values.get('sale_order_id')
            is_active = values.get('is_active', False)
            po_number = values.get('po_number', False)

            user = request.env['res.users'].browse(user_id)

            customer_payment_type = "cash"
            if sale_order_id and is_active:
                sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
                if po_number:
                    sale_order.po_number = po_number

                try:
                    van_location = user.partner_id.van_location
                    if van_location and van_location.warehouse_id:
                        sale_order.warehouse_id = van_location.warehouse_id.id
                except Exception as e:
                    _logger.info("error into the warehouse")
                    _logger.info(str(e))
                if not sale_order.exists():
                    return {'success': False, 'error_msg': f"Sale Order ID {sale_order_id} not found."}

                try:
                    sale_order.order_line._compute_analytic_distribution()

                    worker_jr_cash_obj = request.env['worker.journal'].sudo().search([
                        ('worker_ids', 'in', user.partner_id.id),
                        ('active', '=', True),
                        ('journal_type', '=', 'cash_van')
                    ], limit=1)

                    worker_jr_credit_obj = request.env['worker.journal'].sudo().search([
                        ('worker_ids', 'in', user.partner_id.id),
                        ('active', '=', True),
                        ('journal_type', '=', 'presale')
                    ], limit=1)

                    if sale_order.partner_id.customer_type == "cash" or (
                            sale_order.partner_id.customer_type == "credit" and sale_order.partner_id.is_credit_hold):
                        worker_jr_obj = worker_jr_cash_obj
                    else:
                        worker_jr_obj = worker_jr_credit_obj

                    if worker_jr_obj and worker_jr_obj.journal_id:
                        sale_order.sale_journal = worker_jr_obj.journal_id.id

                except Exception as e:
                    _logger.info("Trying To Fix")
                    _logger.info(e)

                sale_order.active = True
                if sale_order.is_discount_panding:
                    sale_order.approve_discount()
                if sale_order.state != 'sale':
                    sale_order.with_user(user).sudo().action_confirm()

                delivery_result = []
                pending_pickings = sale_order.picking_ids.sorted(key=lambda p: p.picking_type_id.sequence)

                for picking in pending_pickings:
                    if picking.state != 'done':
                        picking.draft_trigger = True
                        picking.custom_state_trigger = False
                        picking.scheduled_date = picking.scheduled_date or fields.Datetime.now()
                        picking.date_deadline = picking.date_deadline or fields.Datetime.now() + timedelta(days=3)

                processed_pickings = set()
                while pending_pickings:
                    picking = pending_pickings[0]
                    if picking.id in processed_pickings:
                        break
                    processed_pickings.add(picking.id)

                    if picking.state in ['draft', 'loaded_dispatched']:
                        picking.with_user(user).sudo().action_confirm()

                    if not picking.picker_partner_id:
                        picking.picker_partner_id = sale_order.partner_id
                    if not picking.picking_driver_id:
                        picking.picking_driver_id = sale_order.partner_id

                    if picking.state != 'done':
                        picking.with_user(user).sudo().action_assign()

                        for move in picking.move_ids_without_package:
                            move.picker_partner_id = picking.picker_partner_id

                        picking.with_user(user).sudo().action_assign()
                        if not picking.has_packages:
                            try:
                                picking.with_user(user).sudo().action_put_in_pack()
                                picking.has_packages = True
                            except Exception as e:
                                _logger.info("can't put in pack: %s", e)
                                if 'There is nothing eligible to put in a pack' in str(e):
                                    for one_move in picking.move_ids_without_package:
                                        if getattr(one_move, 'quantity', 0) <= 0:
                                            one_move.quantity = one_move.product_uom_qty
                                    try:
                                        picking.with_user(user).sudo().action_put_in_pack()
                                        picking.has_packages = True
                                    except Exception as e2:
                                        _logger.info("inner exception: %s", e2)

                        try:
                            custodian_id = request.env['custodian'].sudo().search(
                                [("responsible_custodian", "=", user.partner_id.id)], limit=1)
                            if not custodian_id:
                                return {
                                    'success': False,
                                    'message': "You do not have a custodian. Call the IT department.",
                                    'sale_order': {'id': sale_order.id, 'name': sale_order.name},
                                }
                            picking.with_user(user).with_context(
                                mail_create_nosubscribe=False).sudo().button_validate()
                        except UserError as e:
                            # Auto-assign missing lots from van_location for tracked products, then validate again
                            van_location = user.partner_id.van_location
                            for move in picking.move_ids_without_package:
                                if move.product_id.tracking in ('lot', 'serial'):
                                    self._assign_lots_exact_fit(move, van_location)
                                else:
                                    # Non-tracked: ensure qty_done equals need
                                    need = move.product_uom_qty
                                    if move.move_line_ids:
                                        for ml in move.move_line_ids:
                                            ml.sudo().qty_done = need
                                    else:
                                        request.env['stock.move.line'].sudo().create({
                                            'move_id': move.id,
                                            'picking_id': picking.id,
                                            'product_id': move.product_id.id,
                                            'product_uom_id': move.product_uom.id,
                                            'location_id': move.location_id.id,
                                            'location_dest_id': move.location_dest_id.id,
                                            'qty_done': need,
                                        })

                            picking.with_user(user).with_context(
                                mail_create_nosubscribe=False).sudo().button_validate()

                    delivery_result.append({
                        'picking_id': picking.id,
                        'name': picking.name,
                        'state': picking.state,
                        'type': picking.picking_type_id.name,
                        'picking_driver_id': user.partner_id.id,
                    })

                    pending_pickings = sale_order.picking_ids.with_user(user).sudo().filtered(
                        lambda p: p.state not in ['done', 'cancel', 'loaded_dispatched']
                    ).sorted(key=lambda p: p.picking_type_id.sequence)

                new_invoices = self._deliver_remaining_qty_only(sale_order, user)

                # ===== KEY CHANGE (A): update ONE existing invoice if present, else create exactly ONE =====
                target_invoice = self._update_existing_invoice_with_remaining(sale_order, user)

                # Prepare payment (cash customers only, and only if unpaid)
                payment_result = []
                partner_is_credit = (sale_order.partner_id.customer_type == 'credit'
                                     and not sale_order.partner_id.is_credit_hold)
                if (not partner_is_credit
                        and target_invoice.state == 'posted'
                        and target_invoice.payment_state not in ('paid', 'in_payment')
                        and float(target_invoice.amount_residual or 0) > 0):

                    ctx = {
                        'active_model': 'account.move',
                        'active_ids': [target_invoice.id],
                        'active_id': target_invoice.id,
                    }

                    journal = False
                    custodian_id = request.env['custodian'].sudo().search(
                        [("responsible_custodian", "=", user.partner_id.id)], limit=1)
                    if custodian_id:
                        for one in custodian_id.journal_ids:
                            if one.type == "cash":
                                journal = one
                                break
                    if not journal:
                        return {
                            'success': False,
                            'message': "You do not have a cash journal. Call the IT department.",
                            'sale_order': {'id': sale_order.id, 'name': sale_order.name},
                        }

                    pay_wiz = request.env['account.payment.register'].with_user(user).with_context(ctx).sudo().create({
                        'journal_id': journal.id,
                        'amount': target_invoice.amount_residual,
                        'payment_date': fields.Date.to_string(date.today()),
                    })
                    action_result = pay_wiz.with_user(user).sudo().action_create_payments()
                    if action_result.get('res_id'):
                        payment = request.env['account.payment'].sudo().browse(action_result['res_id'])
                        if payment.exists():
                            payment.sudo().collector_name = user.partner_id.name
                            access_token = payment._ensure_portal_token()
                            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                            receipt_url = f"{base_url}/my/payment_method_id/{payment.id}?access_token={access_token}&report_type=pdf&download=true"
                            payment_result.append({
                                'payment_id': payment.id,
                                'name': payment.name,
                                'amount': payment.amount,
                                'receipt_pdf_download': receipt_url,
                            })

                # Cash vs credit flag for your print link
                customer_payment_type = "credit" if partner_is_credit else "cash"
                tax_invoice_4inch_pdf_url = None
                if customer_payment_type == "cash":
                    access_token = sale_order._ensure_portal_token()
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{sale_order.id}?access_token={access_token}&report_type=pdf&download=true"

                return {
                    'success': True,
                    'message': 'Sale Order activated, delivered, and invoice updated.',
                    'sale_order': {'id': sale_order.id, 'name': sale_order.name},
                    'delivery': delivery_result,
                    'payment': payment_result,
                    'customer_payment_type': customer_payment_type,
                    'tax_invoice_4inch_pdf': tax_invoice_4inch_pdf_url,
                    'invoice_id': target_invoice.id,
                    'invoice_number': target_invoice.name,
                }

            # ===== Normal create flow (unchanged except: no duplicate payments & using same invoicing policy) =====
            # ... keep your “create new SO” branch as-is, or reuse the same invoice logic above ...

        except Exception as e:
            _logger.exception("Error in /create_sale_order_with_delivery")
            response = {'success': False, 'error_msg': str(e)}

        return response

    def _deliver_remaining_qty_only(self, sale_order, user):
        """Create/confirm/assign/validate a picking for any remaining SO qty.
        This method DOES NOT create invoices. It only ensures all deliverable qty is delivered.
        """
        SaleOrder = request.env['sale.order'].sudo()
        StockPicking = request.env['stock.picking'].sudo()
        StockMove = request.env['stock.move'].sudo()
        StockMoveLine = request.env['stock.move.line'].sudo()
        Quant = request.env['stock.quant'].sudo()

        # Confirm SO if needed
        if sale_order.state != 'sale':
            sale_order.with_user(user).sudo().action_confirm()

        # Compute remaining per line
        remaining_lines = []
        for line in sale_order.order_line:
            remaining = (line.product_uom_qty or 0.0) - (line.qty_delivered or 0.0)
            if remaining > 0:
                remaining_lines.append((line, remaining))

        if not remaining_lines:
            # Nothing left to deliver; just return
            return

        user_partner = user.partner_id
        warehouse = user_partner.sudo().van_location.warehouse_id
        van_location = user_partner.van_location

        if not warehouse:
            raise UserError("No warehouse found to create remaining delivery.")
        if not van_location:
            raise UserError("No van location found for this user.")

        picking_type = warehouse.out_type_id
        if not picking_type:
            raise UserError("No outbound picking type configured for the warehouse.")

        # Build a fresh picking for remaining
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': sale_order.partner_shipping_id.id or sale_order.partner_id.id,
            'origin': sale_order.name,
            'sale_id': sale_order.id,
            'location_id': van_location.id,
            'picking_driver_id': user.partner_id.id,
            'location_dest_id': sale_order.partner_id.property_stock_customer.id,
            'group_id': sale_order.procurement_group_id.id,
            'scheduled_date': fields.Datetime.now(),
        }
        picking = StockPicking.with_user(user).sudo().create(picking_vals)

        # Create moves for remaining
        for line, remaining in remaining_lines:
            StockMove.with_user(user).sudo().create({
                'name': line.name or line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': remaining,
                'product_uom': line.product_uom.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'sale_line_id': line.id,
                'company_id': sale_order.company_id.id,
                'picker_partner_id': user.partner_id.id,
            })

        # Confirm & assign
        picking.with_user(user).sudo().action_confirm()
        picking.with_user(user).sudo().action_assign()

        # Fill move lines (respect tracking & van_location)
        van_location = user.partner_id.van_location
        for move in picking.move_ids_without_package:
            need = move.product_uom_qty
            if need <= 0:
                continue
            if move.product_id.tracking in ('lot', 'serial'):
                self._assign_lots_exact_fit(move, van_location)
            else:
                if move.move_line_ids:
                    for ml in move.move_line_ids:
                        ml.sudo().qty_done = need
                else:
                    request.env['stock.move.line'].sudo().create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'qty_done': need,
                    })
        # Optional pack (ignore if nothing to pack)
        try:
            if not picking.has_packages:
                picking.with_user(user).sudo().action_put_in_pack()
                picking.has_packages = True
        except Exception:
            pass

        # Validate (no emails)
        picking.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()

        # Done. **No invoice creation here.** We will update/post the invoice afterwards.

    def _update_existing_invoice_with_remaining(self, sale_order, user):
        """
        Update exactly ONE invoice for this SO (prefer latest posted). If none exists,
        create ONE invoice for delivered-but-uninvoiced qty, then post it.
        Keeps the SAME number & date when updating an existing posted invoice.
        """

        Move = request.env['account.move'].sudo()

        # Prefer posted invoices, else drafts
        invs = sale_order.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
        posted = invs.filtered(lambda m: m.state == 'posted')
        target = False
        if posted:
            target = posted.sorted(key=lambda m: (m.invoice_date or m.date or m.create_date), reverse=True)[0]
        elif invs.filtered(lambda m: m.state == 'draft'):
            target = invs.filtered(lambda m: m.state == 'draft')[0]

        # If no invoice at all: create ONE from the SO (delivery-based), then post it and return
        if not target:
            action = sale_order.with_user(user).sudo()._create_invoices()
            target = sale_order.invoice_ids.filtered(lambda m: m.state in ('draft', 'posted')).sorted(
                key=lambda m: m.create_date, reverse=True
            )[:1]
            if target:
                target = target[0]
                company = target.company_id or user.company_id
                if target.state == 'draft':
                    target.with_company(company).with_context(
                        allowed_company_ids=[company.id], force_company=company.id
                    ).sudo().action_post()
                return target
            raise UserError("Could not create an invoice for this Sale Order.")

        # We have an invoice: top it up with qty_to_invoice and keep same number/date
        if target.payment_state in ('paid', 'in_payment'):
            raise UserError("Invoice is already paid/in payment. Remove payment first, then retry.")

        original_name = target.name or '/'
        original_date = target.invoice_date
        original_ref = target.ref

        if target.state == 'posted':
            # Journal must allow cancellation
            target.button_draft()

        # Add only the missing (positive) qty_to_invoice per SO line
        lines_to_add = []
        for so_line in sale_order.order_line:
            qty_needed = float_round(
                so_line.qty_to_invoice or 0.0,
                precision_rounding=so_line.product_uom.rounding or 0.01
            )
            if qty_needed <= 0:
                continue

            vals = so_line._prepare_invoice_line()
            vals.update({
                'move_id': target.id,
                'quantity': qty_needed,
                'sale_line_ids': [(6, 0, [so_line.id])],
            })

            existing = target.invoice_line_ids.filtered(lambda l: l.sale_line_ids and so_line in l.sale_line_ids)
            if existing:
                existing[0].write({'quantity': existing[0].quantity + qty_needed})
            else:
                lines_to_add.append((0, 0, vals))

        if lines_to_add:
            target.write({'invoice_line_ids': lines_to_add})

        # Recompute totals safely across versions
        self._recompute_invoice_totals_compat(target)

        # Restore number/date so Odoo won't resequence
        target.write({
            'name': original_name,
            'invoice_date': original_date,
            'ref': original_ref,
        })

        company = target.company_id or user.company_id
        target.with_company(company).with_context(
            allowed_company_ids=[company.id],
            force_company=company.id
        ).sudo().action_post()

        if original_name and target.name != original_name:
            # If this ever triggers, your journal isn't allowing proper reuse. Fix journal settings.
            raise UserError("Invoice numbering changed unexpectedly. Check journal cancel/reuse settings.")

        return target

    def _recompute_invoice_totals_compat(self, move):
        """
        Cross-version recompute for account.move after modifying invoice_line_ids.
        Tries new → old APIs; safe no-ops if a method doesn't exist.
        """
        # Newer API (if present)
        if hasattr(move, '_recompute_dynamic_lines'):
            try:
                move._recompute_dynamic_lines(recompute_all_taxes=True)
                return
            except Exception:
                pass

        # Onchange-style recompute (some versions)
        if hasattr(move, '_onchange_recompute_dynamic_lines'):
            try:
                move._onchange_recompute_dynamic_lines()
            except Exception:
                pass

        # Older granular fallbacks
        if hasattr(move, '_recompute_tax_lines'):
            try:
                move._recompute_tax_lines()
            except Exception:
                pass

        if hasattr(move, '_recompute_payment_terms_lines'):
            try:
                move._recompute_payment_terms_lines()
            except Exception:
                pass

        if hasattr(move, '_recompute_cash_rounding'):
            try:
                move._recompute_cash_rounding()
            except Exception:
                pass

        if hasattr(move, '_onchange_currency'):
            try:
                move._onchange_currency()
            except Exception:
                pass

        if hasattr(move, '_onchange_partner_id'):
            try:
                move._onchange_partner_id()
            except Exception:
                pass

    def _assign_lots_exact_fit(self, move, van_location):
        """Assign lots from van_location to match needed qty as tightly as possible.
        - FEFO (use_date/life_date asc), then smallest qty first
        - Skip expired lots
        - Exact fit attempts (1-quant, then 2-quant) before greedy
        - Handles 'serial' tracking with qty_done=1 per serial
        """
        Quant = request.env['stock.quant'].sudo()
        today = fields.Datetime.now()

        # How much we still need (respecting existing qty_done, if any)
        uom_rounding = move.product_uom.rounding or 0.01
        needed = (move.product_uom_qty or 0.0)
        if move.move_line_ids:
            done = sum(ml.qty_done for ml in move.move_line_ids)
            needed = max(0.0, needed - done)

        if needed <= 0:
            return

        # Start clean for tracked products; for non-tracked we’ll write qty_done directly elsewhere
        if move.product_id.tracking in ('lot', 'serial') and move.move_line_ids:
            move.move_line_ids.sudo().unlink()

        # Pull candidate quants from van location
        quants = Quant.search([
            ('location_id', '=', van_location.id),
            ('product_id', '=', move.product_id.id),
            ('quantity', '>', 0),
        ])

        # Build annotated list with lot, quantity, use_date/life_date
        candidates = []
        for q in quants:
            lot = q.lot_id
            # Skip quants without lot for tracked products
            if move.product_id.tracking in ('lot', 'serial') and not lot:
                continue

            # FEFO dates (prefer use_date; fallback to life_date; else large)
            use_dt = None
            if lot:
                use_dt = lot.use_date or lot.expiration_date
                # Skip expired lots
                # if lot.expiration_date and lot.expiration_date < today:
                #     continue

            candidates.append({
                'quant': q,
                'qty': float(q.quantity),
                'lot': lot,
                'fefo': use_dt or fields.Datetime.to_datetime('2099-12-31 23:59:59'),
            })

        if not candidates:
            return  # nothing we can do; validate may backorder

        # Sort FEFO, then smallest qty to ease exact fits and avoid overshoot
        candidates.sort(key=lambda c: (c['fefo'], c['qty']))

        # SERIAL handling: take one serial per unit needed
        if move.product_id.tracking == 'serial':
            allocated = 0.0
            for c in candidates:
                if allocated >= needed:
                    break
                if c['qty'] <= 0:
                    continue
                # One serial per line
                request.env['stock.move.line'].sudo().create({
                    'move_id': move.id,
                    'picking_id': move.picking_id.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': c['lot'].id,
                    'qty_done': 1.0,
                })
                allocated += 1.0
            return

        # LOT-tracked or none: try exact single-quant match first
        # (round to uom precision when comparing)
        def _round(x):  # local rounding
            from odoo.tools.float_utils import float_round
            return float_round(x, precision_rounding=uom_rounding)

        rneeded = _round(needed)
        for c in candidates:
            if _round(c['qty']) == rneeded:
                request.env['stock.move.line'].sudo().create({
                    'move_id': move.id,
                    'picking_id': move.picking_id.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': c['lot'].id if c['lot'] else False,
                    'qty_done': rneeded,
                })
                return

        # Try two-quant exact sum (cap to first ~50 for speed)
        seen = {}
        capped = candidates[:50]
        for c in capped:
            comp = _round(rneeded - _round(c['qty']))
            if comp in seen:
                # Use c and its complement
                c2 = seen[comp]
                # First quant
                request.env['stock.move.line'].sudo().create({
                    'move_id': move.id,
                    'picking_id': move.picking_id.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': c['lot'].id if c['lot'] else False,
                    'qty_done': _round(c['qty']),
                })
                # Second quant
                request.env['stock.move.line'].sudo().create({
                    'move_id': move.id,
                    'picking_id': move.picking_id.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': c2['lot'].id if c2['lot'] else False,
                    'qty_done': comp,
                })
                return
            seen[_round(c['qty'])] = c

        # Greedy smallest-first (FEFO) without exceeding need
        allocated = 0.0
        for c in candidates:
            if allocated >= needed:
                break
            take = min(c['qty'], needed - allocated)
            if take <= 0:
                continue
            request.env['stock.move.line'].sudo().create({
                'move_id': move.id,
                'picking_id': move.picking_id.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'lot_id': c['lot'].id if c['lot'] else False,
                'qty_done': take,
            })
            allocated += take

    @http.route('/api/v1/upload_sale_order_img_button', type='json', auth='none', methods=['POST'], csrf=False)
    def upload_sale_order_img_preview(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = values.get('sale_order_id')
            po_number = values.get('po_number')
            po_image_b64 = values.get('uploaded_po_order_img', None)

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)

            if sale_order_id:
                sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
                if po_number:
                    sale_order.po_number = po_number
                try:
                    if po_image_b64:

                        request.env['ir.attachment'].sudo().create({
                            'name': f'PO_Image_{sale_order.name or sale_order.id}.jpg',
                            'res_model': 'sale.order',
                            'res_id': sale_order.id,
                            'type': 'binary',
                            'mimetype': 'image/jpeg',
                            'datas': po_image_b64,
                        })

                        return {
                            'success': True,
                            'message': f'Sale order ID {sale_order_id} Image Uploaded successfully.',
                        }


                except Exception as e:
                    _logger.exception("Error in Uploaded Image!")
                    response = {'success': False, 'error_msg': str(e)}
                    return response

            else:
                response = {'success': False, 'error_msg': "Sale Order is not exist!!"}


        except Exception as e:
            _logger.exception("Error in /api/v1/upload_sale_order_img_button")
            response = {'success': False, 'error_msg': str(e)}

        return response

    def _cap_foc_to_available_stock(self, env, sale_order, van_partner):
        """
        Limit FOC (buy_x_get_y) lines so: paid_qty + foc_qty <= available van stock
        Uses lot.expiration_date when present (unlotted/No expiry = usable).
        """
        van_loc = getattr(van_partner, 'van_location', False) or getattr(van_partner, 'van_location_id', False)
        if not van_loc:
            return
        _logger.info("Good inside")
        # ONLY buy_x_get_y reward product lines (your requested condition)
        foc_lines = sale_order.order_line.filtered(
            lambda l: l.reward_id
                      and l.reward_id.program_id.program_type == 'buy_x_get_y'
                      and l.product_id
                      and not l.display_type
                      and l.product_id.type == 'consu'
        )
        if not foc_lines:
            return
        _logger.info("Good inside2")

        products = foc_lines.mapped('product_id')
        product_ids = products.ids

        # Available in van, ignoring expired lots (expiration_date)
        now = fields.Datetime.now()
        Quant = env['stock.quant'].sudo()
        groups = Quant.read_group(
            domain=[
                ('location_id', 'child_of', van_loc.id),
                ('product_id', 'in', product_ids),
                ('quantity', '>', 0),
                '|', ('lot_id', '=', False),
                '|', ('lot_id.expiration_date', '=', False),
                ('lot_id.expiration_date', '>', now),
            ],
            fields=['product_id', 'quantity:sum', 'reserved_quantity:sum'],
            groupby=['product_id'],
        )
        _logger.info("Good inside3")
        _logger.info(groups)
        avail_by_prod = {
            g['product_id'][0]: (
                    (g.get('quantity_sum') or g.get('quantity') or 0.0)
                    - (g.get('reserved_quantity_sum') or g.get('reserved_quantity') or 0.0)
            )
            for g in groups
        }
        _logger.info("avail_by_prod = %s", avail_by_prod)
        _logger.info("Good inside4")
        _logger.info(avail_by_prod)

        def _to_product_uom(line, qty):
            if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
                return line.product_uom._compute_quantity(qty, line.product_id.uom_id, round=False)
            return qty
        _logger.info("Good inside5")

        for product in products:
            prod_lines = sale_order.order_line.filtered(lambda l: l.product_id == product)
            # paid = non-reward lines only
            paid_qty = sum(_to_product_uom(l, l.product_uom_qty) for l in prod_lines if not l.is_reward_line)
            foc_prod_lines = prod_lines.filtered(
                lambda l: l.reward_id and l.reward_id.program_id.program_type == 'buy_x_get_y'
            )
            if not foc_prod_lines:
                continue

            foc_total = sum(_to_product_uom(l, l.product_uom_qty) for l in foc_prod_lines)
            avail = max(0.0, avail_by_prod.get(product.id, 0.0))

            max_foc_kept = max(0.0, avail - paid_qty)
            if max_foc_kept <= 0.0:
                foc_prod_lines._reset_loyalty(complete=True)
                foc_prod_lines.with_context(tracking_disable=True, mail_notrack=True, mail_create_nolog=True).unlink()
                continue

            if foc_total <= max_foc_kept + 1e-9:
                continue  # within capacity

            # Trim down deterministically
            remaining = max_foc_kept
            for line in foc_prod_lines.sorted(key=lambda l: (l.sequence, l.id)):
                q_prod = _to_product_uom(line, line.product_uom_qty)
                if remaining <= 1e-9:
                    # line._reset_loyalty(complete=True)
                    line.with_context(tracking_disable=True, mail_notrack=True, mail_create_nolog=True).unlink()
                    continue
                if q_prod <= remaining + 1e-9:
                    remaining -= q_prod
                else:
                    # partial keep → write just the qty
                    new_qty = remaining
                    if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
                        new_qty = line.product_id.uom_id._compute_quantity(remaining, line.product_uom, round=False)
                    line.with_context(tracking_disable=True, mail_notrack=True, mail_create_nolog=True).write({
                        'product_uom_qty': new_qty
                    })
                    remaining = 0.0

        env.flush_all()

    # utils/sale_loyalty_wizard.py  (or at top of your controller file)
    def apply_all_rewards_via_wizard(self, env, sale_order, product_choices=None, max_loops=50):
        """
        Runs the 'sale.loyalty.reward.wizard' in a loop until no rewards remain.
        - product_choices: optional {reward_id: product_id} mapping for multi_product rewards
        - Returns list of applied reward ids
        """
        applied = []
        loops = 0
        _logger.info("inside apply rewards via wizard")

        while loops < max_loops:
            _logger.info("inside the loop %s" % loops)
            # Get the exact context the button would use
            action = sale_order.action_open_reward_wizard()
            ctx = action.get('context') or {}
            if isinstance(ctx, str):
                ctx = safe_eval(ctx)
            wiz_env = env['sale.loyalty.reward.wizard'].with_context(ctx)

            # First wizard: just to compute claimable rewards
            probe_wiz = wiz_env.create({'order_id': sale_order.id})
            reward_ids = probe_wiz.reward_ids
            if not reward_ids:
                break  # nothing left to claim

            # Pick ONE reward at a time (lets the order refresh between iterations)
            reward = reward_ids[0]
            vals = {
                'order_id': sale_order.id,
                'selected_reward_id': reward.id,
            }
            # Multi-product rewards: choose product explicitly
            if reward.multi_product:
                chosen_product_id = None
                if product_choices and reward.id in product_choices:
                    chosen_product_id = product_choices[reward.id]
                else:
                    # default to the first available reward product
                    chosen_product_id = reward.reward_product_ids[:1].id
                if not chosen_product_id:
                    raise UserError("Reward requires a product, but none is available/selected.")
                vals['selected_product_id'] = chosen_product_id

            # Real wizard used to apply
            real_wiz = wiz_env.create(vals)
            real_wiz.action_apply()  # this mutates the sale order
            # ✅ ensure recomputes hit DB before next reward
            env.flush_all()
            applied.append(reward.id)
            loops += 1

            # Re-browse the order to ensure fresh values for next loop
            sale_order.invalidate_recordset()
            sale_order = sale_order.browse(sale_order.id)

        if loops >= max_loops:
            raise UserError("Safety stop: too many reward iterations (possible loop).")

        return applied

    @http.route('/api/v1/create_sale_order_preview_button', type='json', auth='none', methods=['POST'], csrf=False)
    def create_sale_order_preview(self, **kwargs):
        response = {}
        sale_order_start_datetime = datetime.now()
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            partner_id = values.get('partner_id')
            customer_id = values.get('customer_id')
            po_number = values.get('po_number')
            order_creation_source = values.get('order_creation_source')
            sale_order_id = values.get('sale_order_id')
            product_lines = values.get('products', [])
            location_id = values.get('location_id', False)
            commitment_date = values.get('commitment_date', False)
            warehouse_id = values.get('warehouse_id', 0)

            _logger.info("------------------------------------------")
            _logger.info("thi is the location")
            _logger.info(location_id)
            _logger.info("thi is the location")
            _logger.info("------------------------------------------")
            ship_to_id = False
            if location_id:
                fsm_location = request.env['fsm.location'].sudo().browse(int(location_id))
                try:
                    if fsm_location:
                        ship_to_id = fsm_location.shipping_address_id.id
                except MissingError as e:
                    _logger.info("missing location")
                    _logger.info(e)
                except Exception as e:
                    _logger.info("missing location2")
                    _logger.info(e)

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            request.update_env(user=user.id)
            partner = request.env['res.partner'].sudo().browse(partner_id)
            customer = request.env['res.partner'].sudo().browse(customer_id)


            if not partner.exists() or not customer.exists():
                return {'success': False, 'error_msg': 'Invalid partner or customer ID.'}


            if sale_order_id and (not product_lines or len(product_lines) == 0):
                sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
                if sale_order.exists():
                    sale_order.unlink()
                    return {
                        'success': True,
                        'message': f'Sale order ID {sale_order_id} deleted successfully.'
                    }
                else:
                    return {'success': False, 'error_msg': f'Invalid sale_order_id: {sale_order_id}'}


            order_lines = []
            reward_required = False

            responsible = False
            if order_creation_source == "presales":
                responsible = user.partner_id.internal_user.id
            else:
                responsible = user.id

            for line in product_lines:
                product_id = line.get('product_id')
                quantity = line.get('quantity')
                price_unit = line.get('price_unit')
                uom_id = line.get('uom_id')
                # discount = line.get('discount', 0)
                packaging_id = line.get('product_packaging_id')
                product_packaging_qty = line.get('quantity')
                is_loyalty_product = line.get('is_loyalty_product', False)

                if not all([product_id, quantity, price_unit, uom_id]):
                    return {'success': False, 'error_msg': 'Missing product data'}

                product = request.env['product.product'].sudo().browse(int(product_id))
                _logger.info("this is the product %s and product type %s and this exist fun: %s" %(product, type(product), product.exists()))
                if not product.exists() or not product.active:
                    template = request.env['product.template'].sudo().browse(product_id)
                    product = template.product_variant_ids[:1] if template.exists() else False
                    if not product or not product.active:
                        return {'success': False, 'error_msg': f"Invalid product ID: {product_id}"}

                # if packaging_id:
                #     packaging = request.env['product.packaging'].sudo().browse(int(packaging_id))
                #     if packaging.exists():
                #         # quantity *= packaging.qty
                #         product_packaging_qty *= packaging.qty
                #         uom_id = packaging.product_uom_id.id

                if is_loyalty_product:
                    reward_required = True

                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': product_packaging_qty,
                    'price_unit': price_unit,
                    # 'discount': discount,
                    'product_uom': uom_id,
                    'product_packaging_id':packaging_id,
                    'product_packaging_qty':product_packaging_qty,
                    'name': product.name,
                }))

            if not order_lines:
                return {'success': False, 'error_msg': 'No valid order lines provided'}


            if not sale_order_id:
                sale_val = {
                    'partner_id': customer.id,
                    'date_order': fields.Datetime.now(),
                    'order_creation_source': order_creation_source,
                    # 'order_line': order_lines,
                    'company_id': user.company_id.id,
                    'active': False,
                    'user_id': responsible
                }

                if commitment_date:
                    sale_val['commitment_date'] = commitment_date
                else:
                    sale_val['commitment_date'] = fields.Datetime.now()
                if po_number:
                    sale_val["po_number"] = po_number
                if customer.property_product_pricelist:
                    sale_val['pricelist_id'] = customer.property_product_pricelist.id

                worker_jr_cash_obj = request.env['worker.journal'].sudo().search([
                    ('worker_ids', 'in', user.partner_id.id),
                    ('active', '=', True),
                    ('journal_type', '=', 'cash_van')
                ], limit=1)

                worker_jr_credit_obj = request.env['worker.journal'].sudo().search([
                    ('worker_ids', 'in', user.partner_id.id),
                    ('active', '=', True),
                    ('journal_type', '=', 'presale')
                ], limit=1)

                if customer.customer_type == "cash" or (
                        customer.customer_type == "credit" and customer.is_credit_hold == True):
                    worker_jr_obj = worker_jr_cash_obj
                else:
                    worker_jr_obj = worker_jr_credit_obj

                if worker_jr_obj and worker_jr_obj.journal_id:
                    sale_val["sale_journal"] = worker_jr_obj.journal_id.id

                # Create new sale order
                sale_order = request.env['sale.order'].with_user(user.id).sudo().create(sale_val)
                sale_order.write({'order_line': order_lines})
                if ship_to_id:
                    sale_order.write({"partner_shipping_id": ship_to_id})

                if warehouse_id and warehouse_id != 0:
                    sale_order.write({"warehouse_id": warehouse_id})

            else:
                sale_order = request.env['sale.order'].with_user(user.id).sudo().browse(sale_order_id)
                sale_val = {
                    'partner_id': customer.id,
                    'active': False,
                    'user_id': responsible
                }

                if commitment_date:
                    sale_val['commitment_date'] = commitment_date
                else:
                    sale_val['commitment_date'] = fields.Datetime.now()
                if po_number:
                    sale_val["po_number"] = po_number
                if customer.property_product_pricelist:
                    sale_val['pricelist_id'] = customer.property_product_pricelist.id

                worker_jr_cash_obj = request.env['worker.journal'].sudo().search([
                    ('worker_ids', 'in', user.partner_id.id),
                    ('active', '=', True),
                    ('journal_type', '=', 'cash_van')
                ], limit=1)

                worker_jr_credit_obj = request.env['worker.journal'].sudo().search([
                    ('worker_ids', 'in', user.partner_id.id),
                    ('active', '=', True),
                    ('journal_type', '=', 'presale')
                ], limit=1)

                if customer.customer_type == "cash" or (
                        customer.customer_type == "credit" and customer.is_credit_hold == True):
                    worker_jr_obj = worker_jr_cash_obj
                else:
                    worker_jr_obj = worker_jr_credit_obj

                if worker_jr_obj and worker_jr_obj.journal_id:
                    sale_val["sale_journal"] = worker_jr_obj.journal_id.id
                if ship_to_id:
                    sale_order.write({"partner_shipping_id": ship_to_id})
                    sale_order.partner_shipping_id = ship_to_id
                if po_number:
                    sale_order.po_number = po_number
                if not sale_order.exists():
                    return {'success': False, 'error_msg': f'Invalid sale_order_id: {sale_order_id}'}
                # 1) detach loyalty links before deleting lines (this is key)
                sale_order.order_line._reset_loyalty(complete=True)

                # 2) do a single atomic write using Odoo’s 12n commands:
                #    (5, 0, 0) clears existing lines (unlink), then we add your new lines
                cmds = [(5, 0, 0)] + order_lines
                vals = dict(sale_val, order_line=cmds)

                # 3) optional: quiet the chatter to reduce side effects (no functional change)
                ctx = dict(
                    mail_create_nolog=True,
                    tracking_disable=True,
                    mail_notrack=True,
                    mail_activity_automation=False,
                )

                sale_order.with_context(**ctx).write(vals)

            # --- NEW AUTOMATIC REWARD APPLICATION LOGIC ---
            err_message = ""
            applied_rewards = []


            if ship_to_id:
                sale_order.sudo().write({"partner_shipping_id": ship_to_id})
            if reward_required:
                try:

                    # Optional: let API choose products for specific rewards
                    # product_choices = { <reward_id>: <product_id>, ... }
                    # product_choices = None

                    applied_ids = self.apply_all_rewards_via_wizard(request.env, sale_order)
                    applied_rewards = applied_ids

                    if user.user_type == 'sales_user':
                        _logger.info("it's van")
                        # ⬇️ remove FOC lines if van has no usable stock (zero or expired)
                        self._cap_foc_to_available_stock(request.env, sale_order, user.partner_id)

                    # (Optional) If your flow also needs to run pricing recompute afterward:
                    # try:
                    #     sale_order._update_programs_and_rewards()
                    # except Exception as e:
                    #     _logger.info("Exception in reward1 %s" % e)
                    #     pass
                    # try:
                    #     sale_order.apply_promotions()
                    # except Exception as e:
                    #     _logger.info("Exception in reward2 %s" % e)

                    # # Step 1: Update programs and rewards
                    # sale_order._update_programs_and_rewards()
                    #
                    # # Step 2: Get all claimable rewards using the new logic
                    # claimable_rewards = sale_order._get_claimable_rewards()
                    #
                    # # Step 3: Apply all claimable rewards automatically
                    # for coupon, rewards in claimable_rewards.items():
                    #     for reward in rewards:
                    #         try:
                    #             # Check if this is a custom promotion type
                    #             if reward.program_id.program_type in (
                    #             'ladder_promotion', 'slab_promotion', 'flat_discount'):
                    #                 # Apply custom promotions using the new apply_promotions method
                    #                 sale_order.apply_promotions(reward.program_id)
                    #                 applied_rewards.append(
                    #                     f"{reward.program_id.name} ({reward.program_id.program_type})")
                    #             else:
                    #                 # Apply core Odoo rewards using the standard method
                    #                 sale_order._apply_program_reward(reward, coupon)
                    #                 applied_rewards.append(f"{reward.description} (core reward)")
                    #         except Exception as reward_error:
                    #             _logger.warning(f"Failed to apply reward {reward.id}: {str(reward_error)}")
                    #             if not err_message:
                    #                 err_message = f"Some rewards could not be applied: {str(reward_error)}"
                    #
                    # # Step 4: Final update to refresh totals and lines after all rewards applied
                    # try:
                    #     sale_order._update_programs_and_rewards()
                    # except:
                    #     pass
                    # sale_order.apply_promotions()

                except (ValidationError, UserError) as e:
                    err_message = str(e)
                    _logger.info("Error inside the promotion %s" % e)
                except Exception as e:
                    _logger.exception("Error in automatic reward processing")
                    err_message = f"Error processing rewards: {str(e)}"

            # try:
            #     sale_order.apply_promotions()
            # except Exception as e:
            #     _logger.info("Apply Promotion!")
            #     _logger.info(str(e))
            # and check the reward line

            # 1) read the lines (as you already do)
            lines_data = sale_order.order_line.read([
                'product_id', 'name', 'product_uom_qty', 'price_unit', 'price_subtotal',
                'product_uom', 'product_packaging_qty', 'product_packaging_id',
                'price_total', 'is_reward_line', 'discount', 'discount_unit_price',
                'original_total', 'tax_id','discount_amount',
            ])

            # 2) build caches (one query per model)
            product_ids = [d['product_id'][0] for d in lines_data if d.get('product_id')]
            prod_map = {
                p['id']: p
                for p in request.env['product.product'].browse(product_ids).read(['default_code', 'barcode'])
            }

            tax_ids = set(tid for d in lines_data for tid in (d.get('tax_id') or []))
            tax_map = {
                t['id']: t['name']
                for t in request.env['account.tax'].browse(list(tax_ids)).read(['name'])
            }

            cur = sale_order.currency_id
            amount_undiscounted = cur.round(sum(
                (d['price_subtotal'] + (d.get('discount_amount') or 0.0))
                for d in lines_data
                if not d['is_reward_line']  # exclude gift/discount lines
            ))

            # 3) massage minimal fields using the caches
            line_info = []
            for d in lines_data:
                pid = d['product_id'][0] if d['product_id'] else False
                code = prod_map.get(pid, {}).get('default_code')
                barcode = prod_map.get(pid, {}).get('barcode')
                tax_ids_line = d.get('tax_id') or []
                tax_names = [tax_map.get(t) for t in tax_ids_line]

                line_info.append({
                    'product_id': pid,
                    'product_name': d['name'],
                    'qty': d['product_uom_qty'],
                    'price_unit': d['price_unit'],
                    'price_subtotal': d['price_subtotal'],
                    'uom_id': d['product_uom'][0] if d['product_uom'] else False,
                    'uom_name': d['product_uom'][1] if d['product_uom'] else False,
                    'product_packaging_qty': d['product_packaging_qty'],
                    'product_packaging_id': d['product_packaging_id'][0] if d['product_packaging_id'] else False,
                    'product_packaging_name': d['product_packaging_id'][1] if d['product_packaging_id'] else False,
                    'tax_incel_total': d['price_total'],
                    'is_reward_line': d['is_reward_line'],
                    'discount': d['discount'],
                    'code': code,
                    'discount_amount': d['discount_amount'],
                    'barcode': barcode,
                    'discount_unit_price': d.get('discount_unit_price', 0.0),
                    'original_total': d.get('original_total', 0.0),
                    'tax_id': tax_ids_line,
                    'tax_name': ', '.join([n for n in tax_names if n]),
                })

            # line_info = [{
            #     'product_id': line.product_id.id,
            #     'product_name': line.name,
            #     'qty': line.product_uom_qty,
            #     'price_unit': 0.0 if (line.reward_id and line.reward_id.reward_type == 'product') else line.price_unit,
            #     'price_subtotal': line.price_subtotal,
            #     'uom_id': line.product_uom.id,
            #     'uom_name': line.product_uom.name,
            #     'code': line.product_id.default_code,
            #     'barcode': line.product_id.barcode,
            #     'tax_id': line.tax_id.id,
            #     'tax_name': line.tax_id.name,
            #     'product_packaging_qty': line.product_packaging_qty,
            #     'product_packaging_id': line.product_packaging_id.id,
            #     'product_packaging_name': line.product_packaging_id.name,
            #     'tax_incel_total': line.price_total,
            #     'is_reward_line': line.is_reward_line,
            #     'discount': line.discount,
            #     'discount_unit_price': line.discount_unit_price,
            #     'original_total': line.original_total,
            # } for line in sale_order.order_line]

            sale_order_end_datetime = datetime.now()

            delta = sale_order_end_datetime - sale_order_start_datetime
            # Convert timedelta to string (HH:MM:SS)
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            sale_order.api_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

            response = {
                'success': True,
                'message': 'Sale order created or updated with reward lines (if applicable).',
                "err_message": err_message,
                'sale_order': {
                    'id': sale_order.id,
                    'name': sale_order.name,
                    'amount_untaxed': sale_order.amount_untaxed,
                    'amount_tax': sale_order.amount_tax,
                    'amount_total': sale_order.amount_total,
                    'discount_amount_total': sale_order.discount_amount_total,
                    'amount_undiscounted': amount_undiscounted,
                    # 'amount_undiscounted': sale_order.amount_undiscounted, # total before discount
                    # 'amount_undiscounted': sale_order.tax_totals['before_discount_amount'], # total before discount
                    'lines': line_info,
                }
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/create_sale_order_preview_button")
            response = {'success': False, 'error_msg': str(e)}

        return response

    @http.route('/api/v1/create_invoice_for_sale_order', type='json', auth='none', methods=['POST'])
    def create_invoice_for_sale_order(self, **kwargs):
        values = request.httprequest.json
        response = {}

        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = int(values.get('sale_order_id', 0))

            if not (user_id and auth_token and sale_order_id):
                return {'success': False, 'error_msg': 'Missing required parameters.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
            if not sale_order.exists():
                return {'success': False, 'error_msg': 'Invalid Sale Order ID.'}

            if sale_order.state != 'sale':
                return {'success': False,
                        'error_msg': 'Invoice can only be generated when Sale Order is confirmed (state = sale).'}

            deliveries = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
            if not deliveries:
                return {'success': False, 'error_msg': 'No outgoing delivery orders found for this Sale Order.'}

            if not all(picking.state == 'done' for picking in deliveries):
                return {'success': False,
                        'error_msg': 'All delivery orders must be completed (state = done) before invoicing.'}

            for line in sale_order.order_line:
                _logger.info(
                    f"Product: {line.product_id.display_name}, Delivered Qty: {line.qty_delivered}, To Invoice: {line.qty_to_invoice}")

            invoices = sale_order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel')
            # access_token_inv_already = invoices._portal_ensure_token()
            # pdf_download_inv_already_url = f"{invoices.get_base_url()}/my/invoices/{invoices.id}?access_token={access_token_inv_already}&report_type=pdf&download=true"

            tax_invoice_4inch_pdf_url = None
            if sale_order:
                access_token = sale_order._ensure_portal_token()
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

                # Report access using URL default pdf report
                tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{sale_order.id}?access_token={access_token}&report_type=pdf&download=true"

            if invoices:
                return {
                    'success': True,
                    'message': 'Invoice already exists for this Sale Order.',
                    'invoice': {
                        'id': invoices[0].id,
                        'name': invoices[0].name,
                        'amount_total': invoices[0].amount_total,
                        'currency': invoices[0].currency_id.name,
                        'state': invoices[0].state,
                        'partner': invoices[0].partner_id.name,
                        'date': str(invoices[0].invoice_date),
                        'url': f"/web#id={invoices[0].id}&model=account.move&view_type=form",
                        # 'pdf_download_inv_already_url': pdf_download_inv_already_url,
                        'pdf_download_inv_already_url': tax_invoice_4inch_pdf_url,
                    }
                }
            invoice = sale_order.with_user(user.id).sudo()._create_invoices()
            if not invoice:
                return {'success': False, 'error_msg': 'Invoice was not created.'}
            invoice = invoice.sudo()
            # analytic_account = request.env['account.analytic.account'].sudo().search([('name', '=', 'VAN Sales')],
            #                                                                          limit=1)
            # if not analytic_account:
            #     return {'success': False, 'error_msg': 'Analytic account "VAN Sales" not found.'}
            # for line in invoice.invoice_line_ids:
            #     line.sudo().write({
            #         'analytic_distribution': {
            #             str(analytic_account.id): 100.0
            #         }
            #     })

            invoice.with_user(user.id).sudo().action_post()
            access_token = invoice._portal_ensure_token()
            pdf_download_url = f"{invoice.get_base_url()}/my/invoices/{invoice.id}?access_token={access_token}&report_type=pdf&download=true"
            response.update({
                'success': True,
                'message': 'Invoice created successfully.',
                'invoice': {
                    'id': invoice.id,
                    'name': invoice.name,
                    'amount_total': invoice.amount_total,
                    'currency': invoice.currency_id.name,
                    'state': invoice.state,
                    'partner': invoice.partner_id.name,
                    'date': str(invoice.invoice_date),
                    'url': f"/web#id={invoice.id}&model=account.move&view_type=form",
                    # 'pdf_download_url': pdf_download_url,
                    'pdf_download_url': tax_invoice_4inch_pdf_url,
                }
            })

        except Exception as e:
            _logger.exception("Error in /create_invoice_for_sale_order")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    def get_quarter_date_range(self, quarter, year):
        return {
            1: (date(year, 1, 1), date(year, 3, 31)),
            2: (date(year, 4, 1), date(year, 6, 30)),
            3: (date(year, 7, 1), date(year, 9, 30)),
            4: (date(year, 10, 1), date(year, 12, 31)),
        }[quarter]

    def get_weeks_of_month(self, year, month):
        first_day = date(year, month, 1)
        num_days = calendar.monthrange(year, month)[1]
        last_day = date(year, month, num_days)
        weeks = []
        start = first_day
        while start <= last_day:
            end = start + timedelta(days=6)
            if end > last_day:
                end = last_day
            weeks.append((start, end))
            start = end + timedelta(days=1)
        return weeks

    @http.route('/api/v1/filter_invoices_by_period', type='json', auth='none', methods=['POST'])
    def filter_invoices_by_period(self, **kwargs):
        try:
            values = request.httprequest.json
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            filter_type = values.get('filter_type')

            if not (user_id and auth_token and filter_type):
                return {'success': False, 'error_msg': 'Missing required parameters.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            today = fields.Date.today()
            current_year = today.year
            current_month = today.month
            data = []

            if filter_type == 'Day':
                weekday = today.weekday()
                days_since_saturday = (weekday + 2) % 7
                start_date = today - timedelta(days=days_since_saturday)
                end_date = start_date + timedelta(days=6)

                for i in range(7):
                    current_day = start_date + timedelta(days=i)
                    domain = [
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted'),
                        ('assign_to', '=', user.partner_id.id),
                        ('invoice_date', '=', current_day)
                    ]
                    invoices = request.env['account.move'].sudo().search(domain)
                    data.append({
                        'label': str(current_day),
                        'count': len(invoices),
                        'total': sum(inv.amount_total for inv in invoices)
                    })

            elif filter_type == 'Week':
                weeks = self.get_weeks_of_month(current_year, current_month)
                for idx, (start, end) in enumerate(weeks, start=1):
                    domain = [
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted'),
                        ('assign_to', '=', user.partner_id.id),
                        ('invoice_date', '>=', start),
                        ('invoice_date', '<=', end)
                    ]
                    invoices = request.env['account.move'].sudo().search(domain)
                    data.append({
                        'label': f"Week {idx}",
                        'count': len(invoices),
                        'total': sum(inv.amount_total for inv in invoices)
                    })

            # elif filter_type == 'Month':
            #     start_date = date(today.year, 1, 1)
            #     end_date = date(today.year, 12, 31)

            elif filter_type == 'Quarter':
                for q in range(1, 5):
                    start, end = self.get_quarter_date_range(q, current_year)
                    domain = [
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted'),
                        ('assign_to', '=', user.partner_id.id),
                        ('invoice_date', '>=', start),
                        ('invoice_date', '<=', end)
                    ]
                    invoices = request.env['account.move'].sudo().search(domain)
                    data.append({
                        'label': f"Q{q}",
                        'count': len(invoices),
                        'total': sum(inv.amount_total for inv in invoices)
                    })


            elif filter_type == 'Year':
                for m in range(1, 13):
                    start = date(current_year, m, 1)
                    end = date(current_year, m, calendar.monthrange(current_year, m)[1])
                    domain = [
                        ('move_type', '=', 'out_invoice'),
                        ('state', '=', 'posted'),
                        ('assign_to', '=', user.partner_id.id),
                        ('invoice_date', '>=', start),
                        ('invoice_date', '<=', end)
                    ]
                    invoices = request.env['account.move'].sudo().search(domain)
                    data.append({
                        'label': calendar.month_abbr[m],
                        'count': len(invoices),
                        'total': sum(inv.amount_total for inv in invoices)
                    })

            else:
                return {'success': False, 'error_msg': 'Invalid filter_type. Use Day, Week, Month, or Quarter.'}
            # invoices = request.env['account.move'].with_user(user.id).sudo().search([
            #     ('move_type', '=', 'out_invoice'),
            #     ('state', '=', 'posted'),
            #     ('assign_to', '=', user.partner_id.id),
            #     ('invoice_date', '>=', start_date),
            #     ('invoice_date', '<=', end_date)
            # ], order='invoice_date desc')

            return {
                'success': True,
                'filter_type': filter_type,
                'year': current_year,
                'data': data
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/filter_invoices_by_period")
            return {'success': False, 'error_msg': f"Error occurred: {str(e)}"}

    # @http.route('/api/v1/rma_list_invoices', type='json', auth='none', methods=['POST'])
    # def rma_list_invoices(self, **kwargs):
    #     values = request.httprequest.json
    #     response = {}
    #
    #     try:
    #         user_id = int(values.get('user_id', 0))
    #         auth_token = values.get('auth_token')
    #         worker_id = values.get('worker_id', 0)
    #
    #
    #         user = request.env['res.users'].sudo().browse(user_id)
    #         if not user.exists() or not auth_token:
    #             return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}
    #         customer_id = values.get('customer_id')
    #         customer = request.env['res.partner'].sudo().browse(customer_id)
    #         if not customer.exists():
    #             return {'success': False, 'error_msg': 'Invalid customer ID.'}
    #         token = request.env['mobile.auth.token'].sudo().search([
    #             ('user_id', '=', user_id),
    #             ('mobile_app_auth_token', '=', auth_token)
    #         ], limit=1)
    #
    #         if not token:
    #             return {'success': False, 'error_msg': 'Invalid or expired auth token.'}
    #
    #         van_sale_user = user.has_group('plnx_sales_team.group_sales_team_van_sale')
    #
    #         invoices = request.env['account.move'].sudo().search([
    #             ('move_type', '=', 'out_invoice'),
    #             ('partner_id', '=', customer.id),
    #             ('state', '=', 'posted')
    #         ], order='invoice_date desc')
    #
    #         invoice_data = []
    #         for invoice in invoices:
    #             deliveries = []
    #             seen_picking_ids = set()
    #
    #             for line in invoice.invoice_line_ids:
    #                 for sale_line in line.sale_line_ids:
    #                     sale_order = sale_line.order_id
    #                     for picking in sale_order.picking_ids:
    #                         if picking.id in seen_picking_ids or picking.picking_type_id.code != 'outgoing':
    #                             continue
    #                         seen_picking_ids.add(picking.id)
    #                         product_lines = []
    #                         for move in picking.move_ids_without_package:
    #                             product_lines.append({
    #                                 'product_id': move.product_id.id,
    #                                 'product_name': move.product_id.name,
    #                                 'barcode': move.product_id.barcode,
    #                                 'product_code': move.product_id.default_code,
    #                                 'quantity': move.product_uom_qty,
    #                                 'uom': move.product_uom.name,
    #                                 'image': self._get_image_url_dynamic(
    #                                     model=move.product_id._name,
    #                                     record_id=move.product_id.id,
    #                                     field_name='image_1920'
    #                                 ),
    #                             })
    #
    #                         deliveries.append({
    #                             'id': picking.id,
    #                             'name': picking.name,
    #                             'state': picking.state,
    #                             'is_out_type': True,
    #                             'sale_id': picking.sale_id.id or (
    #                                 picking.move_ids_without_package.filtered(lambda m: m.sale_line_id).mapped(
    #                                     'sale_line_id.order_id.id')[0] if picking.move_ids_without_package.filtered(
    #                                     lambda m: m.sale_line_id) else None),
    #                             'is_return': bool(picking.move_ids.filtered(lambda m: m.returned_move_ids)),
    #                             'fsm_name': picking.fsm_order_id.name if picking.fsm_order_id else '',
    #                             'fsm_id': picking.fsm_order_id.id if picking.fsm_order_id else '',
    #                             'product_lines': product_lines
    #                         })
    #
    #             invoice_data.append({
    #                 'id': invoice.id,
    #                 'name': invoice.name,
    #                 'date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
    #                 'amount_total': invoice.amount_total,
    #                 'currency': invoice.currency_id.name,
    #                 'state': invoice.state,
    #                 'partner_id': invoice.partner_id.id,
    #                 'partner_name': invoice.partner_id.name,
    #                 'deliveries': deliveries
    #             })
    #
    #         if worker_id and worker_id != 0:
    #             partner = request.env['res.partner'].browse(worker_id)
    #         else:
    #             partner = user.partner_id
    #
    #         # get sales team
    #         crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [partner.id])],
    #                                                          limit=1)
    #         _logger.info(crm_team)
    #         rma_return_casued_by = []
    #         rma_return_reason = []
    #         if crm_team:
    #             fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
    #             rma_return_caused_byObj = request.env['rma.return.caused.by'].sudo().search([('sales_teams','=', crm_team.id)])
    #             rma_return_casued_by = rma_return_caused_byObj.mapped('return_caused_by_ids')
    #             rma_return_reason = rma_return_caused_byObj.mapped('return_reason_ids')
    #         if len(rma_return_reason) <= 0:
    #             rma_return_reason = request.env['rma.return.reason'].sudo().search([])
    #         # clean format (id, name only)
    #         rma_return_reason_list = [{'id': r.id, 'name': r.name} for r in rma_return_reason]
    #         rma_return_caused_by_list = [{'id': c.id, 'name': c.name} for c in rma_return_casued_by]
    #
    #
    #         return_reason_data = request.env['rma.operation'].sudo().search_read([], ['id', 'name'])
    #
    #         response = {
    #             'success': True,
    #             'count': len(invoice_data),
    #             'van_sale_user': van_sale_user,
    #             'invoices': invoice_data,
    #             'return_reasons': return_reason_data,
    #             'return_reason_lines': rma_return_reason_list,
    #             'return_caused_by': rma_return_caused_by_list
    #         }
    #
    #     except Exception as e:
    #         _logger.exception("Error in /api/v1/rma_list_invoices")
    #         response = {'success': False, 'error_msg': str(e)}
    #
    #     return response

    @http.route('/api/v1/rma_list_invoices', type='json', auth='none', methods=['POST'])
    def rma_list_invoices(self, **kwargs):
        values = request.httprequest.json
        response = {}

        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            worker_id = values.get('worker_id', 0)

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            customer_id = values.get('customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)
            if not customer.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            van_sale_user = user.has_group('plnx_sales_team.group_sales_team_van_sale')

            invoices = request.env['account.move'].sudo().search([
                ('move_type', '=', 'out_invoice'),
                ('partner_id', '=', customer.id),
                ('state', '=', 'posted')
            ], order='invoice_date desc')

            invoice_data = []
            for invoice in invoices:
                deliveries = []
                seen_picking_ids = set()

                # Map invoice lines → Sale Orders
                inv_lines_by_so = {}
                for il in invoice.invoice_line_ids:
                    # skip section/note lines or lines without product
                    if not il.product_id:
                        continue
                    so_ids = set()
                    for so_line in il.sale_line_ids:
                        if so_line.order_id:
                            so_ids.add(so_line.order_id.id)
                    # If an invoice line has no sale_line_ids, we’ll attach it to the first picking encountered later
                    if not so_ids:
                        so_ids = set([0])  # placeholder bucket for "unassigned to SO"
                    for so_id in so_ids:
                        inv_lines_by_so.setdefault(so_id, []).append(il)

                # Track which invoice lines we’ve already attached per SO (to avoid duplication across pickings)
                used_line_ids_per_so = {so_id: set() for so_id in inv_lines_by_so.keys()}

                # Build deliveries by iterating relevant pickings (as before)
                # Derive candidate SOs from invoice lines; then walk their pickings
                related_so_ids = [so_id for so_id in inv_lines_by_so.keys() if so_id]
                related_sos = request.env['sale.order'].sudo().browse(related_so_ids)

                # We also keep "unassigned" invoice lines (so_id == 0) to drop into the first picking we see
                unassigned_lines = inv_lines_by_so.get(0, [])

                # Iterate each related SO’s outgoing pickings (same as your original structure)
                for so in related_sos:
                    for picking in so.picking_ids:
                        if picking.id in seen_picking_ids or picking.picking_type_id.code != 'outgoing':
                            continue
                        seen_picking_ids.add(picking.id)

                        # Select invoice lines tied to THIS SO, and not yet used
                        product_lines = []
                        bucket = inv_lines_by_so.get(so.id, [])
                        used_ids = used_line_ids_per_so.get(so.id, set())

                        def _line_to_payload(il):
                            # Safe UoM name from invoice line or product
                            uom_name = ''
                            uom_field = getattr(il, 'product_uom_id', False)
                            if uom_field:
                                uom_name = uom_field.name or ''
                            elif il.product_id and il.product_id.uom_id:
                                uom_name = il.product_id.uom_id.name or ''
                            return {
                                'product_id': il.product_id.id,
                                'product_name': il.product_id.name,
                                'barcode': il.product_id.barcode,
                                'product_code': il.product_id.default_code,
                                'quantity': il.quantity,  # from INVOICE line
                                'uom': uom_name,
                                'image': self._get_image_url_dynamic(
                                    model=il.product_id._name,
                                    record_id=il.product_id.id,
                                    field_name='image_1920'
                                ),
                            }

                        # Add SO-specific lines first (no duplicates)
                        for il in bucket:
                            if il.id in used_ids:
                                continue
                            product_lines.append(_line_to_payload(il))
                            used_ids.add(il.id)
                        used_line_ids_per_so[so.id] = used_ids

                        # If still empty and we have unassigned invoice lines, attach them to this first picking we see
                        if not product_lines and unassigned_lines:
                            for il in unassigned_lines:
                                product_lines.append(_line_to_payload(il))
                            # clear so they are not repeated on other pickings
                            unassigned_lines = []

                        deliveries.append({
                            'id': picking.id,
                            'name': picking.name,
                            'state': picking.state,
                            'is_out_type': True,
                            'sale_id': picking.sale_id.id or (
                                picking.move_ids_without_package.filtered(lambda m: m.sale_line_id).mapped(
                                    'sale_line_id.order_id.id')[0] if picking.move_ids_without_package.filtered(
                                    lambda m: m.sale_line_id) else None),
                            'is_return': bool(picking.move_ids.filtered(lambda m: m.returned_move_ids)),
                            'fsm_name': picking.fsm_order_id.name if picking.fsm_order_id else '',
                            'fsm_id': picking.fsm_order_id.id if picking.fsm_order_id else '',
                            'product_lines': product_lines
                        })

                # If there were no related SOs/pickings at all, but the invoice has lines,
                # return a single synthetic "delivery" record holding all invoice lines (keeps schema stable).
                if not deliveries:
                    product_lines = []
                    for il in invoice.invoice_line_ids.filtered(lambda l: l.product_id):
                        uom_name = ''
                        uom_field = getattr(il, 'product_uom_id', False)
                        if uom_field:
                            uom_name = uom_field.name or ''
                        elif il.product_id and il.product_id.uom_id:
                            uom_name = il.product_id.uom_id.name or ''
                        product_lines.append({
                            'product_id': il.product_id.id,
                            'product_name': il.product_id.name,
                            'barcode': il.product_id.barcode,
                            'product_code': il.product_id.default_code,
                            'quantity': il.quantity,
                            'uom': uom_name,
                            'image': self._get_image_url_dynamic(
                                model=il.product_id._name,
                                record_id=il.product_id.id,
                                field_name='image_1920'
                            ),
                        })
                    deliveries.append({
                        'id': 0,
                        'name': 'Invoice Lines',
                        'state': invoice.state,
                        'is_out_type': True,
                        'sale_id': None,
                        'is_return': False,
                        'fsm_name': '',
                        'fsm_id': '',
                        'product_lines': product_lines
                    })

                invoice_data.append({
                    'id': invoice.id,
                    'name': invoice.name,
                    'date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                    'amount_total': invoice.amount_total,
                    'currency': invoice.currency_id.name,
                    'state': invoice.state,
                    'partner_id': invoice.partner_id.id,
                    'partner_name': invoice.partner_id.name,
                    'deliveries': deliveries
                })

            # worker/partner & team bits unchanged
            if worker_id and worker_id != 0:
                partner = request.env['res.partner'].browse(worker_id)
            else:
                partner = user.partner_id

            crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [partner.id])], limit=1)
            rma_return_casued_by = []
            rma_return_reason = []
            if crm_team:
                fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
                rma_return_caused_byObj = request.env['rma.return.caused.by'].sudo().search(
                    [('sales_teams', '=', crm_team.id)])
                rma_return_casued_by = rma_return_caused_byObj.mapped('return_caused_by_ids')
                rma_return_reason = rma_return_caused_byObj.mapped('return_reason_ids')
            if len(rma_return_reason) <= 0:
                rma_return_reason = request.env['rma.return.reason'].sudo().search([])

            rma_return_reason_list = [{'id': r.id, 'name': r.name} for r in rma_return_reason]
            rma_return_caused_by_list = [{'id': c.id, 'name': c.name} for c in rma_return_casued_by]
            return_reason_data = request.env['rma.operation'].sudo().search_read([], ['id', 'name'])

            response = {
                'success': True,
                'count': len(invoice_data),
                'van_sale_user': van_sale_user,
                'invoices': invoice_data,
                # 'return_reasons': return_reason_data,
                'return_reasons': rma_return_caused_by_list,
                'return_reason_lines': rma_return_reason_list,
                'return_caused_by': rma_return_caused_by_list
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/rma_list_invoices")
            response = {'success': False, 'error_msg': str(e)}

        return response

    @http.route('/api/v1/rma_confirm', type='json', auth='public', methods=['POST'], csrf=False)
    def rma_confirm(self, **kwargs):
        values = request.httprequest.json or {}
        try:
            # ---------------- Inputs & Auth ----------------
            user_id = int(values.get('user_id', 0) or 0)
            auth_token = values.get('auth_token')
            invoice_id = int(values.get('invoice_id', 0) or 0)
            products = values.get('products', []) or []
            partner_id = int(values.get('customer_id', 0) or 0)
            rma_type = values.get('rma_type')
            return_caused_by = int(values.get('return_caused_by', 0) or 0)
            return_reason = int(values.get('return_reason', 0) or 0)
            delivery_id = int(values.get('delivery_id', 0) or 0)
            fsm_order_id = values.get('fsm_order_id')
            fsm_order = request.env['fsm.order'].sudo().browse(int(fsm_order_id or 0))

            worker_id = int(values.get('worker_id', 0) or 0)

            customer = request.env['res.partner'].sudo().browse(partner_id)

            if worker_id:
                responsible_worker_id = request.env['res.partner'].sudo().browse(worker_id)
                user = responsible_worker_id.internal_user
            else:
                user = request.env['res.users'].sudo().browse(user_id)
                responsible_worker_id = user.partner_id

            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists():
                return {'success': False, 'error_msg': 'Invoice not found.'}

            delivery = request.env['stock.picking'].sudo().browse(delivery_id)
            if not delivery.exists():
                return {'success': False, 'error_msg': 'Delivery not found.'}

            # ---------------- Create RMA Shell ----------------
            rma_model = request.env['rma'].sudo()
            origin = ''
            if fsm_order:
                partner_name = fsm_order.person_id_partner.name or ''
                fsm_name = fsm_order.name or ''
                origin = f"{partner_name} {fsm_name}".strip()

            rma_operation = request.env['rma.operation'].sudo().search([
                ('active', '=', True), ('operation_type', '=', 'refund')
            ], limit=1)

            rma_vals = {
                'partner_id': partner_id,
                'rma_type': "base_on_invoice",
                'user_id': user.id,
                'invoice_id': invoice_id,
                'state': 'draft',
                'company_id': user.sudo().with_user(SUPERUSER_ID).company_id.id,
                'visit_id': fsm_order.id if fsm_order else False,
                'origin': origin,
                'grv_no': invoice.name,
                'responsible_worker_id': responsible_worker_id.id,
                'sales_person_id': responsible_worker_id.id,
            }
            if rma_operation:
                rma_vals['operation_id'] = rma_operation.id

            # Try to pick a van/internal location for this user
            if not worker_id:
                van_locations = request.env['stock.location'].sudo().search([
                    ('responsible_id', '=', user.id),
                    ('usage', '=', 'internal')
                ], limit=1)
                if not van_locations:
                    van_locations = user.partner_id.van_location
                if van_locations:
                    rma_vals['location_id'] = van_locations.id

            # Sales team on RMA
            if partner_id:
                crm_team = request.env['crm.team'].sudo().search(
                    [('partner_member_ids', 'in', [partner_id])], limit=1
                )
                if crm_team:
                    rma_vals['crm_team_id'] = crm_team.id

            rma_vals['collection_request_date'] = fields.Date.today()

            # Create the RMA
            rma = rma_model.with_user(SUPERUSER_ID).create(rma_vals)

            # Initial GRV (likely 0 now; will recompute later)
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # ---------------- Lines: FIX for duplicate products ----------------
            # Keep ALL existing behavior. We only change how we choose which line to update:
            # build a queue per product and consume ONE line per payload row.
            existing_lines_pool = defaultdict(list)
            for l in rma.line_ids.sorted(key=lambda r: r.id):
                existing_lines_pool[l.product_id.id].append(l)

            updated_line_ids = []

            def _safe_int(x):
                try: return int(x or 0)
                except Exception: return 0

            def _safe_float(x):
                try: return float(x or 0)
                except Exception: return 0.0

            def _pop_matching_line(product_id, product_packaging_id, return_reason_id, return_reason_type_id, return_caused_by_id):
                """Pop ONE unused existing line for this product. Prefer an exact match if optional fields provided."""
                bucket = existing_lines_pool.get(product_id) or []

                def _is_exact(line):
                    if product_packaging_id and (line.product_packaging_id.id or 0) != product_packaging_id:
                        return False
                    if return_reason_id and (line.return_reason_id.id or 0) != return_reason_id:
                        return False
                    if return_reason_type_id and (line.return_reason_type_id.id or 0) != return_reason_type_id:
                        return False
                    if return_caused_by_id and (line.return_caused_by_id.id or 0) != return_caused_by_id:
                        return False
                    return True

                # exact match first
                for i, line in enumerate(bucket):
                    if _is_exact(line):
                        bucket.pop(i)
                        if not bucket:
                            existing_lines_pool.pop(product_id, None)
                        return line

                # fallback: any remaining line for this product
                if bucket:
                    line = bucket.pop(0)
                    if not bucket:
                        existing_lines_pool.pop(product_id, None)
                    return line
                return None

            for prod in products:
                product_id = _safe_int(prod.get('product_id'))
                returned_qty = _safe_float(prod.get('returned_qty'))
                product_packaging_qty = _safe_float(prod.get('product_packaging_qty'))
                product_packaging_id = _safe_int(prod.get('product_packaging_id'))

                return_caused_by_id = _safe_int(prod.get('return_cause_by'))
                return_reason_id = _safe_int(prod.get('return_reason'))
                return_reason_type_id = _safe_int(prod.get('return_reason_type_id'))

                production_date = prod.get('production_date')  # kept for future use
                expiry_date = prod.get('expiry_date')
                lot = prod.get('lot') or 0
                if not lot and production_date and expiry_date:
                    lot = f"{production_date} - {expiry_date}"

                # consume ONE existing line per payload row (no new creation; preserve prices/taxes)
                existing_line = _pop_matching_line(
                    product_id, product_packaging_id, return_reason_id, return_reason_type_id, return_caused_by_id
                )

                if existing_line:
                    existing_line.sudo().with_user(SUPERUSER_ID).write({
                        'product_uom_qty': returned_qty,
                        'product_packaging_qty': product_packaging_qty,
                        'product_packaging_id': product_packaging_id or False,
                        'return_reason_id': return_reason_id or False,
                        'return_reason_type_id': return_reason_type_id or False,
                        'return_caused_by_id': return_caused_by_id or False,
                        # DO NOT touch price_unit/taxes/exercise fields (preserve original)
                        'exercise_price': existing_line.exercise_price,
                        # 'lot_number': lot if rma_type == 'base_on_product' and lot else False,
                        # 'production_date': production_date,
                        # 'expiry_date': expiry_date,
                    })
                    updated_line_ids.append(existing_line.id)
                else:
                    _logger.warning(f"No unused RMA line left to match product {product_id} on RMA {rma.id}")

            # Build helper sets
            other_lines = rma.line_ids.filtered(lambda l: l.id not in updated_line_ids)
            to_update_lines = rma.line_ids.filtered(lambda l: l.id in updated_line_ids)

            # Mirror selected fields into rma.invoice.line (keep your behavior)
            for one in to_update_lines:
                request.env['rma.invoice.line'].sudo().create({
                    'product_uom_qty': one.product_uom_qty,
                    'product_packaging_qty': one.product_packaging_qty,
                    # 'product_packaging_id': one.product_packaging_id.id,
                    'return_reason_id': one.return_reason_id.id,
                    'return_reason_type_id': one.return_reason_type_id.id,
                    'return_caused_by_id': one.return_caused_by_id.id,
                    'product_id': one.product_id.id,
                    'price_unit': one.price_unit,
                    'product_uom_id': one.product_uom_id.id,
                    'rma_id': one.rma_id.id,
                    'move_id': one.move_id.id if one.move_id else False,
                    'move_line_id': one.move_line_id.id if one.move_line_id else False,
                    'system_unit_price': one.system_unit_price,
                    'tax_id': [(4, one.tax_id.id)] if one.tax_id else False,
                    'discount': one.discount,
                    'exercise_price': one.exercise_price,
                    'analytic_distribution': one.analytic_distribution,
                })

            # Recompute (before unlink)
            rma.sudo().compute_line_ids()

            # Delete lines not provided by API in this call (preserve your cleanup)
            try:
                if other_lines:
                    other_lines.with_user(SUPERUSER_ID).unlink()
            except Exception as e:
                _logger.info("Failed to unlink other_lines: %s", str(e))

            # Recompute and GRV again
            rma.sudo().compute_line_ids()
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # ---------------- Auto confirm / picking / refund ----------------
            conf_grv_amount = float(request.env['ir.config_parameter'].sudo().get_param(
                'plnx_rma_extended.grv_amount'
            ) or 50)
            tax_credit_4inch_pdf_url = False

            if rma.grv_amount <= conf_grv_amount and getattr(user, 'user_type', False) == 'sales_user':
                rma.with_user(SUPERUSER_ID).action_confirm()

                if rma.reception_move_id and rma.reception_move_id.picking_id:
                    rma.reception_move_id.picking_id.quality_check_todo = True

                    rma_pick = rma.reception_move_id.picking_id.with_user(user).sudo()
                    if rma_pick.state in ['draft', 'loaded_dispatched']:
                        rma_pick.with_user(user).sudo().action_confirm()

                    if not rma_pick.picker_partner_id:
                        rma_pick.picker_partner_id = user.partner_id.id
                    if not rma_pick.picking_driver_id:
                        rma_pick.picking_driver_id = user.partner_id.id

                    if rma_pick.state != 'done':
                        rma_pick.with_user(user).sudo().action_assign()

                        for move in rma_pick.move_ids_without_package:
                            move.picker_partner_id = rma_pick.picker_partner_id

                        rma_pick.with_user(user).sudo().action_assign()
                        if not rma_pick.has_packages:
                            try:
                                rma_pick.with_user(user).sudo().action_put_in_pack()
                                rma_pick.has_packages = True
                            except Exception as e:
                                _logger.info("action_put_in_pack failed: %s", str(e))
                                try:
                                    rma_pick.with_user(user).sudo().action_assign_driver()
                                    rma_pick.with_user(user).sudo().action_collect()
                                    rma_pick.with_user(user).sudo().action_item_offload()
                                except Exception as e2:
                                    _logger.info("fallback driver/collect/offload failed: %s", str(e2))

                    # Try button_validate and auto-fill lots if missing
                    try:
                        rma_pick.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()
                    except Exception as e:
                        error_message = str(e)
                        if 'supply a Lot/Serial number' in error_message:
                            _logger.info("Auto-injecting missing lots from original picking...")
                            original_picking = rma.picking_id
                            for move in rma_pick.move_ids_without_package:
                                orig_lines = original_picking.move_line_ids.filtered(
                                    lambda ml: ml.product_id == move.product_id and ml.lot_id
                                )
                                if not move.move_line_ids:
                                    for orig in orig_lines:
                                        request.env['stock.move.line'].sudo().create({
                                            'picking_id': rma_pick.id,
                                            'move_id': move.id,
                                            'product_id': move.product_id.id,
                                            'product_uom_id': move.product_uom.id,
                                            'qty_done': orig.qty_done,
                                            'location_id': move.location_id.id,
                                            'location_dest_id': move.location_dest_id.id,
                                            'lot_id': orig.lot_id.id,
                                        })
                                else:
                                    for ml in move.move_line_ids:
                                        if not ml.qty_done:
                                            ml.qty_done = move.product_uom_qty
                                        if not ml.lot_id and orig_lines:
                                            ml.lot_id = orig_lines[0].lot_id.id
                            rma_pick.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()

                # Quality checks loop
                picking = rma.reception_move_id.picking_id.with_user(user).sudo() if rma.reception_move_id and rma.reception_move_id.picking_id else False
                if picking and picking.state != 'done':
                    try:
                        while True:
                            action = picking.check_quality()
                            if not isinstance(action, dict) or action.get('res_model') != 'quality.check.wizard':
                                break
                            ctx = action.get('context', {}) or {}
                            check_ids = ctx.get('default_check_ids', [])
                            current_id = ctx.get('default_current_check_id')
                            to_pass = [current_id] if current_id else check_ids
                            for check_id in to_pass:
                                qc = request.env['quality.check'].with_user(user).sudo().browse(check_id)
                                if qc:
                                    qc.do_pass()
                        picking.quality_check_todo = True
                    except Exception as e:
                        _logger.info("Quality check flow error: %s", str(e))

                    # Final validate
                    try:
                        picking.button_validate()
                    except Exception as e:
                        _logger.info("picking.button_validate failed: %s", str(e))

                # Refund handling
                if rma.refund_id:
                    if rma.refund_id.state == 'draft':
                        rma.refund_id.with_user(user.id).action_post()

                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    access_token = rma.refund_id._ensure_portal_token()
                    tax_credit_4inch_pdf_url = f"{base_url}/my/tax_credit_4inch_pdf/{rma.refund_id.id}?access_token={access_token}&report_type=pdf&download=true"

                    # pick a cash journal from custodian or fallback
                    journal = False
                    custodian_id = request.env['custodian'].sudo().search(
                        [("responsible_custodian", "=", user.partner_id.id)], limit=1)
                    for one in custodian_id.journal_ids:
                        if one.type == "cash":
                            journal = one
                    if not journal:
                        journal = request.env['account.journal'].sudo().search([('type', '=', 'cash')], limit=1)

                    # collect payment if non-credit or on hold
                    if customer.customer_type != 'credit':
                    # if customer.customer_type != 'credit' or (customer.customer_type == 'credit' and customer.is_credit_hold):
                        company_id = rma.refund_id.company_id.id
                        ctx = {
                            'active_model': 'account.move',
                            'active_ids': [rma.refund_id.id],
                            'active_id': rma.refund_id.id,
                            'company_id': company_id,
                            'allowed_company_ids': [company_id],
                        }
                        account_payment_ids = request.env['account.payment'].sudo().search([('invoice_ids','in', [rma.refund_id.id])])
                        _logger.info('1##############################################################')
                        _logger.info(account_payment_ids)
                        _logger.info('1##############################################################')
                        if not account_payment_ids:
                            account_payment_register = request.env['account.payment.register'].sudo().with_context(**ctx).create({
                                'journal_id': journal.id,
                                'responsible_id': user.partner_id.id,
                                'group_payment': True,
                                'custodian_id': custodian_id.id,
                            })
                            account_payment_register.action_create_payments()

                            if rma.refund_id.matched_payment_ids:
                                for payment in rma.refund_id.matched_payment_ids:
                                    payment.collector_name = user.partner_id.name
                                    if payment.state == 'draft':
                                        payment.action_post()
                                    elif payment.state == 'in_process' or not payment.state != "paid":
                                        payment.action_validate()
                else:
                    # If no existing refund, create one
                    rma.with_user(user.id).action_refund()
                    if rma.refund_id and rma.refund_id.state == 'draft':
                        rma.refund_id.with_user(user.id).action_post()
                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        access_token = rma.refund_id._ensure_portal_token()
                        tax_credit_4inch_pdf_url = f"{base_url}/my/tax_credit_4inch_pdf/{rma.refund_id.id}?access_token={access_token}&report_type=pdf&download=true"

                    # Journal from worker custodian or fallback
                    journal = False
                    worker_user_id = request.env['res.users'].sudo().browse(user_id)
                    worker_partner = worker_user_id.partner_id
                    custodian_id = request.env['custodian'].sudo().search(
                        [("responsible_custodian", "=", worker_partner.id)], limit=1)
                    for one in custodian_id.journal_ids:
                        journal = one
                    if not journal:
                        journal = request.env['account.journal'].sudo().search([('type', '=', 'cash')], limit=1)

                    if not rma.refund_id:
                        rma.write({"state": "received"})
                        rma._compute_can_be_refunded()
                        rma.write({"can_be_refunded": True})
                        rma.action_refund()

                    if rma.refund_id and (customer.customer_type != 'credit'):
                    # if rma.refund_id and (customer.customer_type != 'credit' or (customer.customer_type == 'credit' and customer.is_credit_hold)):
                        account_payment_register = request.env['account.payment.register'].sudo().with_user(user.id).with_context({
                            'active_model': 'account.move',
                            'active_ids': [rma.refund_id.id],
                            'active_id': rma.refund_id.id,
                            'journal_id': journal.id,
                        }).create({
                            'amount': rma.refund_id.amount_residual,
                            'payment_date': fields.Date.to_string(date.today()),
                            'journal_id': journal.id,
                            'collector_name': user.partner_id.name,
                            'custodian_id': custodian_id.id,
                            'responsible_id': user.partner_id.id,
                            'group_payment': True,
                        })
                        account_payment_register.sudo().action_create_payments()

                        if rma.refund_id.matched_payment_ids:
                            for payment in rma.refund_id.matched_payment_ids:
                                payment.collector_name = user.partner_id.name
                                if payment.state == 'draft':
                                    payment.sudo().action_post()
                                elif payment.state == 'in_process' or not payment.state != "paid":
                                    payment.sudo().action_validate()
            else:
                rma.sudo().action_submit_rma()

            res = {
                'success': True,
                'rma_id': rma.id,
                'rma_name': rma.name,
                'updated_line_ids': updated_line_ids,
                'print': False,
            }
            if tax_credit_4inch_pdf_url:
                res.update({'tax_credit_4inch_pdf_url': tax_credit_4inch_pdf_url, 'print': True})
            return res

        except Exception as e:
            _logger.exception("Error in /api/v1/rma_confirm")
            return {'success': False, 'error_msg': str(e)}

    @http.route('/api/v1/rma_single_product_confirm', type='json', auth='none', methods=['POST'])
    def rma_single_product_confirm(self, **kwargs):
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            product_id = int(values.get('product_id', 0))
            rma_type = values.get('rma_type')
            product_uom_qty = float(values.get('product_uom_qty', 0))
            lot = values.get('lot', 0)
            return_caused_by = int(values.get('return_caused_by'))
            return_reason = int(values.get('return_reason'))
            rma_return_reason = int(values.get('rma_return_reason'))
            fsm_order_id = values.get('fsm_order_id')
            fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            customer_id = values.get('customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)
            if not customer.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            product = request.env['product.product'].sudo().browse(product_id)
            if not product.exists() or not product.active:
                return {'success': False, 'error_msg': 'Product not found.'}

            product_cal = product.lst_price * product_uom_qty
            origin = ''
            if fsm_order:
                partner_name = fsm_order.person_id_partner.name or ''
                fsm_name = fsm_order.name or ''
                origin = f"{partner_name} {fsm_name}".strip()
            rma_vals = {
                'product_id': product.id,
                'partner_id': customer.id,
                'barcode': product.barcode,
                'rma_type': rma_type,
                'grv_amount': product_cal,
                'product_uom_qty': product_uom_qty,
                'return_caused_by': return_caused_by,
                'operation_id': return_reason,
                'return_reason_id': rma_return_reason,
                'lot_number': lot if rma_type == 'base_on_product' and lot else False,
                'user_id': user.id,
                'state': 'draft',
                'visit_id': fsm_order.id,
                'responsible_worker_id': user.partner_id.id,
                'company_id': user.sudo().with_user(SUPERUSER_ID).company_id.id,
                'origin': origin,
                'collection_request_date': fields.Date.today()
            }
            rma = request.env['rma'].sudo().with_user(SUPERUSER_ID).create(rma_vals)

            return {
                'success': True,
                'rma_id': rma.id,
                'rma_name': rma.name,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/rma_single_product_confirm")
            return {'success': False, 'error_msg': str(e)}

    @http.route('/api/v1/rma_multiple_product_confirm', type='json', auth='public', methods=['POST'], csrf=False)
    def rma_multiple_product_confirm(self, **kwargs):
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token = values.get('auth_token')

            customer_id = int(values.get('customer_id', 0))
            fsm_order_id = values.get('fsm_order_id')
            rma_type = values.get('rma_type')
            return_caused_by = int(values.get('return_caused_by', 0))
            return_reason = int(values.get('return_reason', 0))
            rma_return_reason = int(values.get('rma_return_reason', 0))
            grv_no = values.get('grv_no')

            products = values.get('products', [])
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            customer = request.env['res.partner'].sudo().browse(customer_id)
            if not customer.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)
            origin = ''
            if fsm_order.exists():
                partner_name = fsm_order.person_id_partner.name or ''
                fsm_name = fsm_order.name or ''
                origin = f"{partner_name} {fsm_name}".strip()
            product_lines = []
            for product_data in products:
                product_id = int(product_data.get('product_id', 0))
                product_uom_qty = float(product_data.get('product_uom_qty', 0))
                product_uom_id = int(product_data.get('product_uom_id', 0))
                lot = product_data.get('lot', 0)
                return_caused_by_id = int(product_data.get('return_caused_by_id', 0))
                return_reason_id = int(product_data.get('return_reason_id', 0))
                return_reason_type_id = int(product_data.get('return_reason_type_id', 0))
                product_packaging_qty = int(product_data.get('product_packaging_qty', 0))
                product_packaging_id = int(product_data.get('product_packaging_id', 0))

                production_date = product_data.get('production_date', False)
                expiry_date = product_data.get('expiry_date', False)

                if lot == 0 and production_date and expiry_date:
                    lot = str(production_date) + " - " + str(expiry_date)

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists() or not product.active:
                    return {'success': False, 'error_msg': f'Product ID {product_id} not found.'}

                product_lines.append((0, 0, {
                    'product_id': product.id,
                    'price_unit': product.lst_price,
                    'product_uom_qty': product_uom_qty,
                    'product_uom_id': product_uom_id,
                    'return_reason_id': return_reason_id,
                    'lot_number': lot if rma_type == 'base_on_product' and lot else False,
                    'return_reason_type_id': return_reason_type_id,
                    'product_packaging_qty': product_packaging_qty,
                    'product_packaging_id': product_packaging_id,
                    'production_date': production_date,
                    'return_caused_by_id': return_caused_by_id,
                    'excise_tax': product.exercise_price,
                    # 'barcode': product.barcode,
                    # 'grv_amount': product.lst_price * product_uom_qty,
                }))

            if worker_id and worker_id != 0:
                partner = request.env['res.partner'].sudo().browse(worker_id)
            else:
                partner = user.partner_id

            crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [partner.id])],
                                                             limit=1)


            rma_vals = {
                'partner_id': customer.id,
                'rma_type': rma_type,
                'operation_id': return_reason,
                'user_id': user.id,
                'state': 'draft',
                'visit_id': fsm_order.id,
                'company_id': user.sudo().with_user(SUPERUSER_ID).company_id.id,
                'origin': origin,
                'delivery_required': "yes",
                'product_line_ids': product_lines,
                'responsible_worker_id': partner.id,
                'collection_request_date': fields.Date.today(),
            }
            if crm_team:
                rma_vals['crm_team_id'] = crm_team.id

            if return_caused_by:
                rma_vals['return_caused_by'] = return_caused_by

            if worker_id != 0:
                van_location = request.env['stock.location'].sudo().search([('responsible_id','=',user.id)], limit=1)

                if van_location:
                    rma_vals['location_id'] = van_location.id
                else:
                    van_location = partner.van_location
                    if van_location:
                        rma_vals['location_id'] = van_location.id

            rma_vals['sales_person_id'] = partner.id

            if grv_no:
                rma_vals['grv_no'] = grv_no
            rma = request.env['rma'].sudo().with_user(SUPERUSER_ID).create(rma_vals)
            grv_amount = abs(sum(line.total for line in rma.product_line_ids))

            rma.grv_amount = grv_amount

            conf_grv_amount = float(
                request.env['ir.config_parameter'].sudo().get_param('plnx_rma_extended.grv_amount') or 50)
            tax_credit_4inch_pdf_url = False

            _logger.info("---------------------------------------------------------")
            _logger.info(conf_grv_amount)
            _logger.info(rma.grv_amount)
            _logger.info("---------------------------------------------------------")
            if rma.grv_amount <= conf_grv_amount and user.user_type == 'sales_user':
                # rma.sudo().with_user(SUPERUSER_ID).action_submit_rma()
                rma.sudo().with_user(SUPERUSER_ID).action_confirm()
                if rma.reception_move_id and rma.reception_move_id.picking_id:
                    rma.reception_move_id.picking_id.quality_check_todo = True
                    # try:
                    rma_pick = rma.reception_move_id.picking_id.with_user(user.id).sudo()

                    if rma_pick.state in ['draft', 'loaded_dispatched']:
                        rma_pick.with_user(user).sudo().action_confirm()

                    if not rma_pick.picker_partner_id:
                        rma_pick.picker_partner_id = user.partner_id.id
                    if not rma_pick.picking_driver_id:
                        rma_pick.picking_driver_id = user.partner_id.id

                    if rma_pick.state != 'done':
                        rma_pick.with_user(user).sudo().action_assign()

                        for move in rma_pick.move_ids_without_package:
                            move.picker_partner_id = rma_pick.picker_partner_id

                        rma_pick.with_user(user).sudo().action_assign()
                        if not rma_pick.has_packages:
                            try:
                                rma_pick.with_user(user).sudo().action_put_in_pack()
                                rma_pick.has_packages = True
                            except Exception as e:
                                _logger.info(str(e))
                                try:
                                    rma_pick.with_user(user).sudo().action_assign_driver()
                                    rma_pick.with_user(user).sudo().action_item_offload()
                                    rma_pick.with_user(user).sudo().action_collect()
                                except Exception as e:
                                    _logger.info("other error")
                                    _logger.info(str(e))
                        # ---- HERE: wrap button_validate in try/except ----
                        error_message = ""
                        try:
                            # rma_pick.with_user(user).with_context(
                            #     mail_create_nosubscribe=False).sudo().button_validate()

                            # 1) Try to validate
                            action = rma_pick.with_user(user).with_context(
                                mail_create_nosubscribe=False).sudo().button_validate()

                            # 2) AUTO-CONFIRM WIZARDS (expiry/backorder/immediate)
                            def _expired_lot_cmds(picking):
                                """
                                Build default lot line commands for the expiry wizard.
                                Uses any of life_date/use_date/expiration_date/removal_date to decide expiry.
                                """
                                cmds = []
                                now = fields.Datetime.now()
                                for ml in picking.move_line_ids:
                                    lot = ml.lot_id
                                    if not lot:
                                        continue
                                    # consider the earliest relevant expiry-like date
                                    exp_dt = lot.use_date or lot.expiration_date or lot.removal_date
                                    if exp_dt and exp_dt <= now:
                                        cmds.append((0, 0, {
                                            'product_id': ml.product_id.id,
                                            'name': lot.name or '',
                                        }))
                                return cmds

                            def _auto_confirm_picking_wizards(action_dict, picking, acting_user):
                                """
                                Follows any wizard actions returned by button_validate and confirms them automatically.
                                Ensures expected context keys (e.g., default_lot_ids) exist for the expiry wizard.
                                """
                                WIZ_METHODS = {
                                    'expiry.picking.confirmation': 'process',  # your custom / product_expiry wizard
                                    'stock.immediate.transfer': 'process',  # standard
                                    'stock.backorder.confirmation': 'process',
                                    # or 'process_cancel_backorder' to skip backorders
                                }

                                max_hops = 5
                                while isinstance(action_dict, dict) and action_dict.get(
                                        'type') == 'ir.actions.act_window' and max_hops > 0:
                                    res_model = action_dict.get('res_model')
                                    method = WIZ_METHODS.get(res_model, 'process')

                                    # 1) Build a safe context
                                    ctx = dict(action_dict.get('context') or {})
                                    ctx.update({
                                        'active_model': 'stock.picking',
                                        'active_id': picking.id,
                                        'active_ids': [picking.id],
                                    })

                                    # 2) Ensure the keys this wizard expects exist
                                    if res_model in ('expiry.picking.confirmation', 'confirm.expiry'):
                                        # If the action didn't supply default_lot_ids, derive or at least set empty.
                                        ctx.setdefault('default_lot_ids', _expired_lot_cmds(picking))
                                        # Optional niceties – some implementations read these:
                                        ctx.setdefault('default_show_lots', bool(ctx['default_lot_ids']))
                                        ctx.setdefault('default_description', 'Auto-confirmed from API')

                                    WizardEnv = request.env[res_model].with_context(ctx).with_user(acting_user).sudo()
                                    res_id = action_dict.get('res_id')
                                    wiz = WizardEnv.browse(res_id) if res_id else WizardEnv.create({})

                                    # 3) Call the wizard method. If it still complains about missing keys, retry with hard-safe defaults.
                                    try:
                                        action_dict = getattr(wiz, method)() or None
                                    except KeyError as ke:
                                        # Safety net: some custom code does ctx.pop('default_lot_ids') with no default.
                                        if str(ke) == "'default_lot_ids'":
                                            WizardEnv = WizardEnv.with_context(
                                                {**WizardEnv.env.context, 'default_lot_ids': []})
                                            wiz = WizardEnv.browse(res_id) if res_id else WizardEnv.create({})
                                            action_dict = getattr(wiz, method)() or None
                                        else:
                                            raise
                                    max_hops -= 1

                                return True

                            # run the auto-confirm if a wizard popped
                            if isinstance(action, dict) and action.get('type') == 'ir.actions.act_window':
                                _auto_confirm_picking_wizards(action, rma_pick, user)

                        except UserError as e:
                            error_message = str(e)
                            # Detect the “Lot/Serial” case
                            if 'supply a Lot/Serial number' in error_message:
                                # you can customize the wording you return here:
                                error_message = 'Missing Lot/Serial number for some products. ' + error_message
                                original_picking  = rma.picking_id
                                # 2) for each move in the RMA pick, copy over lot & qty_done
                                for move in rma_pick.move_ids_without_package:
                                    # find all original move_lines for this product that have a lot
                                    orig_lines = original_picking.move_line_ids.filtered(
                                        lambda ml: ml.product_id == move.product_id and ml.lot_id
                                    )
                                    # if no RMA move_lines yet, create one per original lot line
                                    if not move.move_line_ids:
                                        for orig in orig_lines:
                                            request.env['stock.move.line'].sudo().create({
                                                'picking_id': rma_pick.id,
                                                'move_id': move.id,
                                                'product_id': move.product_id.id,
                                                'product_uom_id': move.product_uom.id,
                                                'qty_done': orig.qty_done,
                                                'location_id': move.location_id.id,
                                                'location_dest_id': move.location_dest_id.id,
                                                'lot_id': orig.lot_id.id,
                                            })
                                    else:
                                        # update existing lines
                                        for ml in move.move_line_ids:
                                            # fill qty_done if empty
                                            if not ml.qty_done:
                                                ml.qty_done = move.product_uom_qty
                                            # inject lot if missing
                                            if not ml.lot_id and orig_lines:
                                                ml.lot_id = orig_lines[0].lot_id.id

                                rma_pick.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()
                            elif "The entry" in error_message and "must be in draft." in error_message:
                                expiry_refund_id = request.env['account.move'].sudo().search([('invoice_origin','=',rma.name)])
                                if expiry_refund_id and not rma.refund_id:
                                    rma.refund_id = expiry_refund_id.id
                                    rma.sudo().write({"refund_id": expiry_refund_id.id})
                                _logger.info("Not lot error")
                                _logger.info(error_message)
                    if rma.refund_id:
                        account_payment_ids = request.env['account.payment'].sudo().search([('invoice_ids','in', [rma.refund_id.id])])
                        _logger.info('1##############################################################')
                        _logger.info(account_payment_ids)
                        _logger.info('1##############################################################')
                        if rma.refund_id.state == 'draft':
                            rma.refund_id.with_user(user.id).action_post()

                        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        access_token = rma.refund_id._ensure_portal_token()
                        tax_credit_4inch_pdf_url = f"{base_url}/my/tax_credit_4inch_pdf/{rma.refund_id.id}?access_token={access_token}&report_type=pdf&download=true"

                        journal = False

                        custodian_id = request.env['custodian'].sudo().search(
                            [("responsible_custodian", "=", user.partner_id.id)], limit=1)
                        for one in custodian_id.journal_ids:
                            if one.type == "cash":
                                journal = one
                        if not journal:
                            journal = request.env['account.journal'].sudo().search([
                                ('type', '=', 'cash'),
                            ])

                        journal_id = journal.id
                        if customer.customer_type != 'credit':
                        # if customer.customer_type != 'credit' or (customer.customer_type == 'credit' and customer.is_credit_hold == True):
                            try:
                                _logger.info('2##############################################################')
                                _logger.info(account_payment_ids)
                                _logger.info('2##############################################################')

                                account_payment_register = request.env['account.payment.register'].sudo().with_user(
                                    user.id).with_context({
                                    'active_model': 'account.move',
                                    'active_ids': [rma.refund_id.id],
                                    'active_id': rma.refund_id.id,
                                    'journal_id': journal_id,
                                }).sudo().create({
                                    'journal_id': journal_id,
                                    'responsible_id': user.partner_id.id,
                                    'custodian_id': custodian_id.id,
                                })

                                account_payment_register.sudo().action_create_payments()
                            except UserError as ue:
                                error_message = str(ue)
                                if "The entry" in error_message and "must be in draft." in error_message:
                                    def _extract_move_id_from_error(msg: str):
                                        """
                                        Parse '(id 598930)' or 'id 598930' from a UserError message.
                                        """
                                        m = re.search(r'\(id\s*(\d+)\)', msg)
                                        if not m:
                                            m = re.search(r'\bid\s*([0-9]{3,})\b', msg)
                                        return int(m.group(1)) if m else None

                                    def _link_payment_move_to_invoice(move_id, invoice, user):
                                        """
                                        Given an account.move ID for a payment entry, reconcile it with the (posted) invoice.
                                        Works on v14+ where payments are account.payment + move, or pure move fallback.
                                        """
                                        if not move_id or not invoice:
                                            return False

                                        Move = request.env['account.move'].sudo()
                                        move = Move.browse(int(move_id))
                                        if not move.exists():
                                            return False

                                        # Find account.payment if present
                                        payment = False
                                        if 'payment_id' in move._fields and move.payment_id:
                                            payment = move.payment_id
                                        elif 'account.payment' in request.env:
                                            payment = request.env['account.payment'].sudo().search(
                                                [('move_id', '=', move.id)], limit=1)

                                        # Ensure both documents are posted
                                        if invoice.state != 'posted':
                                            invoice.with_user(user.id).sudo().action_post()

                                        if payment and hasattr(payment, 'state') and payment.state != 'posted':
                                            payment.with_user(user.id).sudo().action_post()
                                        elif move.state != 'posted':
                                            move.with_user(user.id).sudo().action_post()

                                        # Company sanity check (avoid cross-company reconciliation surprises)
                                        if move.company_id.id != invoice.company_id.id:
                                            raise UserError(
                                                "Payment company differs from invoice company; cannot reconcile automatically.")

                                        # Grab open receivable/payable lines on both sides
                                        def _is_rp(line):
                                            at = getattr(line.account_id, 'account_type', False) or getattr(
                                                line.account_id, 'internal_type', False)
                                            return at in (
                                            'asset_receivable', 'liability_payable', 'receivable', 'payable')

                                        inv_lines = invoice.line_ids.filtered(lambda l: _is_rp(l) and not l.reconciled)
                                        pay_lines = move.line_ids.filtered(lambda l: _is_rp(
                                            l) and not l.reconciled and l.partner_id.id == invoice.partner_id.id)

                                        if not inv_lines or not pay_lines:
                                            # Nothing to reconcile (maybe already done or wrong lines)
                                            return False

                                        (inv_lines + pay_lines).with_user(user.id).sudo().reconcile()
                                        invoice.matched_payment_ids = [(4, payment.id)]
                                        invoice.sudo().write({"matched_payment_ids": [(4, payment.id)]})
                                        return True
                                    move_id = _extract_move_id_from_error(error_message)
                                    # reconcile that existing payment JE with your refund invoice
                                    _link_payment_move_to_invoice(move_id, rma.refund_id, user)

                            if rma.refund_id.matched_payment_ids:
                                _logger.info('3##############################################################')
                                _logger.info(account_payment_ids)
                                _logger.info('3##############################################################')

                                for payment in rma.refund_id.matched_payment_ids:
                                    if payment.state == 'draft':
                                        payment.action_post()
                                    elif payment.state == 'in_process' or not payment.state != "paid":
                                        payment.action_validate()
                    else:
                        rma.sudo().with_user(user.id).sudo().action_refund()
                        if rma.refund_id.state == 'draft':
                            rma.refund_id.with_user(user.id).sudo().action_post()

                            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                            access_token = rma.refund_id._ensure_portal_token()
                            tax_credit_4inch_pdf_url = f"{base_url}/my/tax_credit_4inch_pdf/{rma.refund_id.id}?access_token={access_token}&report_type=pdf&download=true"

                        journal = False

                        custodian_id = request.env['custodian'].sudo().search(
                            [("responsible_custodian", "=", user.partner_id.id)], limit=1)
                        for one in custodian_id.journal_ids:
                            if one.type == "cash":
                                journal = one
                        if not journal:
                            journal = request.env['account.journal'].sudo().search([
                                ('type', '=', 'cash'),
                            ])

                        journal_id = journal.id
                        if not rma.refund_id:
                            rma.state = "received"
                            rma.sudo().write({"state": "received"})
                            rma.sudo()._compute_can_be_refunded()
                            rma.sudo().can_be_refunded = True
                            rma.sudo().write({"can_be_refunded": True})
                            rma.sudo().action_refund()
                            if rma.refund_id.state == 'draft':
                                rma.refund_id.with_user(user.id).sudo().action_post()

                        if customer.customer_type != 'credit':
                        # if customer.customer_type != 'credit' or (customer.customer_type == 'credit' and customer.is_credit_hold == True):
                            account_payment_register = request.env['account.payment.register'].sudo().with_user(
                                user.id).with_context({
                                'active_model': 'account.move.line',
                                'active_ids': rma.refund_id.line_ids.ids,
                                'journal_id': journal_id,
                                'custodian_id': custodian_id.id,
                                'responsible_id': user.partner_id.id,
                            }).sudo().create({
                                'journal_id': journal_id,
                                'responsible_id': user.partner_id.id,
                                'collector_name': user.partner_id.name,
                                'custodian_id': custodian_id.id,
                            })
                            account_payment_register.sudo().action_create_payments()
                            if rma.refund_id.matched_payment_ids:
                                for payment in rma.refund_id.matched_payment_ids:
                                    if payment.state == 'draft':
                                        payment.sudo().action_post()
                                    elif payment.state == 'in_process' or not payment.state != "paid":
                                        payment.sudo().action_validate()
            else:
                rma.sudo().action_submit_rma()
            res = {
                'success': True,
                'rma_id': rma.id,
                'rma_name': rma.name,
                'print': False,
            }
            if tax_credit_4inch_pdf_url:
                res.update({'tax_credit_4inch_pdf_url':tax_credit_4inch_pdf_url, 'print': True})
            return res

        except Exception as e:
            _logger.exception("Error in /api/v1/rma_multiple_product_confirm")
            return {'success': False, 'error_msg': str(e)}

    @http.route('/api/v1/rma_single_product_list', type='json', auth='public', methods=['POST'])
    def rma_single_product_list(self, **kwargs):
        values = request.httprequest.json or {}
        try:
            # === Auth & inputs ====================================================
            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token = values.get('auth_token')
            customer_id = int(values.get('customer_id', 0))

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            company = request.env['res.company'].sudo().search([], limit=1)
            partner = request.env['res.partner'].sudo().browse(worker_id) if worker_id else user.partner_id
            pricelist = partner.with_company(company).property_product_pricelist

            # === Helper: normalize date/datetime -> 'YYYY-MM-DD' ==================
            def _to_date_str(value):
                if not value:
                    return None
                try:
                    if isinstance(value, datetime):
                        value = value.date()
                    if isinstance(value, date):
                        return fields.Date.to_string(value)
                    return str(value)
                except Exception:
                    try:
                        return value.isoformat()
                    except Exception:
                        return str(value)

            # === Fetch ONLY lots that belong to eligible products AND HAVE expiry ===
            # We filter on product fields via dotted domain + require any expiration field.
            lots = request.env['stock.lot'].sudo().search([
                ('product_id.sale_ok', '=', True),
                ('product_id.type', '=', 'consu'),
                ('product_id.active', '=', True),
                ('product_id.brand_id', '!=', False),
                '|', ('company_id', '=', company.id), ('company_id', '=', False),
                # has an expiration date in one of the known fields
                ('expiration_date', '!=', False),
            ], order='create_date desc')

            # Keep only lots where the resolved expiration is actually present
            qualified_lots = []
            for lot in lots:
                exp_raw = lot.expiration_date or lot.life_date or lot.removal_date or lot.alert_date
                exp_str = _to_date_str(exp_raw)
                if exp_str:
                    qualified_lots.append((lot, exp_str))

            if not qualified_lots:
                # No lots with expiration → no products to show
                return {
                    'success': True,
                    'count': 0,
                    'brands': [],
                    'return_operation_data': [],
                    'rma_return_reason': [],
                    'rma_return_reason_type': [],
                    'return_caused_by': [],
                }

            # === Determine the product set from qualified lots ====================
            product_ids = list({lot.product_id.id for lot, _ in qualified_lots})

            # Now fetch ONLY those products (brand/sale_ok/type/active already implied by lots)
            products = request.env['product.product'].sudo().browse(product_ids)

            # === Batch prefetch packaging for these products ======================
            packagings = request.env['product.packaging'].sudo().search([('product_id', 'in', product_ids)])
            packaging_map = defaultdict(list)
            for p in packagings:
                packaging_map[p.product_id.id].append({
                    'id': p.id,
                    'name': p.name,
                    'uom': p.product_uom_id.name,
                    'uom_id': p.product_uom_id.id,
                    'qty_per_pack': p.qty,
                    'on_hand_qty': 1,  # keep your previous shape
                })

            # === Build lot maps ====================================================
            lot_map_flat = defaultdict(list)  # flat list (backward compat)
            lot_map_by_exp = defaultdict(lambda: defaultdict(list))  # expiration -> lots

            for lot, exp_str in qualified_lots:
                # flat
                lot_map_flat[lot.product_id.id].append({
                    'id': lot.id,
                    'name': lot.name,
                    # 'expiration_date': exp_str,  # uncomment if you also want it here
                })
                # grouped
                lot_map_by_exp[lot.product_id.id][exp_str].append({
                    'id': lot.id,
                    'name': lot.name,
                })

            # === Build response: brands + "All" ===================================
            brand_buckets = {}
            all_products = []
            _img = self._get_image_url_dynamic

            for product in products:
                price = pricelist._get_product_price(product, 1.0) if pricelist else product.list_price

                # Expiration groups sorted ascending; each has its related lots
                exp_groups = []
                exp_dict = lot_map_by_exp.get(product.id, {})
                for exp_key in sorted(exp_dict.keys()):  # 'YYYY-MM-DD' strings sort fine
                    exp_groups.append({
                        'expiration_date': exp_key,
                        'lots': sorted(exp_dict[exp_key], key=lambda x: x['name']),
                    })

                entry = {
                    'product_id': product.id,
                    'product_name': product.display_name,
                    'barcode': product.barcode,
                    'default_code': product.default_code,
                    'uom': product.uom_id.name,
                    'uom_id': product.uom_id.id,
                    'lst_price': price,
                    'product_packaging': packaging_map.get(product.id, []),

                    # NEW: what your app needs for the dropdown flow
                    'expirations': exp_groups,  # [{expiration_date, lots:[{id,name},...]}, ...]
                    # Keep old flat list if some clients still read it
                    'lots': lot_map_flat.get(product.id, []),

                    'on_hand_qty': 1,  # unchanged shape
                    'image': _img(product._name, product.id, 'image_1920'),
                }

                bid = product.brand_id.id or 0
                bname = product.brand_id.name or 'Unbranded'
                bucket = brand_buckets.setdefault(bid, {'brand_id': bid, 'brand': bname, 'products': []})
                bucket['products'].append(entry)
                all_products.append(entry)

            brands = [{'brand_id': 0, 'brand': 'All', 'products': all_products}] + list(brand_buckets.values())

            # === RMA meta (unchanged) =============================================
            crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [partner.id])], limit=1)

            rma_return_casued_by = []
            rma_return_reason = []
            if crm_team:
                rcb_obj = request.env['rma.return.caused.by'].sudo().search([('sales_teams', '=', crm_team.id)])
                rma_return_casued_by = rcb_obj.mapped('return_caused_by_ids')
                rma_return_reason = rcb_obj.mapped('return_reason_ids')
            if not rma_return_reason:
                rma_return_reason = request.env['rma.return.reason'].sudo().search([])

            rma_return_reason_list = [{'id': r.id, 'name': r.name} for r in rma_return_reason]
            rma_return_caused_by_list = [{'id': c.id, 'name': c.name} for c in rma_return_casued_by]

            opts = dict(
                return_operation_data=request.env['rma.operation'].sudo().search_read([], ['id', 'name']),
                rma_return_reason=rma_return_reason_list,
                rma_return_reason_type=request.env['rma.return.reason.type'].sudo().search_read([], ['id', 'name']),
                return_caused_by=rma_return_caused_by_list,
            )

            return {'success': True, 'count': len(brands), 'brands': brands, **opts}

        except Exception as e:
            _logger.exception("Error in /api/v1/rma_single_product_list")
            return {'success': False, 'error_msg': str(e)}

    @http.route('/api/v1/outstanding_invoices', type='json', auth='none', methods=['POST'])
    def get_outstanding_invoices(self, **kwargs):
        try:
            values = request.httprequest.json
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            customer_id = int(values.get('customer_id', 0))
            worker_id = int(values.get('worker_id', 0))

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "=", "not_paid")
            ]
            if customer_id:
                domain.append(("partner_id", "=", customer_id))

            invoices = request.env['account.move'].sudo().search(domain)

            invoice_list = []
            total_due = 0.0

            for inv in invoices:
                invoice_list.append({
                    'invoice_id': inv.id,
                    'invoice_name': inv.name,
                    'customer_reference': inv.partner_id.ref,
                    'invoice_date': inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                    'amount_total': inv.amount_total,
                    'currency': inv.currency_id.name,
                    'partner_id': inv.partner_id.id,
                    'partner_name': inv.partner_id.name,
                })
                total_due += inv.amount_residual
            account_journals = False
            journals_list = []


            if worker_id != 0:
                partner_id = request.env['res.partner'].sudo().browse(worker_id)
            else:
                partner_id = user.partner_id

            custodian_id = request.env['custodian'].sudo().search([("responsible_custodian","=", partner_id.id )], limit=1)
            account_journal_ids = []
            if custodian_id and custodian_id.journal_ids:
                account_journal_ids = custodian_id.journal_ids
            if not account_journal_ids:
                account_journal_ids = request.env['account.journal'].sudo().search([
                    ('is_pdc', '=', True)
                ])



            for journal in account_journal_ids:
                payment_method_list = []
                for inbound in custodian_id.inbound_payment_method_line_ids:
                    if inbound.journal_id.id == journal.id:
                        payment_method_list.append({"name": inbound.name, "id": inbound.id})
                journals_list.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'payment_methods': payment_method_list,
                })

            #
            # if custodian_id and custodian_id.journal_ids:
            #     account_journals = custodian_id.journal_ids[0]
            # if not account_journals:
            #     account_journals = request.env['account.journal'].sudo().search([
            #         ('type', '=', 'cash'),
            #     ])
            #
            # journal_data = account_journals.read(['id', 'name'])

            return {
                'success': True,
                'count': len(invoice_list),
                'total_due': total_due,
                'trx_date': date.today(),
                'invoices': invoice_list,
                'account_journal': journals_list
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/outstanding_invoices")
            return {'success': False, 'error_msg': str(e)}

    @http.route('/api/v1/confirm_invoice_payment', type='json', auth='none', methods=['POST'])
    def confirm_invoice_payment(self, **kwargs):
        try:
            values = request.httprequest.json
            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token = values.get('auth_token')
            invoice_ids = values.get('invoice_ids', [])
            journal_id = values.get('journal_id')
            payment_date = values.get('payment_date') or fields.Date.today()
            paid_amount = float(values.get('paid_amount', 0))
            memo = values.get('memo', '')
            fsm_order_id = values.get('fsm_order_id')

            if not user_id or not auth_token:
                return {'success': False, 'error_msg': 'Missing user ID or auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            invoices = request.env['account.move'].sudo().browse(invoice_ids).filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted' and inv.payment_state != 'paid'
            )

            if not invoices:
                return {'success': False, 'error_msg': 'No valid unpaid invoices found.'}

            partner_ids = invoices.mapped('partner_id.id')
            if len(set(partner_ids)) > 1:
                return {'success': False, 'error_msg': 'Selected invoices belong to different customers.'}
            partner = invoices[0].partner_id
            company_id = invoices[0].company_id.id
            if not company_id:
                return {'success': False, 'error_msg': 'Invoice is not linked to a company.'}

            journal = request.env['account.journal'].sudo().browse(journal_id)
            if not journal.exists():
                return {'success': False, 'error_msg': 'Invalid journal ID.'}
            if journal.company_id.id != company_id:
                return {'success': False, 'error_msg': 'Journal company does not match invoice company.'}

            payment_method = request.env.ref('account.account_payment_method_manual_in', raise_if_not_found=False)
            if not payment_method:
                return {'success': False, 'error_msg': 'Manual inbound payment method not configured.'}
            ctx = {
                'active_model': 'account.move.line',
                'active_ids': invoices.line_ids.ids,
                'company_id': company_id,
                'allowed_company_ids': [company_id]
            }
            payment_wiz = request.env['account.payment.register'].sudo().with_context(**ctx).create({
                'journal_id': journal_id,
                'payment_date': payment_date,
                'communication': memo or 'BATCH/' + fields.Date.today().strftime('%Y/%m/%d') + '/' + str(
                    random.randint(1000, 9999)),
            })

            # try to fix the singleton issue
            payments = False
            for one_payment in payment_wiz:
                _logger.info("One Payment Generated from wiz %s" % one_payment)
                payments = one_payment.sudo().with_user(SUPERUSER_ID)._create_payments()
                if not payments:
                    return {'success': False, 'error_msg': 'Payment creation failed.'}

                payments.sudo().with_user(SUPERUSER_ID).action_validate()
            if not payments:
                return {'success': False, 'error_msg': 'Payment creation failed.'}

            for inv in invoices:
                payment_lines = payments.mapped('move_id').line_ids.filtered(lambda l: l.account_id.id in inv.line_ids.mapped('account_id').ids)
                inv_lines = inv.line_ids.filtered(lambda l: l.account_id.account_type in ('receivable', 'payable'))
                (payment_lines + inv_lines).filtered(lambda l: not l.reconciled).reconcile()
            updated_invoices = []
            for inv in invoices:
                inv.with_user(SUPERUSER_ID)._compute_amount()
                updated_invoices.append({
                    'invoice_id': inv.id,
                    'invoice_name': inv.name,
                    'payment_state': inv.payment_state,
                    'residual_amount': inv.amount_residual,
                    'currency': inv.currency_id.name
                })

            return {
                'success': True,
                'payment_id': [payment.id for payment in payments],
                'payment_name': [payment.name for payment in payments],
                'amount': [payment.amount for payment in payments],
                'currency': [payment.currency_id.name for payment in payments],
                'message': 'Payment successfully processed.',
                'invoices': updated_invoices
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/confirm_invoice_payment: %s", str(e))
            return {'success': False, 'error_msg': 'System error occurred while processing payment.'}

    @http.route('/api/v1/outstanding_confirm_invoice_payment', type='json', auth='none', methods=['POST'], csrf=False)
    def outstanding_confirm_invoice_payment(self, **kwargs):
        try:
            values = request.httprequest.json
            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token = values.get('auth_token')
            invoice_ids = values.get('invoice_ids', [])
            journal_id = values.get('journal_id')
            payment_date = values.get('payment_date') or fields.Date.today()
            paid_amount = float(values.get('paid_amount', 0))
            memo = values.get('memo', '')
            fsm_order_id = values.get('fsm_order_id')

            payment_method_id = values.get('payment_method_id')  # Optional
            cheque_number = values.get('cheque_number')
            cheque_date = values.get('cheque_date')
            cheque_pic = values.get('cheque_pic')  # base64 image string
            bank_id = values.get('bank_id')
            note = values.get('note')
            cheque_owner = values.get('cheque_owner')

            if not user_id or not auth_token:
                return {'success': False, 'error_msg': 'Missing user ID or auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            invoices = request.env['account.move'].sudo().browse(invoice_ids).filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted' and inv.payment_state != 'paid'
            )

            if not invoices:
                return {'success': False, 'error_msg': 'No valid unpaid invoices found.'}

            partner_ids = invoices.mapped('partner_id.id')
            if len(set(partner_ids)) > 1:
                return {'success': False, 'error_msg': 'Selected invoices belong to different customers.'}
            partner = invoices[0].partner_id
            company_id = invoices[0].company_id.id
            if not company_id:
                return {'success': False, 'error_msg': 'Invoice is not linked to a company.'}

            journal = request.env['account.journal'].sudo().browse(journal_id)
            if not journal.exists():
                return {'success': False, 'error_msg': 'Invalid journal ID.'}
            if journal.company_id.id != company_id:
                return {'success': False, 'error_msg': 'Journal company does not match invoice company.'}

            payment_method = request.env.ref('account.account_payment_method_manual_in', raise_if_not_found=False)
            if not payment_method:
                return {'success': False, 'error_msg': 'Manual inbound payment method not configured.'}
            ctx = {
                'active_model': 'account.move.line',
                'active_ids': invoices.line_ids.ids,
                'company_id': company_id,
                'allowed_company_ids': [company_id],
                'visit_id': fsm_order_id
            }
            fsm = request.env['fsm.order'].sudo().browse(fsm_order_id)
            fsm_name = fsm.name if fsm.exists() else 'NO-FSM'

            if worker_id != 0:
                worker_partner = request.env['res.partner'].sudo().browse(worker_id)
            else:
                worker_partner = user.partner_id

            payment_vals = {
                'journal_id': journal_id,
                'payment_date': payment_date,
                'communication': memo or 'VAN TEAM/' + fsm_name + '/' + fields.Date.today().strftime(
                    '%Y/%m/%d') + '/' + str(random.randint(1000, 9999)),
                'responsible_id': worker_partner.id,
                'group_payment': True
            }
            real_payment_vals = {}
            origin_payment = {}
            # if cheque_date:
            #     real_payment_vals['date'] = cheque_date
            if note:
                real_payment_vals['pdc_payable_note'] = note
            if cheque_pic:
                real_payment_vals['cheque_scanning'] = cheque_pic
            if payment_method:
                real_payment_vals['payment_method_id'] = payment_method.id
            if payment_method_id:
                real_payment_vals['payment_method_line_id'] = payment_method_id
                # payment_vals['payment_method_id'] = payment_method.id

                payment_method_line_id_obj = request.env['account.payment.method.line'].sudo().browse(int(payment_method_id))
                if payment_method_line_id_obj:
                    if payment_method_line_id_obj.payment_method_id.is_cdc_method:
                        payment_mode = 'cdc'
                        real_payment_vals['payment_mode'] = payment_mode
                        if bank_id:
                            real_payment_vals['cdc_bank_id'] = bank_id
                        if cheque_number:
                            real_payment_vals['cdc_ref'] = cheque_number
                        if note:
                            real_payment_vals['cdc_payable_note'] = note
                        if cheque_owner:
                            real_payment_vals['cheque_owner'] = cheque_owner
                        if worker_partner:
                            real_payment_vals['collector_name'] = worker_partner.name
                    elif payment_method_line_id_obj.payment_method_id.is_pdc_method:
                        payment_mode = 'pdc'
                        real_payment_vals['payment_mode'] = payment_mode
                        if bank_id:
                            real_payment_vals['pdc_bank_id'] = bank_id
                        if cheque_number:
                            real_payment_vals['pdc_ref'] = cheque_number
                        if note:
                            real_payment_vals['pdc_payable_note'] = note
                        if cheque_owner:
                            real_payment_vals['cheque_owner'] = cheque_owner
                        if worker_partner:
                            real_payment_vals['collector_name'] = worker_partner.name

            payment_wiz = request.env['account.payment.register'].sudo().with_context(**ctx).create(payment_vals)

            payments = False
            _logger.info("Payment Generated from wiz %s" % payment_wiz)
            receipt_voucher_links = []
            for one_payment in payment_wiz:
                _logger.info("One Payment Generated from wiz %s" % one_payment)
                payments = one_payment.sudo().with_user(SUPERUSER_ID).with_context(**ctx)._create_payments()
                if not payments:
                    return {'success': False, 'error_msg': 'Payment creation failed.'}
                payments.sudo().with_user(SUPERUSER_ID).write(real_payment_vals)
                payments.sudo().with_user(SUPERUSER_ID).action_validate()
                visit_record = request.env['fsm.order'].browse(fsm_order_id)
                linked_invoice_list = []
                for line in invoices.line_ids:
                    linked_invoice_list.append((4, line.id))
                visit_record.sudo().write({'invoice_lines': linked_invoice_list})

            if not payments:
                return {'success': False, 'error_msg': 'Payment creation failed.'}
            for payment in payments:
                access_token = payment._ensure_portal_token()
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                receipt_voucher_4inch_pdf_url = f"{base_url}/my/receipt_voucher_4inch_pdf/{payment.id}?access_token={access_token}&report_type=pdf&download=true"
                receipt_voucher_links.append(receipt_voucher_4inch_pdf_url)

            for inv in invoices:
                payment_lines = payments.mapped('move_id').line_ids.filtered(
                    lambda l: l.account_id.id in inv.line_ids.mapped('account_id').ids)
                inv_lines = inv.line_ids.filtered(lambda l: l.account_id.account_type in ('receivable', 'payable'))
                (payment_lines + inv_lines).filtered(lambda l: not l.reconciled).reconcile()
            updated_invoices = []
            for inv in invoices:
                inv.with_user(SUPERUSER_ID)._compute_amount()
                updated_invoices.append({
                    'invoice_id': inv.id,
                    'invoice_name': inv.name,
                    'payment_state': inv.payment_state,
                    'residual_amount': inv.amount_residual,
                    'currency': inv.currency_id.name
                })

            return {
                'success': True,
                'payment_id': [payment.id for payment in payments],
                'payment_name': [payment.name for payment in payments],
                'amount': [payment.amount for payment in payments],
                'currency': [payment.currency_id.name for payment in payments],
                'message': 'Payment successfully processed.',
                'invoices': updated_invoices,
                'receipt_voucher_links': receipt_voucher_links,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/confirm_invoice_payment: %s", str(e))
            return {'success': False, 'error_msg': 'System error occurred while processing payment.'}

    @http.route('/api/v1/payment_collection_data', type='json', auth='none', methods=['POST'])
    def payment_collection_data(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            customer_id = values.get('customer_id')
            worker_id = values.get('worker_id', 0)


            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {
                    'success': False,
                    'error_msg': 'Invalid or expired auth token.'
                }
            user = request.env['res.users'].sudo().browse(user_id)
            customer = request.env['res.partner'].sudo().browse(customer_id)
            if not customer.exists():
                return {
                    'success': False,
                    'error_msg': 'Customer not found.'
                }

            total_overdue = customer.with_user(user.id).sudo().total_overdue

            if worker_id != 0:
                partner_id = request.env['res.partner'].sudo().browse(worker_id)
            else:
                partner_id = user.partner_id

            custodian_id = request.env['custodian'].sudo().search([("responsible_custodian","=", partner_id.id )], limit=1)
            account_journal_ids = []
            if custodian_id and custodian_id.journal_ids:
                account_journal_ids = custodian_id.journal_ids
            if not account_journal_ids:
                account_journal_ids = request.env['account.journal'].sudo().search([
                    ('is_pdc', '=', True)
                ])


            bank = request.env['res.bank'].sudo().search([])
            bank_data = bank.read(['id', 'name'])
            if not bank.exists():
                return {'success': False, 'error_msg': 'Invalid bank ID.'}

            journals_list = []
            for journal in account_journal_ids:
                payment_method_list = []
                for inbound in custodian_id.inbound_payment_method_line_ids:
                    if inbound.journal_id.id == journal.id:
                        payment_method_list.append({"name": inbound.name, "id": inbound.id})
                journals_list.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'payment_methods': payment_method_list,
                })

            response.update({
                'success': True,
                'data': {
                    'customer_id': customer.id,
                    'total_overdue': round(total_overdue, 2),
                    'account_journals': journals_list,
                    'bank': bank_data
                }
            })

        except Exception as e:
            _logger.exception("Error in /api/v1/payment_collection_data")
            response.update({
                'success': False,
                'error_msg': str(e)
            })

        return response

    @http.route('/api/v1/create_payment_collection', type='json', auth='none', methods=['POST'])
    def create_payment_collection(self, **kwargs):
        try:
            values = request.httprequest.json

            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token =values.get('auth_token')
            amount = float(values.get('amount', 0))
            journal_id = values.get('journal_id')
            cheque_owner = values.get('cheque_owner')
            payment_method_id = values.get('payment_method_id')

            journal = request.env['account.journal'].sudo().browse(journal_id)
            if not journal.exists():
                return {'success': False, 'error_msg': 'Invalid journal ID.'}


            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired token.'}

            bank_id = int(values.get('bank_id', 0))

            customer_id = values.get('customer_id')
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid partner ID.'}

            cheque_date = values.get('cheque_date',False)
            if cheque_date:
                try:
                    cheque_date = fields.Date.to_date(values['cheque_date'])
                    # if cheque_date < fields.Date.today():
                    #     return {'success': False, 'error_msg': 'Cheque date cannot be in the past for PDC.'}
                except ValueError:
                    return {'success': False, 'error_msg': 'Invalid date format. Use YYYY-MM-DD.'}

            if worker_id != 0:
                worker_partner = request.env['res.partner'].sudo().browse(worker_id)
            else:
                worker_partner = user.partner_id

            custodian_id = request.env['custodian'].sudo().search([("responsible_custodian","=", worker_partner.id )], limit=1)

            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': amount,
                'currency_id': user.company_id.currency_id.id,
                'company_id': user.company_id.id,
                'responsible_id': worker_partner.id,
                'collector_name': worker_partner.name,
            }
            if custodian_id:
                payment_vals['custodian_id'] = custodian_id.id

            if payment_method_id:
                payment_vals['payment_method_line_id'] = int(payment_method_id)

            cheque_number = values['cheque_number']
            note = values.get('note', '')
            cheque_pic = values.get('cheque_pic')
            is_pdc_payable = values.get('is_pdc_payable')
            if cheque_date:
                payment_vals['due_date'] = cheque_date
            if journal:
                payment_vals['journal_id'] = journal.id
                # payment_vals['payment_method_line_id'] = journal.inbound_payment_method_line_ids[0].id
            if is_pdc_payable:
                payment_vals['is_pdc_payable'] = True
            if bank_id:
                payment_vals['pdc_bank_id'] = bank_id
            if cheque_number:
                payment_vals['pdc_ref'] = cheque_number
            if note:
                payment_vals['pdc_payable_note'] = note
                payment_vals['memo'] = note
            if cheque_pic:
                payment_vals['cheque_scanning'] = cheque_pic
            if cheque_owner:
                payment_vals['cheque_owner'] = cheque_owner
            if worker_partner:
                payment_vals['collector_name'] = worker_partner.name

            # cheque_pic_base64 = values.get('cheque_pic')
            if cheque_pic:
                try:
                    cheque_binary = base64.b64decode(cheque_pic + '===')
                    payment_vals['cheque_scanning'] = base64.b64encode(cheque_binary).decode()
                except Exception as e:
                    return {'success': False, 'error_msg': f'Invalid cheque_pic base64: {str(e)}'}


            if values.get('invoice_id'):
                try:
                    payment_vals['invoice_ids'] = [(4, int(values['invoice_id']))]
                except ValueError:
                    return {'success': False, 'error_msg': 'Invalid invoice ID format.'}

            payment = request.env['account.payment'].with_user(user.id).sudo().create(payment_vals)
            if payment.payment_mode == 'cdc':
                if cheque_number:
                    payment.cdc_ref = cheque_number
                    payment.pdc_ref = False

                if bank_id:
                    payment.cdc_bank_id = bank_id
                    payment.pdc_bank_id = False

            payment.with_user(user.id).sudo().action_post()
            access_token = payment._ensure_portal_token()
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            receipt_voucher_4inch_pdf_url = f"{base_url}/my/receipt_voucher_4inch_pdf/{payment.id}?access_token={access_token}&report_type=pdf&download=true"

            return {
                'success': True,
                'payment_id': payment.id,
                'payment_name': payment.name,
                'receipt_voucher_4inch_pdf_url': receipt_voucher_4inch_pdf_url,
                'message': 'PDC Collection successfully created.'
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/create_payment_collection: %s", str(e))
            return {'success': False, 'error_msg': 'System error occurred while creating collection.'}

    @http.route('/api/v1/pre_sale_stock_count', type='json', auth='none', methods=['POST'], csrf=False)
    def pre_sale_stock_count(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = int(values.get('user_id'))
            auth_token = values.get('auth_token')
            fsm_order_id = int(values.get('fsm_order_id'))
            barcode = values.get('barcode')
            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)
            if not fsm_order or not fsm_order.location_id or not fsm_order.location_id.inventory_location_id:
                return {'success': False, 'error_msg': 'Invalid FSM order or location data missing.'}

            product = request.env['product.product'].sudo().search([
                ('barcode', '=', barcode),
                ('active','=', True)
            ], limit=1)

            if not product:
                return {'success': False, 'error_msg': 'Product with this barcode not found.'}
            brand_list = []
            all_brand = request.env['product.brand'].sudo().search([])

            product_packaging_list = []
            product_packaging = request.env['product.packaging'].sudo().search([])
            for packages in product_packaging:
                product_packaging_list.append({
                    'id': packages.id,
                    'name': packages.name,
                    'uom': packages.product_uom_id.name
                })

            for brand in all_brand:
                products = request.env['product.template'].sudo().search([
                    ('sale_ok', '=', True),
                    ('type', '=', 'consu'),
                    ('brand_id', '=', brand.id),
                    ('active','=', True),
                ])

                product_list = []
                for prod in products:
                    packaging_data = []
                    for packaging in prod.packaging_ids:
                        packaging_data.append({
                            'id': packaging.id,
                            'name': packaging.name,
                            'uom': packaging.product_uom_id.name,
                            'uom_id': packaging.product_uom_id.id,
                            'qty_per_pack': packaging.qty
                        })

                        brand_list.append({
                            'id': brand.id,
                            'name': brand.name,
                            'products': product_list
                        })

            response.update({
                'success': True,
                'product': {
                    'fsm_order_id': fsm_order.id,
                    'product_id': product.id,
                    'product_name': product.name,
                    'default_code': product.default_code,
                    'barcode': product.barcode,
                    'image': self._get_image_url_dynamic(
                        model=product._name,
                        record_id=product.id,
                        field_name='image_1920'
                    ),
                    'uom': product.uom_id.name,
                    'uom_id': product.uom_id.id,
                    'brand_id': product.brand_id.id if product.brand_id else 0,
                    'brand_name': product.brand_id.name if product.brand_id else 'Unbranded',
                    'product_packaging': packaging_data,
                },
            })

        except Exception as e:
            _logger.exception("Error in /api/v1/pre_sale_stock_count")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    @http.route('/api/v1/pre_sale_stock_confirm', type='json', auth='none', methods=['POST'], csrf=False)
    def pre_sale_stock_confirm(self, **kwargs):
        response = {}
        values = request.httprequest.json

        try:
            user_id = int(values.get('user_id'))
            auth_token = values.get('auth_token')
            fsm_order_id = int(values.get('fsm_order_id'))
            products = values.get('products', [])

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)
            if not fsm_order:
                return {'success': False, 'error_msg': 'FSM order not found.'}

            context = {
                'customer_id': fsm_order.customer_id.id,
                'location_id': fsm_order.location_id.id,
                'visit_id': fsm_order.id,
                'worker_id': fsm_order.person_id_partner.id if fsm_order.person_id_partner else False,
                'date': fields.Date.today(),
            }

            stock_record = request.env['customer.stock'].sudo().create(context)
            customer_stock_id = stock_record.id

            product_lines = []
            for item in products:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 0)

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists() and not product.active:
                    continue

                line = (0, 0, {
                    'product_id': product.id,
                    'qty': quantity
                })
                product_lines.append(line)

            stock_record.sudo().write({'line_ids': product_lines})

            response_lines = []
            for line in stock_record.line_ids:
                response_lines.append({
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'barcode': line.product_id.barcode,
                    'uom': line.product_id.uom_id.name,
                    'uom_id': line.product_id.uom_id.id,
                    'quantity': line.qty,
                    'default_code': line.product_id.default_code,
                    'image': self._get_image_url_dynamic(
                        model='product.product',
                        record_id=line.product_id.id,
                        field_name='image_1920'
                    )
                })
            response.update({
                'success': True,
                'customer_stock_id': stock_record.id,
                'lines': response_lines
            })

        except Exception as e:
            _logger.exception("Error in /api/v1/pre_sale_stock_confirm")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    @http.route('/api/v1/van_daily_collection_report', type='json', auth='none', methods=['POST'], csrf=False)
    def van_daily_collection_report(self, **kwargs):
        values = request.httprequest.json
        user_id = int(values.get('user_id'))
        worker_id = int(values.get('worker_id', 0))
        auth_token = values.get('auth_token')
        start_date_str = values.get('start_date')
        end_date_str = values.get('end_date')

        if not user_id or not auth_token:
            return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

        token = request.env['mobile.auth.token'].sudo().search([
            ('user_id', '=', user_id),
            ('mobile_app_auth_token', '=', auth_token)
        ], limit=1)

        if not token:
            return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

        result = {'data': [], 'total': 0.0}

        try:
            user = request.env['res.users'].sudo().browse(user_id)
            start_date = datetime.strptime(start_date_str, "%d-%m-%Y").date()
            end_date = datetime.strptime(end_date_str, "%d-%m-%Y").date()

            if worker_id != 0:
                worker_partner = request.env['res.partner'].sudo().browse(worker_id)
            else:
                worker_partner = user.partner_id



            # --- 3. Search RMAs (only those having a refund_id) for this responsible worker ---
            # (Assuming refund_id is a Many2one to account.move)
            rma_model = request.env['rma'].sudo()
            rmas = rma_model.search([
                ('responsible_worker_id', '=', worker_partner.id),
                ('refund_id', '!=', False),
                ('state', 'in', ['confirmed','refunded','finished','replaced','locked'])
            ])

            # --- 4. Collect all related refund moves & their payments efficiently ---
            refund_moves = rmas.mapped('refund_id')
            # We assume account.payment is linked via refund move (e.g., move_id on payment)
            # If your relation differs, adjust accordingly.
            payments = refund_moves.mapped('matched_payment_ids')
            # --- 5. Filter payments by date range (convert payment.date to date) ---
            # payment.date is typically a fields.Date (string), safe to compare after converting.
            try:
                filtered_payments = payments.filtered(
                    lambda p: (
                            p.date
                            and start_date <= (p.date if isinstance(p.date, date)
                                               else datetime.strptime(p.date, "%Y-%m-%d").date()) <= end_date
                            and p.state in ['paid','in_progress']
                            and p.responsible_id != False
                            and p.responsible_id and worker_partner and p.responsible_id == worker_partner.id

                    )
                )
            except:
                filtered_payments = []

            total = 0.0
            first_payment_ids = []


            for payment in filtered_payments:
                customer = payment.partner_id
                receipt_no = payment.move_id.name if payment.move_id else ''
                invoice_no = payment.memo if payment.memo else ''
                amount = (-1 * payment.amount) or 0.0
                total += amount

                access_token = payment._ensure_portal_token()
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                receipt_voucher_4inch_pdf_url = f"{base_url}/my/receipt_voucher_4inch_pdf/{payment.id}?access_token={access_token}&report_type=pdf&download=true"

                result['data'].append({
                    'customer_name': customer.name,
                    'code': customer.customer_code or '',
                    'receipt_no': receipt_no,
                    'invoice_no': invoice_no,
                    'payment_type': payment.journal_id.type.title(),
                    'amount': amount,
                    'receipt_voucher_4inch_pdf_url': receipt_voucher_4inch_pdf_url,
                })
                first_payment_ids.append(payment.id)

            payments = request.env['account.payment'].sudo().search([
                ('responsible_id', '=', worker_partner.id),
                ('state', 'in', ['paid','in_process']),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
            _logger.info("---------------------------------------------------------------")
            _logger.info(payments)
            _logger.info( worker_partner.id)
            _logger.info(start_date_str)
            _logger.info(end_date_str)
            _logger.info(start_date)
            _logger.info(end_date)
            _logger.info("end")
            _logger.info("-------------------------------------------------------------------")
            for payment in payments:
                if payment.id not in first_payment_ids:
                    customer = payment.partner_id
                    receipt_no = payment.move_id.name if payment.move_id else ''
                    invoice_no = payment.memo if payment.memo else ''
                    amount = payment.amount or 0.0
                    if payment.payment_type == 'outbound':
                        amount = amount * -1
                    total += amount

                    access_token = payment._ensure_portal_token()
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    receipt_voucher_4inch_pdf_url = f"{base_url}/my/receipt_voucher_4inch_pdf/{payment.id}?access_token={access_token}&report_type=pdf&download=true"


                    result['data'].append({
                        'customer_name': customer.name,
                        'code': customer.customer_code or '',
                        'receipt_no': receipt_no,
                        'invoice_no': invoice_no,
                        'payment_type': payment.journal_id.type.title(),
                        'amount': amount,
                        'receipt_voucher_4inch_pdf_url': receipt_voucher_4inch_pdf_url,
                    })

            result['total'] = f"{total:.2f} AED"
            return {
                'success': True,
                'data': result['data'],
                'total': result['total']
            }
            response.update({'success': True})

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/pre_sale_outstanding_invoices', type='json', auth='none', methods=['POST'])
    def pre_sale_outstanding_invoices(self, **kwargs):
        try:
            values = request.httprequest.json
            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token = values.get('auth_token')
            customer_id = int(values.get('customer_id', 0))

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "=", "not_paid")
            ]
            if customer_id:
                domain.append(("partner_id", "=", customer_id))

            invoices = request.env['account.move'].sudo().search(domain)

            invoice_list = []
            total_due = 0.0

            for inv in invoices:
                invoice_list.append({
                    'invoice_id': inv.id,
                    'invoice_name': inv.name,
                    'customer_reference': inv.partner_id.ref,
                    'invoice_date': inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                    'amount_total': inv.amount_total,
                    'currency': inv.currency_id.name,
                    'partner_id': inv.partner_id.id,
                    'partner_name': inv.partner_id.name,
                })
                total_due += inv.amount_residual

            if worker_id != 0:
                partner_id = request.env['res.partner'].sudo().browse(worker_id)
            else:
                partner_id = user.partner_id

            custodian_id = request.env['custodian'].sudo().search([("responsible_custodian","=", partner_id.id )], limit=1)
            account_journal_ids = []
            if custodian_id and custodian_id.journal_ids:
                account_journal_ids = custodian_id.journal_ids
            if not account_journal_ids:
                account_journal_ids = request.env['account.journal'].sudo().search([
                    ('is_pdc', '=', True)
                ])

            journals_list = []
            for journal in account_journal_ids:
                payment_method_list = []
                for inbound in custodian_id.inbound_payment_method_line_ids:
                    if inbound.journal_id.id == journal.id:
                        payment_method_list.append({"name": inbound.name, "id": inbound.id})
                journals_list.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                    'payment_methods': payment_method_list,
                })


            bank = request.env['res.bank'].sudo().search([])
            bank_data = bank.read(['id', 'name'])
            if not bank.exists():
                return {'success': False, 'error_msg': 'Invalid bank ID.'}

            return {
                'success': True,
                'count': len(invoice_list),
                'total_due': total_due,
                'trx_date': date.today(),
                'invoices': invoice_list,
                'account_journal': journals_list,
                'bank':bank_data,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/outstanding_invoices")
            return {'success': False, 'error_msg': str(e)}

    @http.route('/api/v1/pre_saleoutstanding_confirm_invoice_payment', type='json', auth='none', methods=['POST'],
                csrf=False)
    def pre_saleoutstanding_confirm_invoice_payment(self, **kwargs):
        try:
            values = request.httprequest.json

            user_id = int(values.get('user_id', 0))
            worker_id = int(values.get('worker_id', 0))
            auth_token = values.get('auth_token')
            invoice_ids = values.get('invoice_ids', [])
            journal_id = values.get('journal_id')
            payment_date = values.get('payment_date') or fields.Date.today()
            paid_amount = float(values.get('paid_amount', 0))
            memo = values.get('memo', '')
            fsm_order_id = values.get('fsm_order_id')
            customer_id = values.get('customer_id')

            payment_method_id = values.get('payment_method_id')
            cheque_number = values.get('cheque_number')
            cheque_date = values.get('cheque_date')
            cheque_pic = values.get('cheque_pic')
            bank_id = values.get('bank_id')
            note = values.get('note')

            if not user_id or not auth_token:
                return {'success': False, 'error_msg': 'Missing user ID or auth token.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user ID.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            # Validate partner
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid partner ID.'}

            # Get valid invoices
            invoices = request.env['account.move'].sudo().browse(invoice_ids).filtered(lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted' and inv.payment_state != 'paid')
            if not invoices:
                return {'success': False, 'error_msg': 'No valid unpaid invoices found.'}

            partner_ids = invoices.mapped('partner_id.id')
            if len(set(partner_ids)) > 1:
                return {'success': False, 'error_msg': 'Invoices belong to different customers.'}

            company_id = invoices[0].company_id.id


            journal = request.env['account.journal'].sudo().browse(journal_id)
            if not journal.exists():
                return {'success': False, 'error_msg': 'Invalid journal ID.'}
            if journal.company_id.id != company_id:
                return {'success': False, 'error_msg': 'Journal company does not match invoice company.'}
            if journal.type not in ['bank', 'cash']:
                return {'success': False, 'error_msg': 'Only bank and cash journals are allowed.'}
            payment_method_line = None
            if payment_method_id:
                candidate_method = request.env['account.payment.method.line'].sudo().browse(payment_method_id)
                if candidate_method and candidate_method in journal.inbound_payment_method_line_ids:
                    payment_method_line = candidate_method
                else:
                    return {'success': False, 'error_msg': 'Invalid or mismatched payment method for this journal.'}
            else:
                available_method = journal.inbound_payment_method_line_ids.filtered(
                    lambda m: m.payment_method_id.code == 'manual'
                )
                if not available_method:
                    return {'success': False,
                            'error_msg': 'No valid manual payment method line found for this journal.'}
                payment_method_line = available_method[0]


            fsm = request.env['fsm.order'].sudo().browse(fsm_order_id)
            fsm_name = fsm.name if fsm.exists() else 'NO-FSM'

            ctx = {
                'active_model': 'account.move.line',
                'active_ids': invoices.line_ids.ids,
                'company_id': company_id,
                'allowed_company_ids': [company_id],
                'visit_id': fsm_order_id
            }

            if worker_id != 0:
                worker_partner = request.env['res.partner'].sudo().browse(worker_id)
            else:
                worker_partner = user.partner_id

            payment_vals = {
                'partner_id': partner.id,
                'journal_id': journal.id,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'payment_date': payment_date,
                'communication': memo or 'PRE SALES/' + fsm_name + '/' + fields.Date.today().strftime(
                    '%Y/%m/%d') + '/' + str(random.randint(1000, 9999)),
                'responsible_id': worker_partner.id,
                'payment_method_line_id': payment_method_line.id,
                'currency_id': user.company_id.currency_id.id,
                'group_payment': True,
                'pdc_bank_id': bank_id,
            }

            real_payment_vals = {}
            if cheque_number:
                real_payment_vals['pdc_ref'] = cheque_number
            if bank_id:
                real_payment_vals['pdc_bank_id'] = bank_id
            if note:
                real_payment_vals['pdc_payable_note'] = note
            if cheque_pic:
                real_payment_vals['cheque_scanning'] = cheque_pic
            if payment_method_line:
                real_payment_vals['payment_method_line_id'] = payment_method_line.id

            payment_wiz = request.env['account.payment.register'].sudo().with_context(**ctx).create(payment_vals)
            payments = False
            for one_payment in payment_wiz:
                payments = one_payment.sudo().with_user(SUPERUSER_ID).with_context(**ctx)._create_payments()
                if not payments:
                    return {'success': False, 'error_msg': 'Payment creation failed.'}
                payments.sudo().write(real_payment_vals)
                payments.sudo().action_validate()


                fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)
                linked_lines = [(4, line.id) for line in invoices.line_ids]
                fsm_order.sudo().write({'invoice_lines': linked_lines})


            for inv in invoices:
                payment_lines = payments.mapped('move_id').line_ids.filtered(
                    lambda l: l.account_id.id in inv.line_ids.mapped('account_id').ids)
                inv_lines = inv.line_ids.filtered(lambda l: l.account_id.account_type in ('receivable', 'payable'))
                (payment_lines + inv_lines).filtered(lambda l: not l.reconciled).reconcile()

            updated_invoices = [{
                'invoice_id': inv.id,
                'invoice_name': inv.name,
                'payment_state': inv.payment_state,
                'residual_amount': inv.amount_residual,
                'currency': inv.currency_id.name
            } for inv in invoices]

            return {
                'success': True,
                'payment_id': [p.id for p in payments],
                'payment_name': [p.name for p in payments],
                'amount': [p.amount for p in payments],
                'currency': [p.currency_id.name for p in payments],
                'message': 'Payment successfully processed.',
                'invoices': updated_invoices
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/pre_saleoutstanding_confirm_invoice_payment: %s", str(e))
            return {'success': False, 'error_msg': 'System error occurred while processing payment.'}

    @http.route('/api/v1/create_merchandise_shelf_display', type='json', auth='none', methods=['POST'])
    def merchandise_create_shelf_display(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            customer_id = int(values.get('customer_id', 0))
            display_area_id = int(values.get('display_area_id', 0))
            visit_id = int(values.get('visit_id', 0))
            worker_id = int(values.get('worker_id', 0))
            activity_date = int(values.get('activity_date', 0))
            shelf_display_id = int(values.get('shelf_display_id', 0))
            date = activity_date if activity_date else fields.Datetime.now()

            products = values.get('products', [])


            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}


            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}


            partner = request.env['res.partner'].sudo().browse(customer_id)
            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            worker = request.env['res.partner'].sudo().search([('id', '=', worker_id), ('contact_type', '=', 'worker'), ('fsm_person', '=', True)])
            if not worker.exists():
                return {'success': False, 'error_msg': 'Invalid worker ID or Worker is not define!!'}


            display_area = request.env['display.area'].sudo().browse(display_area_id)
            if not display_area.exists():
                return {'success': False, 'error_msg': 'Invalid display area ID.'}

            create_vals = {
                'create_uid': user_id,
                'customer_id': customer_id,
                'display_area_id': display_area_id,
                'visit_id': visit_id,
                'worker_id': worker_id,
                'date': date
            }

            if shelf_display_id:
                shelf_display = request.env['shelf.display'].sudo().browse(shelf_display_id)
            else:
                shelf_display = request.env['shelf.display'].sudo().create(create_vals)



            product_lines = []
            for item in products:
                product_id = item.get('product_id')
                old_qty = item.get('old_qty', 0)
                current_qty = item.get('quantity', 0)

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    continue
                # line = {}
                # if shelf_display.line_ids:
                #     for rec in shelf_display.line_ids:
                #         if rec.product_id.id == product_id:
                #             rec.current_qty = current_qty
                #         else:
                #             line = (0, 0, {
                #                 'product_id': product.id,
                #                 'item_name': product.name,
                #                 'uom_id': product.uom_id.id,
                #                 # 'old_qty': old_qty,
                #                 'current_qty': current_qty,
                #             })
                #         product_lines.append(line)
                # else:
                line = (0, 0, {
                    'product_id': product.id,
                    'item_name': product.name,
                    'uom_id': product.uom_id.id,
                    # 'old_qty': old_qty,
                    'current_qty': current_qty,
                })
                product_lines.append(line)

            shelf_display.sudo().write({'line_ids': product_lines})

            response_lines = []
            for line in shelf_display.line_ids:
                response_lines.append({
                    'product_id': line.product_id.id,
                    'item_name': line.product_id.name,
                    # 'barcode': line.product_id.barcode,
                    'uom': line.product_id.uom_id.name,
                    # 'uom_id': line.product_id.uom_id.id,
                    'old_qty': line.old_qty,
                    'current_qty': line.current_qty
                })
            response.update({
                'success': True,
                'shelf_display_id': shelf_display.id,
                'lines': response_lines
            })



        except Exception as e:
            _logger.exception("Error in /api/v1/create_merchandise_shelf_display")
            return {'success': False, 'error_msg': str(e)}

        return response

    # mechandise_stock_count

    @http.route('/api/v1/get_worker_display_area', type='json', auth='none', methods=['POST'], csrf=False)
    def merchandise_get_worker_display_area(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id'))
            auth_token = values.get('auth_token')

            token_valid = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token_valid:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            display_area = request.env['display.area'].sudo().search([])
            display_area = [{'id':rec.id, 'name': rec.name} for rec in display_area]
            response.update({
                'success': True,
                'display_area': display_area

            })

        except Exception as e:
            _logger.exception("Error in /api/v1/pre_sale_stock_count")
            response.update({'success': False, 'error_msg': str(e)})

        return response

    @http.route('/api/v1/confirm_shelf_display', type='json', auth='none', methods=['POST'], csrf=False)
    def merchandise_confirm_shelf_dispaly(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            customer_id = int(values.get('customer_id', 0))
            display_area_id = int(values.get('display_area_id', 0))
            visit_id = int(values.get('visit_id', 0))
            activity_date = int(values.get('activity_date', 0))
            # shelf_display_id = int(values.get('shelf_display_id', 0))
            date = activity_date if activity_date else fields.Datetime.now()

            products = values.get('products', [])

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            partner = request.env['res.partner'].sudo().browse(customer_id)
            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            worker = user.partner_id
            if not worker.exists():
                return {'success': False, 'error_msg': 'Invalid worker ID or Worker is not define!!'}

            display_area = request.env['display.area'].sudo().browse(display_area_id)
            if not display_area.exists():
                return {'success': False, 'error_msg': 'Invalid display area ID.'}

            create_vals = {
                'create_uid': user_id,
                'customer_id': customer_id,
                'display_area_id': display_area_id,
                'visit_id': visit_id,
                'worker_id': worker.id,
                'date': date
            }

            shelf_display = request.env['shelf.display'].sudo().create(create_vals)

            product_lines = []
            for item in products:
                product_id = item.get('product_id')
                current_qty = item.get('quantity', 0)

                product = request.env['product.product'].sudo().search([('id', '=', int(product_id)), ('active', '=', True)])
                # product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    continue

                line = (0, 0, {
                    'product_id': product.id,
                    'item_name': product.name,
                    'uom_id': product.uom_id.id,
                    # 'old_qty': old_qty,
                    'current_qty': current_qty,
                })
                product_lines.append(line)

            shelf_display.sudo().write({'line_ids': product_lines})

            response_lines = []
            for line in shelf_display.line_ids:
                response_lines.append({
                    'product_id': line.product_id.id,
                    'item_name': line.product_id.name,
                    'barcode': line.product_id.barcode,
                    'uom': line.product_id.uom_id.name,
                    'uom_id': line.product_id.uom_id.id,
                    'old_qty': line.old_qty,
                    'current_qty': line.current_qty,
                })
            response.update({
                'success': True,
                'shelf_display_id': shelf_display.id,
                'lines': response_lines
            })



        except Exception as e:
            _logger.exception("Error in /api/v1/confirm_shelf_display")
            return {'success': False, 'error_msg': str(e)}

        return response

    @http.route('/api/v1/confirm_stock_request', type='json', auth='none', methods=['POST'], csrf=False)
    def confirm_stock_request(self, **kwargs):
        values = request.httprequest.json or {}
        try:
            user_id = int(values.get('user_id') or 0)
            auth_token = values.get('auth_token')
            # Can be a stock.request.order id OR a stock.request id (line)
            any_id = int(values.get('id') or values.get('stock_request_id') or 0)

            # -------- Basic checks --------
            if not user_id or not auth_token or not any_id:
                return {'success': False, 'error_msg': 'Missing user_id, auth_token, or id.'}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': 'Invalid user.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            # -------- Resolve the stock request ORDER from the id you send --------
            StockRequestOrder = request.env['stock.request.order'].sudo()
            StockRequestLine = request.env['stock.request'].sudo()

            stock_req_order = StockRequestOrder.browse(any_id)
            if not stock_req_order.exists():
                # maybe they sent a stock.request line id; climb to its parent order
                line = StockRequestLine.browse(any_id)
                if not line.exists():
                    return {'success': False, 'error_msg': 'Stock Request (order/line) not found.'}
                # parent field can vary by module; try common names
                stock_req_order = (getattr(line, 'stock_request_order_id', False)
                                   or getattr(line, 'request_order_id', False)
                                   or getattr(line, 'order_id', False))
                if not stock_req_order or not stock_req_order.exists():
                    return {'success': False, 'error_msg': 'Parent Stock Request Order not found from line.'}

            # -------- Identify the driver partner & van location (same partner) --------
            # Using the API user’s partner; customize if you want customer-based instead:
            partner = user.partner_id
            van_loc = getattr(partner, 'van_location', False)
            van_loc_id = van_loc.id if van_loc else False
            if not van_loc_id:
                return {'success': False, 'error_msg': 'No van location configured for this partner.'}

            # -------- Find the target picking for THIS stock request order --------
            # We’ll only consider pickings attached to this request order
            pickings = stock_req_order.picking_ids

            # Condition: location_dest_id == partner’s van location AND state == 'assigned'
            candidates = pickings.filtered(
                lambda p: (p.state == 'assigned')
                          and p.location_dest_id
                          and p.location_dest_id.id == van_loc_id
                # optional: also check same partner if you want it stricter
                # and (not p.partner_id or p.partner_id.id == partner.id)
            )

            if not candidates:
                return {
                    'success': False,
                    'error_msg': 'No assigned picking found for this request with destination = van location.'
                }

            # choose one (usually there is one)
            picking = candidates[0].sudo()

            # -------- Validate the picking --------
            # button_validate may return a wizard action (immediate/backorder).
            # action = picking.with_context(skip_overprocessed_check=True).button_validate()
            picking.sudo().write({"van_approve_load_api": True})

            def _auto_confirm_picking_wizards(action_dict, picking, acting_user):
                """
                Follows any wizard actions returned by button_validate and confirms them automatically.
                Ensures expected context keys (e.g., default_lot_ids) exist for the expiry wizard.
                """
                WIZ_METHODS = {
                    'expiry.picking.confirmation': 'process',  # your custom / product_expiry wizard
                    'stock.immediate.transfer': 'process',  # standard
                    'stock.backorder.confirmation': 'process_cancel_backorder',
                    # or 'process_cancel_backorder' to skip backorders
                }

                max_hops = 5
                while isinstance(action_dict, dict) and action_dict.get(
                        'type') == 'ir.actions.act_window' and max_hops > 0:
                    res_model = action_dict.get('res_model')
                    method = WIZ_METHODS.get(res_model, 'process_cancel_backorder')

                    # 1) Build a safe context
                    ctx = dict(action_dict.get('context') or {})
                    ctx.update({
                        'active_model': 'stock.picking',
                        'active_id': picking.id,
                        'active_ids': [picking.id],
                    })

                    # 2) Ensure the keys this wizard expects exist
                    if res_model in ('expiry.picking.confirmation', 'confirm.expiry'):
                        # If the action didn't supply default_lot_ids, derive or at least set empty.
                        # ctx.setdefault('default_lot_ids', _expired_lot_cmds(picking))
                        # Optional niceties – some implementations read these:
                        ctx.setdefault('default_show_lots', bool(ctx['default_lot_ids']))
                        ctx.setdefault('default_description', 'Auto-confirmed from API')

                    WizardEnv = request.env[res_model].with_context(ctx).with_user(acting_user).sudo()
                    res_id = action_dict.get('res_id')
                    wiz = WizardEnv.browse(res_id) if res_id else WizardEnv.create({})

                    # 3) Call the wizard method. If it still complains about missing keys, retry with hard-safe defaults.
                    try:
                        action_dict = getattr(wiz, method)() or None
                    except KeyError as ke:
                        # Safety net: some custom code does ctx.pop('default_lot_ids') with no default.
                        if str(ke) == "'default_lot_ids'":
                            WizardEnv = WizardEnv.with_context(
                                {**WizardEnv.env.context, 'default_lot_ids': []})
                            wiz = WizardEnv.browse(res_id) if res_id else WizardEnv.create({})
                            action_dict = getattr(wiz, method)() or None
                        else:
                            raise
                    max_hops -= 1

                return True

            action = picking.sudo().with_user(user.id).with_context(mail_create_nosubscribe=True).button_validate()

            # Try auto-accept immediate transfer / backorder if a wizard pops
            try:
                if isinstance(action, dict) and action.get('type') == 'ir.actions.act_window':
                    _auto_confirm_picking_wizards(action, picking, user)
                # if isinstance(action, dict):
                #     model = action.get('res_model')
                #     res_id = action.get('res_id')
                #     if model == 'stock.immediate.transfer' and res_id:
                #         wiz = request.env[model].sudo().browse(res_id)
                #         if wiz.exists():
                #             wiz.process()
                #     elif model == 'stock.backorder.confirmation' and res_id:
                #         wiz = request.env[model].sudo().browse(res_id)
                #         if wiz.exists():
                #             # if you want to force "no backorder", call .process_cancel_backorder()
                #             wiz.process()  # confirm backorder creation
            except Exception as e:
                # If any wizard auto-processing fails, we still continue and report the validate call.
                _logger.info("back order issue %s" %(e))

            picking_state_after = picking.state

            return {
                'success': True,
                'message': f"Picking {picking.name} validated.",
                'picking_id': picking.id,
                'picking_state': picking_state_after,
                'stock_request_order_id': stock_req_order.id,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/confirm_stock_request")
            return {'success': False, 'error_msg': str(e)}

    # @http.route('/api/v1/confirm_stock_request', type='json', auth='none', methods=['POST'], csrf=False)
    # def confirm_stock_request(self, **kwargs):
    #     response = {}
    #     values = request.httprequest.json or {}
    #     try:
    #         user_id = values.get('user_id')
    #         auth_token = values.get('auth_token')
    #         req_id = values.get('id')
    #
    #         user = request.env['res.users'].sudo().browse(user_id)
    #         if not user.exists() or not auth_token:
    #             return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}
    #
    #         token = request.env['mobile.auth.token'].sudo().search([
    #             ('user_id', '=', user_id),
    #             ('mobile_app_auth_token', '=', auth_token)
    #         ], limit=1)
    #
    #         if not token:
    #             return {'success': False, 'error_msg': 'Invalid or expired auth token.'}
    #
    #         stock_req = request.env['stock.request.order'].sudo().browse(req_id)
    #         if not stock_req:
    #             return {'success': False, 'error_msg': 'Stock Request not found.'}
    #
    #         stock_req.action_van_load_done()
    #
    #         response.update({
    #             'success': True,
    #             'message': f"Stock request '{stock_req.name}' has been successfully confirmed."
    #         })
    #
    #     except Exception as e:
    #         _logger.exception("Error in /api/v1/confirm_shelf_display")
    #         return {'success': False, 'error_msg': str(e)}
    #
    #     return response

    @http.route('/api/v1/transaction_history', type='json', auth='none', methods=['POST'], csrf=False)
    def transaction_history(self, **kwargs):
        values = request.httprequest.json or {}
        user_id       = values.get('user_id')
        auth_token    = values.get('token')
        start_str     = values.get('start_date')
        end_str       = values.get('end_date')
        worker_id     = values.get('worker_id')

        # 1) Basic validation
        if not user_id or not auth_token:
            return {
                'success': False,
                'error_msg': 'Missing required fields: user_id, token, and end_date are mandatory.'
            }

        # 2) Authenticate token
        token = request.env['mobile.auth.token'].sudo().search([
            ('user_id', '=', int(user_id)),
            ('mobile_app_auth_token', '=', auth_token)
        ], limit=1)
        if not token:
            return {'success': False, 'error_msg': 'Invalid or expired token.'}

        # 3) Parse dates
        fmt = "%d-%m-%Y"
        try:
            end_date = datetime.strptime(end_str, fmt).date() if end_str else None
            start_date = datetime.strptime(start_str, fmt).date() if start_str else None
        except Exception:
            return {'success': False, 'error_msg': 'Dates must be in DD-MM-YYYY format.'}

        # 4) Helper to safe-get attributes
        def sg(record, field, default=''):
            return getattr(record, field, default) or default

        # 5) Fetch records
        try:
            user = request.env['res.users'].sudo().browse(int(user_id))
            my_partner = 0
            if worker_id:
                my_partner = request.env['res.partner'].sudo().browse(worker_id)
            if user.user_type != 'sales_user' and worker_id:
                partner_domain = [('assign_to', '=', my_partner.id)]
                rma_domain = [('responsible_worker_id','=', my_partner.id)]
            else:
                partner_domain = [('assign_to', '=', user.partner_id.id)]
                rma_domain = [('responsible_worker_id','=', user.partner_id.id)]
            date_domain = []
            van_domain = [('customer_id','=',user.partner_id.id),('direction','in',['van_load','van_off_load'])]
            if start_date and end_date:
                date_domain.append(('date_order', '>=', start_date))
                van_domain.append(('expected_date', '>=', start_date))
                date_domain.append(('date_order', '<=', end_date))
                van_domain.append(('expected_date', '<=', end_date))
            elif start_date:
                date_domain.append(('date_order', '>=', start_date))
                van_domain.append(('expected_date', '>=', start_date))
            elif end_date:
                date_domain.append(('date_order', '<=', end_date))
                van_domain.append(('expected_date', '<=', end_date))

            # Sale Orders
            sale_orders = request.env['sale.order'].sudo().search(partner_domain + date_domain)
            stock_requests = request.env['stock.request.order'].sudo().search(van_domain)
            so_data = []
            van_load = []
            van_off_load = []

            for stock_request in stock_requests:
                if stock_request.direction == 'van_load':
                    # --- New logic for to_confirm ---
                    # Resolve van location id (supports both worker-based and user-based)
                    van_loc = (my_partner and getattr(my_partner, 'van_location', False)) or getattr(user.partner_id,
                                                                                                     'van_location',
                                                                                                     False)
                    van_loc_id = van_loc.id if van_loc else False

                    picks = stock_request.picking_ids

                    # 1) Find if there is a van picking (source == van location) in 'assigned' (ready)
                    van_pick_assigned = any(
                        (p.location_dest_id and p.location_dest_id.id == van_loc_id) and p.state == 'assigned'
                        for p in picks
                    )

                    # 2) All OTHER pickings (those not sourced from van location) must be done
                    others_done = all(
                        p.state == 'done'
                        for p in picks
                        if not (p.location_dest_id and p.location_dest_id.id == van_loc_id)
                    )

                    # 3) Stock request must be open
                    is_open = (sg(stock_request, 'state') == 'open')

                    to_confirm = bool(is_open and van_pick_assigned and others_done)

                    # --- existing payload unchanged below ---
                    van_load.append({
                        'id': stock_request.id,
                        'name': stock_request.name,
                        'customer_id': stock_request.customer_id.name,
                        'expected_date': sg(stock_request, 'expected_date'),
                        'picking_policy': sg(stock_request, 'picking_policy'),
                        'direction': sg(stock_request, 'direction'),
                        'warehouse_id': sg(stock_request.warehouse_id, 'id'),
                        'remarks': sg(stock_request, 'remarks'),
                        'route_id': sg(stock_request.route_id, 'id'),
                        'state': [sg(stock_request, 'state'),
                                  dict(stock_request._fields['state'].selection).get(stock_request.state)],
                        'to_confirm': to_confirm,
                        'picking_ids': [
                            {
                                'id': pick.id,
                                'name': pick.name,
                                'delivery_address': sg(pick.partner_id, 'name'),
                                'state': pick.state,
                                'status_label': dict(pick._fields['state'].selection).get(pick.state),
                                'trx_type': sg(pick, 'picking_type_code'),
                                'driver': sg(pick, 'driver_id'),
                                'forklift': sg(pick, 'forklift_id'),
                                'date': sg(pick, 'date_done'),
                                'schedule_date': sg(pick, 'scheduled_date'),
                                'delivery_planned_date': sg(pick, 'scheduled_date'),
                                'move_ids_without_package': [
                                    {
                                        'id': mv.id,
                                        'product_id': mv.product_id.id,
                                        'product_name': mv.product_id.name,
                                        'division': sg(mv.product_id, 'division'),
                                        'product_packaging_id': mv.product_packaging_id.id,
                                        'quantity': mv.product_qty,
                                        'uom': mv.product_uom_qty,
                                        'state': mv.state,
                                        'status_label': dict(pick._fields['state'].selection).get(mv.state),
                                    }
                                    for mv in pick.move_ids_without_package
                                ],
                            }
                            for pick in stock_request.picking_ids
                        ],
                        'stock_request_ids': [
                            {
                                'id': stock_request_id.id,
                                'name': stock_request_id.name,
                                'product_id': stock_request_id.product_id.name,
                                'product_packaging_id': sg(stock_request_id, 'product_packaging_id', 'id'),
                                'product_packaging_qty': stock_request_id.product_packaging_qty,
                                'available_qty': stock_request_id.available_qty,
                                'product_uom_id': sg(stock_request_id.product_uom_id, 'id'),
                                'product_uom_qty': stock_request_id.product_uom_qty,
                                'qty_in_progress': stock_request_id.qty_in_progress,
                                'qty_done': stock_request_id.qty_done,
                                'remarks': stock_request_id.remarks,
                                'state': sg(stock_request_id, 'state'),
                            }
                            for stock_request_id in stock_request.stock_request_ids
                        ]
                    })

                if stock_request.direction == 'van_off_load':
                    van_off_load.append({
                        'id': stock_request.id,
                        'name': stock_request.name,
                        'customer_id': stock_request.customer_id.name,
                        'expected_date': sg(stock_request, 'expected_date'),
                        'picking_policy': sg(stock_request, 'picking_policy'),
                        'direction': sg(stock_request, 'direction'),
                        'warehouse_id': sg(stock_request.warehouse_id, 'id'),
                        'remarks': sg(stock_request, 'remarks'),
                        'route_id': sg(stock_request.route_id, 'id'),
                        'state':[sg(stock_request,'state'),dict(stock_request._fields['state'].selection).get(stock_request.state)],
                        'stock_request_ids': [
                            {
                                'id': stock_request_id.id,
                                'name': stock_request_id.name,
                                'product_id': stock_request_id.product_id.name,
                                'product_packaging_id': sg(stock_request_id.product_packaging_id, 'id'),
                                'product_packaging_qty': stock_request_id.product_packaging_qty,
                                'available_qty': stock_request_id.available_qty,
                                'product_uom_id': sg(stock_request_id.product_uom_id, 'id'),
                                'product_uom_qty': stock_request_id.product_uom_qty,
                                'qty_in_progress': stock_request_id.qty_in_progress,
                                'qty_done': stock_request_id.qty_done,
                                'remarks': stock_request_id.remarks or '' ,
                                'state': sg(stock_request_id, 'state'),
                            }
                            for stock_request_id in stock_request.stock_request_ids
                        ],
                        'picking_ids': [
                            {
                                'id': pick.id,
                                'name': pick.name,
                                'delivery_address': sg(pick.partner_id, 'name'),
                                'state': pick.state,
                                'status_label': dict(pick._fields['state'].selection).get(pick.state),
                                'trx_type': sg(pick, 'picking_type_code'),
                                'driver': sg(pick, 'driver_id'),
                                'forklift': sg(pick, 'forklift_id'),
                                'date': sg(pick, 'date_done'),
                                'schedule_date': sg(pick, 'scheduled_date'),
                                'delivery_planned_date': sg(pick, 'scheduled_date'),
                                'move_ids_without_package': [
                                    {
                                        'id': mv.id,
                                        'product_id': mv.product_id.id,
                                        'product_name': mv.product_id.name,
                                        'division': sg(mv.product_id, 'division'),
                                        'product_packaging_id': mv.product_packaging_id.id,
                                        'quantity': mv.product_qty,
                                        'uom': mv.product_uom_qty,
                                        'state': mv.state,
                                        'status_label': dict(mv._fields['state'].selection).get(mv.state),
                                    }
                                    for mv in pick.move_ids_without_package
                                ],
                            }
                            for pick in stock_request.picking_ids
                        ],
                    })

            for so in sale_orders:
                picks = []
                can_be_cancelled = True
                delivery_status = False
                for pick in so.picking_ids:
                    delivery_status = pick.state
                    if pick.state == 'done':
                        can_be_cancelled = False
                    picks.append({
                        'id': pick.id,
                        'name': pick.name,
                        'delivery_address': sg(pick.partner_id, 'name'),
                        'state': pick.state,
                        'status_label': pick.state,
                        'trx_type': sg(pick, 'picking_type_code'),
                        'driver': sg(pick, 'driver_id'),
                        'forklift': sg(pick, 'forklift_id'),
                        'date': sg(pick, 'date_done'),
                        'schedule_date': sg(pick, 'scheduled_date'),
                        'delivery_planned_date': sg(pick, 'scheduled_date'),
                        'move_ids_without_package': [
                            {
                                'id': mv.id,
                                'product_id': mv.product_id.id,
                                'product_name': mv.product_id.name,
                                'division': sg(mv.product_id, 'division'),
                                'product_packaging_id': mv.product_packaging_id.id,
                                'quantity': mv.product_qty,
                                'uom': mv.product_uom_qty,
                            }
                            for mv in pick.move_ids_without_package
                        ],
                    })

                invs = []
                invoice_status = False
                for inv in so.invoice_ids:
                    can_be_cancelled = False
                    invs.append({
                        'id': inv.id,
                        'name': inv.name,
                        'customer_id': inv.partner_id.id,
                        'customer_name': inv.partner_id.name,
                        'customer_code': sg(inv.partner_id, 'customer_code'),
                        'remark': sg(inv, 'comment'),
                        'po_number': sg(inv, 'po_number'),
                        'voucher_number': inv.name,
                        'reference': sg(inv, 'reference'),
                        'state': sg(inv, 'state'),
                        'invoice_line_ids': [
                            {
                                'id': ln.id,
                                'product_id': ln.product_id.id,
                                'product_name': ln.product_id.name,
                                'quantity': ln.quantity,
                                'price_unit': ln.price_unit,
                            }
                            for ln in inv.invoice_line_ids
                        ]
                    })
                    invoice_status = inv.state

                print("Inside SLA EODER API:", so.id)
                access_token = so._ensure_portal_token()
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{so.id}?access_token={access_token}&report_type=pdf&download=true"



                so_data.append({
                    'customer_id': so.partner_id.id,
                    'customer_name': so.partner_id.name,
                    'id': so.id,
                    'name': so.name,
                    'ref': sg(so, 'client_order_ref'),
                    'customer_channel': sg(so, 'so.customer_partner_channel'),
                    'outlet_code': so.partner_id.outlet_code,
                    'outlet_short_name': sg(so, 'outlet_short_name'),
                    'client_order_ref': sg(so, 'client_order_ref'),
                    'order_date': sg(so, 'date_order'),
                    'warehouse_id': sg(so, 'warehouse_id').id if so.warehouse_id else 0,
                    'order_type': sg(so, 'order_type'),
                    'remarks': sg(so, 'remarks'),
                    'po_number': sg(so, 'po_number'),
                    'po_date': sg(so, 'po_date'),
                    'commitment_date': sg(so, 'commitment_date'),
                    'delivery_status': delivery_status if delivery_status else sg(so, 'delivery_status'),
                    'payment_term_id': sg(so, 'payment_term_id').id if so.payment_term_id else "",
                    'fsm_order_id': sg(so, 'fsm_order_id').id if sg(so, 'fsm_order_id') else '',
                    'amount_paid': sg(so, 'amount_paid'),
                    'amount_invoiced': sg(so, 'amount_invoiced'),
                    'amount_delivered': sg(so, 'amount_delivered'),
                    'amount_tax': sg(so, 'amount_tax'),
                    'amount_total': sg(so, 'amount_total'),
                    'invoice_status': invoice_status if invoice_status else sg(so, 'invoice_status'),
                    'picking_ids': picks,
                    'invoice_ids': invs,
                    'reward_amount': sg(so, 'reward_amount'),
                    'state': sg(so, 'state'),
                    'type_name': sg(so, 'type_name'),
                    'tax_invoice_4inch_pdf_url': tax_invoice_4inch_pdf_url,
                    'can_be_cancelled': can_be_cancelled,
                    'order_line': [
                        {
                            'id': ol.id,
                            'product_id': ol.product_id.id,
                            'product_name': ol.product_id.name,
                            'quantity': ol.product_uom_qty,
                            'division': ol.division,
                            'execise_price': ol.exercise_price,
                            'price_unit': ol.price_unit,
                            'discount': ol.discount,
                            'price_subtotal': ol.price_subtotal,
                        }
                        for ol in so.order_line
                    ]
                })

            # RMAs
            date_domain_rma = []
            if start_date and end_date:
                date_domain_rma += [('date', '>=', start_date), ('date', '<=', end_date)]
            elif start_date:
                date_domain_rma += [('date', '>=', start_date)]
            elif end_date:
                date_domain_rma += [('date', '<=', end_date)]
            rmas = request.env['rma'].sudo().search(rma_domain + date_domain_rma)
            rma_data = []
            for r in rmas:
                tax_credit_4inch_pdf_url = ''
                if r.refund_id:
                    print("Inside SLA EODER API:", r.id)
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    access_token = r.refund_id._ensure_portal_token()
                    tax_credit_4inch_pdf_url = f"{base_url}/my/tax_credit_4inch_pdf/{r.refund_id.id}?access_token={access_token}&report_type=pdf&download=true"


                rma_data.append({
                    'channel': sg(r, 'channel'),
                    'collection_request_date': sg(r, 'collection_request_date'),
                    'customer_account': sg(r, 'customer_account'),
                    'date': sg(r, 'date'),
                    'deadline': sg(r, 'deadline'),
                    'delivered_qty': sg(r, 'delivred_qty'),
                    'division': sg(r, 'division'),
                    'grv_amount': r.grv_amount,
                    'grv_no': sg(r, 'grv_no'),
                    'line_ids': [
                        {
                            'id': ln.id,
                            'product_id': ln.product_id.id,
                            'product_name': ln.product_id.name,
                            'quantity': ln.product_uom_qty,
                        }
                        for ln in r.line_ids
                    ],
                    'location_id': sg(r.location_id, 'id'),
                    'name': r.name,
                    'operation_id': sg(r.operation_id, 'id'),
                    'outlet_name': sg(r, 'outlet_name'),
                    'partner_id': sg(r.partner_id, 'id'),
                    'partner_name': sg(r.partner_id, 'name'),
                    'picking_id': sg(r.picking_id, 'id'),
                    'product_line_ids': [
                        {
                            'id': pl.id,
                            'product_id': pl.product_id.id,
                            'product_name': pl.product_id.name,
                            'quantity': pl.product_uom_qty,
                        }
                        for pl in r.product_line_ids
                    ],
                    'refund_id': sg(r.refund_id, 'id'),
                    'tax_credit_4inch_pdf_url': tax_credit_4inch_pdf_url,
                })

            return {
                'success': True,
                'sale_orders': so_data,
                'rma': rma_data,
                'van_load': van_load,
                'van_off_load': van_off_load,
            }

        except Exception as e:
            _logger.exception("Error in transaction_history")
            return {'success': False, 'error_msg': str(e)}
