from odoo import _, api, fields, models

class ProjectTask(models.Model):
    _inherit = 'project.task'

    picking_id = fields.Many2one('stock.picking', string='Picking')