# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RmaReDeliveryWizard(models.TransientModel):
    _inherit = "rma.delivery.wizard"

    is_delivery_type = fields.Boolean()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        rma_ids = self.env.context.get("active_ids")
        rma = self.env["rma"].browse(rma_ids)
        is_delivery_type = False
        if len(rma) == 1 :
            is_delivery_type = True
        res.update(
            is_delivery_type=is_delivery_type,
        )
        return res