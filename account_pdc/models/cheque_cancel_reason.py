from odoo import fields, models, api

class ChequeCancelReason(models.Model):
    _name = 'cheque.cancel.reason'

    name = fields.Char(
        string="Name"
    )
    
    