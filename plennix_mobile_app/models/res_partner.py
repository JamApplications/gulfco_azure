# -*- coding: utf-8 -*-
from odoo import models, fields,api
import uuid

class ResUsersInherit(models.Model):
    _inherit = 'res.partner'

    total_visits  = fields.Integer( string='Total Visits')
    customer_code = fields.Char(string='Customer Code')
    division_name = fields.Char(string='Division Name')
    customer_devision = fields.Char(string='Division Name')
    visit_start_time = fields.Datetime(string='Visit Start Time',default=fields.Datetime.now)
    visit_end_time = fields.Datetime(string='Visit End Time',default=fields.Datetime.now)
    visit_duration  = fields.Integer(string='Visit Duration')

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    access_token = fields.Char('Portal Access Token', readonly=True)

    def _ensure_portal_token(self):
        for sale_order in self:
            if not sale_order.access_token:
                sale_order.access_token = str(uuid.uuid4())
        return self.access_token

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    access_token = fields.Char('Portal Access Token', readonly=True)

    def _ensure_portal_token(self):
        for payment in self:
            if not payment.access_token:
                payment.access_token = str(uuid.uuid4())
        return self.access_token
    
class ResUsersInherit(models.Model):
    _inherit = 'res.users'    
    
    user_type = fields.Selection(string='User Type', selection=[('sales_user', 'Sales User'), ('merchant', 'Merchant'), ('delivery_user', 'Delivery User'),('order', 'Order User')])
    auth_token = fields.Char('Auth Token')
    mobile_auth_token_ids = fields.One2many(comodel_name='mobile.auth.token', inverse_name='user_id',
                                               string='Mobile Auth IDs')

    @api.model
    def signup(self, values, token=None):
        if token:
            partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
            if (values.get('password') and
                    partner.contact_type == 'worker' and
                    partner.user_ids and
                    all(user.share for user in partner.user_ids)):
                partner.write({'worker_password_data': values.get('password')})
        return super(ResUsersInherit, self).signup(values, token)
