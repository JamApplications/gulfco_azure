from odoo import models, fields, api, _


class DivisionManagement(models.Model):
    _name = 'division.management'
    _description = 'Division Management'

    name = fields.Char(string="Name")
    type = fields.Selection([('food', 'Food'),
                             ('non_food', 'Non-Food'),
                             ('mars', 'MARS')
                             ], string='Type')


class CustomerSubdivision(models.Model):
    _name = 'customer.subdivision'
    _description = 'Customer Subdivision'

    name = fields.Char(required=True)


class SalesMen(models.Model):
    _name = 'sales.men'
    _description = 'Sales  Men'


    sales_partner_id = fields.Many2one('res.partner')#relate2 One2many



    name = fields.Char(string="Name")
    sale_man_id = fields.Many2one('res.users', required=True)
    division_id = fields.Many2one('division.management')
    department = fields.Many2one('account.analytic.account', string="Department")
    sale_man_contact = fields.Char(related='sale_man_id.phone')
    sale_man_mail = fields.Char(related='sale_man_id.email')


