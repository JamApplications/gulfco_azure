# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

from odoo.models import AbstractModel
from odoo.http import request


class IrHttp(AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        if request.session.powerbi_access_token:
            res.update({
                'powerbi_access_token': request.session.powerbi_access_token,
            })
        if request.session.powerbi_refresh_token:
            res.update({
                'powerbi_refresh_token': request.session.powerbi_refresh_token,
            })
        if request.session.powerbi_access_token_info:
            res.update({
                'powerbi_access_token_info': request.session.powerbi_access_token_info,
            })
        if request.session.powerbi_user_info:
            res.update({
                'powerbi_user_info': request.session.powerbi_user_info,
            })
        return res
