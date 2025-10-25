# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

from odoo import fields, models, _


class AssessmentRefuseReason(models.TransientModel):
    _name = "assessment.refuse.reason"
    _description = "Assessment Refused Reason"

    reason = fields.Text("Reason", required=True)

    def action_reason_apply(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        ActModel = self.env[active_model]
        if hasattr(self.env[active_model], "set_refused"):
            records = ActModel.browse(active_ids)
            records.set_refused(self.reason)
