from odoo import api, fields, models


class GovtAuthority(models.Model):
    _name = 'govt.authority'
    _description = 'Municipality Registration'

    name = fields.Char(string="Name")
    certificate_no = fields.Char(string='Certificate No.')
    registration_date = fields.Date(string='Registration date.')
    expiry_date = fields.Date(string='Expiry date.')
    c_f_g_a = fields.Text(string="Comment from Govt authority.")
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Product')
    municipality_status = fields.Selection(
        [('in_progress', 'In Progress'), ('rejected', 'Rejected'), ('approved', 'Approved'),
         ('return_amendment', 'Return for Amendment')])
