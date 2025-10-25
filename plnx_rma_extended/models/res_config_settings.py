
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    grv_amount = fields.Float(
        string="GRV Amount Limit",
        config_parameter='plnx_rma_extended.grv_amount',
    )