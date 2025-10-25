# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api

rma_return_caused_by = [('admin_error', 'Administrative Error'),
                        ('customer_error', 'Customer'),
                        ('logistic_error', 'Logistic'),
                        ('order_entry_error', 'Order Entry'),
                        ('sales_error', 'Sales'),
                        ('warehouse_error', 'Warehouse'),
                        ]





class ReturnCausedBy(models.Model):
    _name = "rma.return.caused.by"
    _description = 'RMA Return Caused By'
    _rec_name = 'sales_teams'


    sales_teams=fields.Many2one('crm.team','Sales Team')
    # return_reason_id=fields.Many2one(comodel_name="rma.return.reason",
    #     string="Return Reason")
    return_reason_ids = fields.Many2many(
    comodel_name="rma.return.reason",
    string="Return Reasons"
    )
    # return_caused_by=fields.Many2one('res.users','Return Caused By')
    return_caused_by = fields.Selection(
        selection=rma_return_caused_by,)

    return_caused_by_ids = fields.Many2many('rma.return.caused.config')

    # return_reason_type_id=fields.Many2one('rma.return.reason.type','Return Type',related='return_reason_id.type')
    return_reason_type_ids = fields.Many2many(
    comodel_name='rma.return.reason.type',
    string='Return Reason Types',
    compute='_compute_return_reason_types',
    store=False,
)

    @api.depends('return_reason_ids.type')
    def _compute_return_reason_types(self):
        for rec in self:
            rec.return_reason_type_ids = rec.return_reason_ids.mapped('type')
            
