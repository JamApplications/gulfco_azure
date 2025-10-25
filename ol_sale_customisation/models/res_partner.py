from odoo import models, api


class Partner(models.Model):
    _inherit = "res.partner"
    
    _rec_names_search = ['complete_name', 'email', 'ref', 'vat', 'company_registry','customer_code', 'outlet_code','vendor_code']
    
  