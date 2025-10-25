from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CustomerMapping(models.Model):
    _name = "customer.mapping"
    _description = "Customer Mapping"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('res.partner', required=True)

    customer_map_lines = fields.One2many('customer.mapping.line', 'customer_map_id')

    location_id = fields.Many2one("fsm.location", required=True)



class CustomerMappingLine(models.Model):
    _name = "customer.mapping.line"

    customer_map_id = fields.Many2one('customer.mapping')

    worker_id = fields.Many2one('res.partner', 'Worker',  domain="[('fsm_person', '=', True)]")
    division = fields.Selection([('food', 'Food'),
                                    ('non_food', 'Non Food'),
                                    ('mars', 'MARS')], string='Division')
    categ_id = fields.Many2one('product.category', string='Product Category')
