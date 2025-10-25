from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CustomerArticle(models.Model):
    _name = 'customer.article'
    _description = 'customer article'
    _rec_name = 'name'

    name = fields.Char("Customer Article Code")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer'
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string=' product_tmpl_id'
    )

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            if record.name:
                existing = self.search([
                    ('name', '=', record.name),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError("The name must be unique.")