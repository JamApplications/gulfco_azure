# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

import json
from werkzeug.datastructures import Headers
from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request, Response
from odoo.tools import json_default

class PowerBIDatasetController(http.Controller):

    @http.route('/powerbi/api/dataset', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def api_external_dataset(self):
        external_data_conf_id = self._get_external_data_conf()
        if not external_data_conf_id:
            raise AccessDenied()
        main_data = external_data_conf_id.get_powerbi_table_data()
        return self.make_basic_response(main_data)

    @http.route('/powerbi/api/schema', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def api_external_schema(self):
        external_data_conf_id = self._get_external_data_conf()
        if not external_data_conf_id:
            raise AccessDenied()
        main_data = external_data_conf_id.get_powerbi_table_schema()
        return self.make_basic_response(main_data)

    def make_basic_response(self, result):
        data = json.dumps(result, ensure_ascii=False, default=json_default)
        headers = Headers()
        headers['Content-Length'] = len(data)
        headers['Content-Type'] = 'application/json; charset=utf-8'
        return Response(data, headers=headers ,status=200)

    def _get_external_data_conf(self):
        api_key = self.get_request_api_key()
        record = request.env['pb.dataset.configuration'].sudo().search([('api_key', '=', api_key)])
        return record

    def get_request_api_key(self):
        auth = request.httprequest.headers.get('Authorization')
        api_key = auth.split(' ')[1]
        return api_key
