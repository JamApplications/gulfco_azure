from odoo import models, fields, api
from odoo.exceptions import UserError



class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _rec_names_search = ['barcode_string']

    
    # Define a computed field that will store the space-separated barcodes
    barcode_string = fields.Char(
        string='Barcodes', 
        compute='_compute_barcodes', 
        store=True  # This field will not be stored in the database, it's computed on the fly
    )

    search_string = fields.Char(
        string='Search String',
    )

    @api.depends('packaging_ids.barcode', 'packaging_ids.package_type_id.barcode' )
    def _compute_barcodes(self):
        for product in self:
            # Initialize an empty list to store the barcodes
            barcodes = []
            
            # Iterate over the packaging_ids related records
            for packaging in product.packaging_ids:
                # Check if package_type_id and barcode exist, then add to the list
                if packaging.barcode:
                    barcodes.append(packaging.barcode)
                elif packaging.package_type_id and packaging.package_type_id.barcode:
                    barcodes.append(packaging.package_type_id.barcode)

            # Join the list of barcodes into a space-separated string
            product.barcode_string = ' '.join(barcodes)
            
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super(ProductTemplate, self).name_search(name=name, args=args, operator=operator, limit=limit)
        if name:
            self.browse([tup[0] for tup in res]).update({'search_string':name})
        return res




class ProductProduct(models.Model):
    _inherit = 'product.product'
    _rec_names_search = ['barcode_string']

    barcode_string = fields.Char(
        string="Package Barcodes",
        compute="_compute_packaging_barcodes",
        store=True
    )

    search_string = fields.Char(
        string='Search String',
    )

    @api.depends('product_tmpl_id.packaging_ids.barcode', 'product_tmpl_id.packaging_ids.package_type_id.barcode')
    def _compute_packaging_barcodes(self):
        for product in self:
            barcodes = []
            for packaging in product.product_tmpl_id.packaging_ids:
                if packaging.barcode:
                    barcodes.append(packaging.barcode)
                elif packaging.package_type_id and packaging.package_type_id.barcode:
                    barcodes.append(packaging.package_type_id.barcode)
            product.barcode_string = ' '.join(barcodes)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super(ProductProduct, self).name_search(name=name, args=args, operator=operator, limit=limit)
        if name:
            res = res + [(product.id, product.display_name) for product in self.search([('barcode_string', operator, name)])]
            self.browse([tup[0] for tup in res]).update({'search_string': name})
        return res

