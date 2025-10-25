# -*- coding: utf-8 -*-
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
from odoo.tools._vendor.send_file import send_file

_logger = logging.getLogger("============API Authenticate========")

default_token_size = 16


def _default_app_unique_key(size, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


class GulfcoMobileAppAPI(http.Controller):

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
