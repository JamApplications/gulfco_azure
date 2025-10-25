# Copyright 2020 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models,api 
from odoo.exceptions import UserError


class RMA(models.Model):
    _inherit = "rma"


    return_reason_ids=fields.Many2many('rma.return.reason',
        string="Return Reason",compute="_compute_return_caused_by_ids",store=True)
    return_caused_by_ids = fields.Many2many(
        'rma.return.caused.config',
        'res_users_users_rma_rel',  # relation table
        'rma_id',  # column pointing to rma.id
        'res_users_id',  # column pointing to res.users.id
        string='Return Caused By',
        compute="_compute_return_caused_by_ids",store=True
    )
    return_reason_id = fields.Many2one(
        comodel_name="rma.return.reason",
        domain="[('id', 'in', return_reason_ids)]",
        string="Return Reason",
        copy=False,
        tracking=True,
        required=False,
    )
    return_reason_type_id=fields.Many2one('rma.return.reason.type','Return Type')
    return_caused_by_id = fields.Many2one('rma.return.caused.config', required=False, related=False,
                                          domain="[('id', 'in', return_caused_by_ids)]")

    @api.depends('picking_id', 'crm_team_id', 'return_caused_by')
    def _compute_return_caused_by_ids(self):
        for rec in self:
            rec.return_reason_ids = None
            rec.return_caused_by_ids = None
            if rec.crm_team_id:
                domains = self.env['rma.return.caused.by'].search([('sales_teams', '=', rec.crm_team_id.id)])
                return_reason_ids = domains.mapped('return_reason_ids')
                return_caused_by_ids = domains.mapped('return_caused_by_ids')
                rec.return_reason_ids = [(6, 0, return_reason_ids.ids)]
                rec.return_caused_by_ids = [(6, 0, return_caused_by_ids.ids)]

    @api.model
    def create(self, vals):
        order = super(RMA, self).create(vals)

        for line in order.line_ids:
            if order.return_caused_by_id:
                if not line.return_caused_by_id:
                    line.return_caused_by_id = order.return_caused_by_id.id

            if order.return_reason_id:
                if not line.return_reason_id:
                    line.return_reason_id = order.return_reason_id.id

            if order.return_reason_type_id:
                if not line.return_reason_type_id:
                    line.return_reason_type_id = order.return_reason_type_id.id


        for line in order.product_line_ids:
            if order.return_caused_by_id:
                if not line.return_caused_by_id:
                    line.return_caused_by_id = order.return_caused_by_id.id

            if order.return_reason_id:
                if not line.return_reason_id:
                    line.return_reason_id = order.return_reason_id.id

            if order.return_reason_type_id:
                if not line.return_reason_type_id:
                    line.return_reason_type_id = order.return_reason_type_id.id

        return order

    def write(self, vals):
        res = super(RMA, self).write(vals)
        for line in self.line_ids:
            if self.return_caused_by_id:
                if not line.return_caused_by_id:
                    line.return_caused_by_id = self.return_caused_by_id.id

            if self.return_reason_id:
                if not line.return_reason_id:
                    line.return_reason_id = self.return_reason_id.id

            if self.return_reason_type_id:
                if not line.return_reason_type_id:
                    line.return_reason_type_id = self.return_reason_type_id.id

        for line in self.product_line_ids:
            if self.return_caused_by_id:
                if not line.return_caused_by_id:
                    line.return_caused_by_id = self.return_caused_by_id.id

            if self.return_reason_id:
                if not line.return_reason_id:
                    line.return_reason_id = self.return_reason_id.id

            if self.return_reason_type_id:
                if not line.return_reason_type_id:
                    line.return_reason_type_id = self.return_reason_type_id.id
        return res

    @api.onchange('return_caused_by_id','return_reason_id','return_reason_type_id')
    def _onchange_return_reason_type_id_id(self):
        for line in self.line_ids:
            if self.return_caused_by_id:
                if not line.return_caused_by_id:
                    line.return_caused_by_id = self.return_caused_by_id.id

            if self.return_reason_id:
                if not line.return_reason_id:
                    line.return_reason_id = self.return_reason_id.id

            if self.return_reason_type_id:
                if not line.return_reason_type_id:
                    line.return_reason_type_id = self.return_reason_type_id.id

        for line in self.product_line_ids:
            if self.return_caused_by_id:
                if not line.return_caused_by_id:
                    line.return_caused_by_id = self.return_caused_by_id.id

            if self.return_reason_id:
                if not line.return_reason_id:
                    line.return_reason_id = self.return_reason_id.id

            if self.return_reason_type_id:
                if not line.return_reason_type_id:
                    line.return_reason_type_id = self.return_reason_type_id.id
    # @api.depends("crm_team_id",'return_caused_by')
    # def _compute_return_caused_by_ids(self):
    #     for rec in self:
    #         if rec.crm_team_id:
    #             domains=self.env['rma.return.caused.by'].search([('sales_teams','=',rec.crm_team_id.id)])
    #             return_caused_by = domains.mapped('return_caused_by')  # collect all related return_reason_id ids
    #             # rec.return_caused_by_ids= [(6, 0, return_caused_by)]
    #             # rec.return_caused_by_ids=list(return_caused_by)
    #             if return_caused_by:
    #                 return_caused_by_ids=domains.filtered(lambda domain:domain.return_caused_by==rec.return_caused_by)
    #                 # return_caused_by_ids=domains
    #                 return_reason_ids=return_caused_by_ids.mapped('return_reason_ids').ids
    #                 rec.return_reason_ids=list(return_reason_ids)
    #             else:
    #                 rec.return_reason_ids=False
    #         else:
    #             rec.return_reason_ids=False
    #             # rec.return_caused_by_ids=False


