# -*- coding: utf-8 -*-
######################################################################
#                                                                    #
# Part of EKIKA CORPORATION PRIVATE LIMITED (Website: ekika.co).     #
# See LICENSE file for full copyright and licensing details.         #
#                                                                    #
######################################################################

from odoo import models, fields


class PbReportTag(models.Model):
    _name = 'pb.report.tag'
    _description = "PowerBI Report Tag"

    name = fields.Char('Name', required=True)
