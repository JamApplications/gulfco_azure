from odoo import models, fields


class CrossDockingMappingGroup(models.Model):
    _name = 'cross.docking.mapping.group'
    _description = 'Cross Docking Mapping Group'
    _rec_name = "division"

    division = fields.Selection([
        ('food', 'Food'),
        ('non_food', 'Non-Food'),
        ('mars', 'MARS')
    ], string='Division', required=True)

    line_ids = fields.One2many('cross.docking.mapping', 'cross_docking_group_id', string='Mapping Lines')

    is_normal = fields.Boolean(string='Is Normal')


class CrossDockingMapping(models.Model):
    _name = 'cross.docking.mapping'
    _description = 'Cross Docking Mapping'

    cross_docking_group_id = fields.Many2one(
        comodel_name='cross.docking.mapping.group',
        string=' cross_docking_group_id',
    )

    division = fields.Selection([
        ('food', 'Food'),
        ('non_food', 'Non-Food'),
        ('mars', 'Mars')
    ], string='Division', related="cross_docking_group_id.division")

    is_dxb = fields.Boolean(string="DXB")
    is_shj = fields.Boolean(string="SHJ")
    is_adh = fields.Boolean(string="ADH")
    is_aln = fields.Boolean(string="ALN")
    is_rak = fields.Boolean(string="RAK")
    is_fuj = fields.Boolean(string="FUJ")
    is_ne = fields.Boolean(string="NE")

    wh_location_id = fields.Many2one('stock.warehouse', string='WH / Customer', required=True)


