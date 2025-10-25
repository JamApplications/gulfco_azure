# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

import json
import logging
import requests
import urllib.parse
import secrets
import hashlib
import base64
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

DEFAULT_SCOPES = 'openid profile email offline_access'
POWERBI_SCOPES = ('https://analysis.windows.net/powerbi/api/Dashboard.Read.All '
                'https://analysis.windows.net/powerbi/api/Dataset.Read.All '
                'https://analysis.windows.net/powerbi/api/Report.Read.All ')

def generate_pkce_pair():
    code_verifier = secrets.token_urlsafe(64)[:128]  # RFC requires max length 128
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode('ascii')
    return code_verifier, code_challenge

def decode_jwt_payload(token):
    # Split the JWT into parts
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError('Invalid JWT token')

    # JWT payload is the second part
    payload_b64 = parts[1]

    # Add necessary padding (Base64url encoding can omit padding)
    padding = '=' * ((4 - len(payload_b64) % 4) % 4)
    payload_b64 += padding

    # Decode Base64url to JSON string
    payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')

    # Parse JSON string to dict
    return json.loads(payload_json)

class PowerBIOAuthController(http.Controller):

    @http.route('/powerbi/embed/oauth/login', auth='user', type='json')
    def powerbi_embed_oauth_login(self, **kw):
        client_id = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.client_id')
        tenant_id = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.tenant_id')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f'{base_url}/powerbi/embed/oauth/callback'
        scope = f'{DEFAULT_SCOPES} {POWERBI_SCOPES}'
        response_type = 'code'

        code_verifier, code_challenge = generate_pkce_pair()
        request.session.powerbi_embed_code_verifier = code_verifier

        auth_url = (
            f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize'
            f'?client_id={client_id}&response_type={response_type}&redirect_uri={urllib.parse.quote(redirect_uri)}'
            f'&response_mode=query&scope={urllib.parse.quote(scope)}&state=12345'
            f'&code_challenge={code_challenge}&code_challenge_method=S256'
        )
        return {'authUrl': auth_url}

    @http.route('/powerbi/embed/oauth/callback', auth='none', type='http')
    def powerbi_embed_oauth_callback(self, code=None, **kw):
        client_id = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.client_id')
        client_secret = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.client_secret')
        tenant_id = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.tenant_id')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f'{base_url}/powerbi/embed/oauth/callback'

        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        scope = f'{DEFAULT_SCOPES} {POWERBI_SCOPES}'
        code_verifier = request.session.powerbi_embed_code_verifier
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
            'code_verifier': code_verifier,
            'scope': scope
        }

        res = requests.post(token_url, data=token_data)
        token_response = res.json()

        request.session.powerbi_embed_code_verifier = False

        # Store access_token securely (session/db)
        self.store_pb_session_info(token_response)

        return request.redirect(self.get_pb_dashboard_action_url())

    @http.route('/powerbi/embed/oauth/refresh/token', auth='user', type='json')
    def powerbi_embed_oauth_refresh_token(self, **kw):
        if not request.session.powerbi_refresh_token:
            return {'Error': 'Refresh Token Not Found'}
        client_id = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.client_id')
        client_secret = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.client_secret')
        tenant_id = request.env['ir.config_parameter'].sudo().get_param('ek_powerbi_connector.tenant_id')

        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        scope = f'{DEFAULT_SCOPES} {POWERBI_SCOPES}'
        token_data = {
            'client_id': client_id,
            'scope': scope,
            'refresh_token': request.session.powerbi_refresh_token,
            'grant_type': 'refresh_token',
            'client_secret': client_secret,
        }
        res = requests.post(token_url, data=token_data) 
        token_response = res.json()
        if token_response.get('error'):
            return {'error': 'Error while refresh token'}

        self.store_pb_session_info(token_response)

        return {'success': {'response': token_response}}

    @http.route('/powerbi/embed/signout', auth='user', type='json')
    def powerbi_embed_signout(self, **kw):
        self.remove_pb_session_info()
        return True

    def remove_pb_session_info(self):
        request.session.powerbi_access_token = False
        request.session.powerbi_refresh_token = False
        request.session.powerbi_access_token_info = False
        request.session.powerbi_user_info = False

    def store_pb_session_info(self, token_response):
        request.session.powerbi_access_token = token_response.get('access_token')
        request.session.powerbi_refresh_token = token_response.get('refresh_token')
        request.session.powerbi_access_token_info = self.get_access_token_info(token_response['access_token'])
        request.session.powerbi_user_info = self.get_ms_user_info(token_response['id_token'])

    def get_pb_dashboard_action_url(self):
        action = request.env['ir.actions.client']._for_xml_id('ek_powerbi_connector.action_ek_powerbi_connector_dashboard_main')
        backend_url = f'/odoo/action-{action["id"]}'
        return backend_url

    def get_access_token_info(self, access_token):
        payload = decode_jwt_payload(access_token)
        return {
            'exp': payload['exp']
        }

    def get_ms_user_info(self, id_token):
        payload = decode_jwt_payload(id_token)
        return {
            'name': payload['name'],
            'email': payload['email'],
        }
