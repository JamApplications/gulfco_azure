# -*- coding: utf-8 -*-
from odoo import models, fields,api
import uuid


class AccountMove(models.Model):
    _inherit = 'account.move'

    access_token = fields.Char('Portal Access Token', readonly=True)

    def _ensure_portal_token(self):
        for move in self:
            if not move.access_token:
                move.access_token = str(uuid.uuid4())
        return self.access_token