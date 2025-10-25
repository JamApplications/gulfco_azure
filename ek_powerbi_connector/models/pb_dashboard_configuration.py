# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

from odoo import models, fields


class PbDashboardConfiguration(models.Model):
    _name = 'pb.dashboard.configuration'
    _description = "PowerBI Dashboard Configuration"

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    report_tag_id = fields.Many2one('pb.report.tag', string='Report Tag')

    group_id = fields.Char('Group ID', required=True)
    report_id = fields.Char('Report ID', required=True)
