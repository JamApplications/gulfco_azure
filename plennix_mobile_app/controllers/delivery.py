import requests
from pytz import country_timezones
from datetime import date, timedelta
from odoo import http
import imghdr
from odoo.fields import Command
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.addons.web.controllers.home import CREDENTIAL_PARAMS
from urllib.parse import parse_qs
from odoo.exceptions import UserError

SIGN_UP_PARAMS = ['name', 'login', 'password', 'confirm_password']
from odoo.http import content_disposition, request
import random
import string
import io
from PIL import Image
import base64
from datetime import datetime
import logging
from pytz import country_timezones
from datetime import datetime, timedelta, date


_logger = logging.getLogger("============API Authenticate========")

default_token_size = 16

class gulfcoMobileAPIdelivery(http.Controller):
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


    @http.route('/api/v1/dashboard_delivery', type='json', auth='none', methods=['POST'])
    def delivery_dashboard(self, **kwargs):
        response = {}
        values = request.httprequest.json
        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            user = request.env['res.users'].sudo().browse(user_id)
            worker_id = int(values.get('worker_id',0))
            picking_driver_id = user.partner_id.id
            if worker_id != 0:
                picking_driver_id = worker_id

            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)

            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            today = fields.Date.today()
            start_date = fields.Datetime.today()
            date_end = start_date.replace(hour=23, minute=59, second=59)


            pickings = request.env['stock.picking'].sudo().search([
                ('picking_driver_id', '=', picking_driver_id),
                ('picking_type_code', '=', 'outgoing'),
                ('delivery_planned_date', '>=', today),
                ('delivery_planned_date', '<=', today)
            ])
            sales_team_delivery = user.has_group('plnx_sales_team.group_sales_team_delivery')
            total_deliveries = len(pickings)
            completed_deliveries = pickings.filtered(lambda p: p.state == 'done')
            pending_deliveries = pickings.filtered(lambda p: p.state not in ['done', 'cancel'])
            sale_order_names = pickings.mapped('origin')
            sale_orders = request.env['sale.order'].sudo().search([
                ('name', 'in', sale_order_names),
                ('state', '=', 'sale'),
                ('date_order', '>=', start_date),
                ('date_order', '<=', date_end)
            ])
            total_sales = len(sale_orders)
            def get_trx_stats(pickings, trx_type):
                trx = pickings.filtered(lambda p: p.trx_type == trx_type)
                return {
                    'total': len(trx),
                    'completed': len(trx.filtered(lambda p: p.state == 'done')),
                    'pending': len(trx.filtered(lambda p: p.state not in ['done', 'cancel']))
                }
            response.update({
                'success': True,
                'data': {
                    'user_id': user.id,
                    'user_name': user.name,
                    'total_deliveries': total_deliveries,
                    'completed_deliveries': len(completed_deliveries),
                    'pending_deliveries': len(pending_deliveries),
                    'total_sales': total_sales,
                    'trx_stats': {
                        'trx_direct_delivery_order': get_trx_stats(pickings, 'direct_delivery_order'),
                        'trx_return_collection': get_trx_stats(pickings, 'return_collection'),
                        'trx_branch_delivery': get_trx_stats(pickings, 'branch_delivery'),
                        'trx_cross_docking_order': get_trx_stats(pickings, 'cross_docking_order'),
                        'trx_3pl_orders': get_trx_stats(pickings, '3pl_orders'),
                        'trx_sample': get_trx_stats(pickings, 'sample'),
                    }
                }
            })

        except Exception as e:
            response.update({
                'success': False, 'error_msg': str(e)})
            _logger.info('Failed to open the delivery dashboard.')

        return response

