from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ChannelChannel(models.Model):
    _name = "channel.channel"
    _description = "Customer Channel"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "channel_name"

    channel_name = fields.Text(string='Channel Name')


class OutletChannel(models.Model):
    _name = "outlet.channel"
    _description = "Outlet Channel"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "outlet_name"


    outlet_name = fields.Text(string='Outlet Name')

    channel_name_id = fields.Many2one(
        'channel.channel',
        string="Channel Name"
    )

    sub_outlet_ids = fields.One2many(
        comodel_name="sub.outlet.channel",
        inverse_name="outlet_id",
        string="Sub Outlets"
    )



class SubOutletChannel(models.Model):
    _name = "sub.outlet.channel"
    _description = "Sub Outlet Channel"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "sub_outlet_name"

    sub_outlet_name = fields.Text(string='Sub Outlet')

    outlet_id = fields.Many2one(
        'outlet.channel',
        string="Outlet"
    )
