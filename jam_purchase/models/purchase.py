from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta , date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
import json
import pytz
from datetime import datetime



class ProductCategory(models.Model):
    _inherit = 'product.category'

    is_it = fields.Boolean(string="IT Assets")



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sdk_ref = fields.Char(string="SDK Reference")
    it_check = fields.Boolean(compute="get_validation", string="IT", store=True)
    state = fields.Selection(selection_add=[('osm_it','Group OSM IT Approve'),('ceo_it','Group CIO Approve')], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)


    @api.depends('order_line')
    def get_validation(self):
        for rec in self:
            rec.it_check = False
            if rec.order_line:
                for line in rec.order_line:
                    if line.product_id.categ_id.is_it is True:
                        rec.it_check = True

    def action_submit_po(self):
        super().action_submit_po()
        order_list=[]
        notification_ids=[]
        it = False
        for order in self:
            if not order.order_line:
                raise UserError('You need to add products to proceed with the purchase order')

            if order.it_check:
                group = self.env['res.groups'].sudo().search([('name', '=', 'Group OSM IT Approve')], limit=1)
                if group:
                    for user in group.users:
                        user_tz = self.env.user.tz or 'UTC'
                        local_tz = pytz.timezone(user_tz)
                        local_dt = order.sudo().date_order.astimezone(local_tz)
                        custom_date = local_dt.strftime('%Y-%m-%d %H:%M:%S')

                        date_string = order.sudo().date_order.strftime('%Y-%m-%d %H:%M:%S')
                        date_string2 = fields.Datetime.to_string(order.sudo().date_order)
                        msg = _('<p> <strong">Dear: </strong>') + user.name + '</p><br/>'
                        msg += _('The LPO Details Below Need Your Approval!') + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Number: </strong>') + order.sudo().name + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Supplier: </strong>') + order.sudo().partner_id.name + '<br/>'
                        msg += _('<strong style="color: #00008B;">SDK Reference: </strong>') + order.sudo().sdk_ref + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Date: </strong>') + custom_date + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Total: </strong>') + str(order.sudo().amount_total) + ' ' + str(order.sudo().currency_id.symbol) + '<br/>'
                        msg += _('<p> <strong>Regards,,</strong>') + '</p><br/>'
                        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                        base_url += '/web#id=%d&view_type=form&model=%s' % (order.id, self._name)
                        msg += str(base_url)
                    
                        self.env['mail.mail'].create(dict(
                                subject=_('LPO approval request'),
                                body_html=msg,
                                email_from=self.env.company.partner_id.email,
                                email_to=user.email,
                            )).send()
                                    
        return True

    def action_gosm(self):
        for order in self:
            order.state = 'osm_it'
            if order.it_check:
                group = self.env['res.groups'].sudo().search([('name', '=', 'Group CIO Approval')], limit=1)
                if group:
                    for user in group.users:
                        user_tz = self.env.user.tz or 'UTC'
                        local_tz = pytz.timezone(user_tz)
                        local_dt = order.sudo().date_order.astimezone(local_tz)
                        custom_date = local_dt.strftime('%Y-%m-%d %H:%M:%S')

                        date_string = order.sudo().date_order.strftime('%Y-%m-%d %H:%M:%S')
                        date_string2 = fields.Datetime.to_string(order.sudo().date_order)
                        msg = _('<p> <strong">Dear: </strong>') + user.name + '</p><br/>'
                        msg += _('The LPO Details Below Need Your Approval!') + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Number: </strong>') + order.sudo().name + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Supplier: </strong>') + order.sudo().partner_id.name + '<br/>'
                        msg += _('<strong style="color: #00008B;">SDK Reference: </strong>') + order.sudo().sdk_ref + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Date: </strong>') + custom_date + '<br/>'
                        msg += _('<strong style="color: #00008B;">LPO Total: </strong>') + str(order.sudo().amount_total) + ' ' + str(order.sudo().currency_id.symbol) + '<br/>'
                        msg += _('<p> <strong>Regards,,</strong>') + '</p><br/>'
                        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                        base_url += '/web#id=%d&view_type=form&model=%s' % (order.id, self._name)
                        msg += str(base_url)
                    
                        self.env['mail.mail'].create(dict(
                                subject=_('LPO approval request'),
                                body_html=msg,
                                email_from=self.env.company.partner_id.email,
                                email_to=user.email,
                            )).send()
                                    
        return True

    def action_gcio(self):
        for order in self:
            order.button_approve()

