from odoo import fields, models

class AssessmentVendorDomain(models.Model):
    _name = 'assessment.vendor.domain'
    _description = 'Assessment Vendor Domain'

    order_count = fields.Integer(string="Nb of Orders")

    rdd = fields.Integer('RDD')
