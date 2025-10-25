from odoo import api, fields, models, _



class SupplierClassification(models.Model):
    _name = 'supplier.classification'
    _description = 'Supplier Classification'
    _rec_name = 'name'


    name = fields.Char('Name', required=True)
    is_filtered = fields.Boolean('Is Principal')



