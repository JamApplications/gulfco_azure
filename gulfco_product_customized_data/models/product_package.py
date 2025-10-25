from odoo import models, fields, api


class ProductPackage(models.Model):
    _inherit = "product.packaging"

    secondary_package=fields.Many2one('product.packaging',string="Secondary Package")
    secondary_quantity=fields.Integer("Secondary Quantity")
    secondary_package_active = fields.Boolean(compute='_compute_secondary_package_active', store=True)
    # product_id = fields.Many2one('product.product', string='Product', check_company=True, required=False, ondelete="cascade")
    # allowed_secondary_packaging_ids = fields.Many2many('product.packaging', compute='_compute_allowed_secondary_packagings')
    #
    # @api.depends('product_id','name')
    # def _compute_allowed_secondary_packagings(self):
    #     for rec in self:
    #         if rec.product_id:
    #             rec.allowed_secondary_packaging_ids = self.env['product.packaging'].search([
    #                 ('product_id', '=', rec.product_id.id)
    #             ])
    #         else:
    #             rec.allowed_secondary_packaging_ids = False


    @api.depends('secondary_package','qty','secondary_quantity')
    def _compute_secondary_package_active(self):
        for rec in self:
            if rec.secondary_package:
                rec.qty=1
                rec.qty=rec.secondary_package.qty * rec.secondary_quantity
                rec.secondary_package_active = True
            else:
                rec.secondary_package_active=False

    #
    # def default_get(self, fields_list):
    #     defaults = super().default_get(fields_list)
    #     return defaults



    # @api.model
    # def _search(self, domain, offset=0, limit=None, order=None):
    #     if self.env.context.get('custom_parent_id'):
    #         product_template = self.env['product.template'].browse(self.env.context.get('custom_parent_id'))
    #         # p_id = product_template.with_context(active_test=False).product_variant_id.id
    #         # query = 'select id from product_packaging where product_id = {}'.format(p_id)
    #         # self.env.cr.execute(query)
    #         # res = self.env.cr.fetchall()
    #         # package_ids = []
    #         # if len(res) > 0:
    #         #     package_ids = [x[0] for x in res]
    #         # domain = domain.copy()
    #         domain.append(('id', 'in',product_template.filter_package_ids._origin.ids))
    #     return super()._search(domain, offset, limit, order)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     packages = super(ProductPackage,self).create(vals_list)
    #     return packages