# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsersExt(models.Model):
    _name = 'mobile.auth.token'
    _description = 'Gulfco mobile auth token'

    user_id = fields.Many2one('res.users', string='Users',required=True)
    mobile_app_auth_token = fields.Char('Auth Token')
    last_login_time = fields.Datetime('Last Login Time')



    