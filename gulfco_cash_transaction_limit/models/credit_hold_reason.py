from odoo import models, fields

class CreditHoldReason(models.Model):
    _name = 'credit.hold.reason'
    _description = 'Credit Hold Reason'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    reason = fields.Selection([('overdue_invoice', 'Overdue Invoice'),
                               ('uncollected_pdc', 'Uncollected PDC'),
                               ('uncollected_cdc', 'Uncollected CDC'),
                               ('uncovered_invoice', 'Uncovered Invoice'),
                               ('expired_license', 'Expired License'),
                               ('bounced_cheque', 'Bounced Cheque'),
                               ('manual_reason', 'Manual Reason'),], default='manual_reason', string='Reason')