class RMAProductLine(models.Model):
    _inherit = 'rma.product.line'

    return_reason_ids = fields.Many2many('rma.return.reason', compute="_compute_return_reason_ids",
                                         string="Return Reason", store=True )

    return_caused_by_ids = fields.Many2many('rma.return.caused.config', compute="_compute_return_reason_ids",
                                            string="Return Cause BY",store=True)

    @api.depends('rma_id', 'rma_id.crm_team_id', 'rma_id.return_caused_by_id')
    def _compute_return_reason_ids(self):
        for rec in self:
            rec.return_reason_ids = None
            rec.return_caused_by_ids = None
            if rec.rma_id.crm_team_id:
                domains = self.env['rma.return.caused.by'].search([('sales_teams', '=', rec.rma_id.crm_team_id.id)])
                return_reason_ids = domains.mapped('return_reason_ids')
                return_caused_by_ids = domains.mapped('return_caused_by_ids')
                rec.return_reason_ids = [(6, 0, return_reason_ids.ids)]
                rec.return_caused_by_ids = [(6, 0, return_caused_by_ids.ids)]

    return_reason_id = fields.Many2one(
        comodel_name="rma.return.reason",
        string="Return Reason",
        domain="[('id', 'in', return_reason_ids)]",
        copy=False,
        tracking=True,
        required=False,
    )
    return_caused_by_id = fields.Many2one('rma.return.caused.config', required=True,related=False,domain="[('id', 'in', return_caused_by_ids)]")

class RMALine(models.Model):
    _inherit = 'rma.line'


    return_reason_ids = fields.Many2many('rma.return.reason', compute="_compute_return_caused_by_ids",
                                         string="Return Reason", store=True)

    return_caused_by_ids = fields.Many2many('rma.return.caused.config', compute="_compute_return_caused_by_ids",
                                            string="Return Caused BYS",store=True)
    return_caused_by_id = fields.Many2one('rma.return.caused.config', required=False,related=False,domain="[('id', 'in', return_caused_by_ids)]")


    @api.depends('rma_id', 'rma_id.picking_id', 'rma_id.crm_team_id', 'rma_id.return_caused_by')
    def _compute_return_caused_by_ids(self):
        for rec in self:
            rec.return_reason_ids = None
            rec.return_caused_by_ids = None
            if rec.rma_id.crm_team_id:
                domains = self.env['rma.return.caused.by'].search([('sales_teams', '=', rec.rma_id.crm_team_id.id)])
                return_reason_ids = domains.mapped('return_reason_ids')
                return_caused_by_ids = domains.mapped('return_caused_by_ids')
                rec.return_reason_ids = [(6, 0, return_reason_ids.ids)]
                rec.return_caused_by_ids = [(6, 0, return_caused_by_ids.ids)]



    return_reason_id = fields.Many2one(
        comodel_name="rma.return.reason",
        domain="[('id', 'in', return_reason_ids)]",
        string="Return Reason",
        copy=False,
        tracking=True,
        required=False,
    )
