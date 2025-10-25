import re
from odoo import api, fields, models, _


class AssessmentPOResult(models.Model):
    _name = "assessment.purchase.result"
    _description = "Assessment Purchase Result"
    _order = "sequence"

    sequence = fields.Integer(default=1)
    code = fields.Char(required=True)
    name = fields.Char(required=True)
    description = fields.Text()
    color = fields.Char()
    res_field = fields.Char(copy=False)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Code must be unique'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.generate_vendor_domain_field()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("code"):
            self.generate_vendor_domain_field()
        return res

    def unlink(self):
        self.clear_vendor_domain_field()
        super().unlink()

    def _get_field_name(self):
        self.ensure_one()
        code = re.sub("[^0-9a-zA-Z_]", "", self.code, 0, re.IGNORECASE)
        if not code:
            code = str(self.id)
        return "x_{}".format(code)

    def generate_vendor_domain_field(self):
        ResField = self.env["ir.model.fields"]
        ResModel = self.env['ir.model']
        model_id = ResModel._get_id("assessment.vendor.domain")
        for record in self:
            field_description = (record.name).strip()
            if not field_description:
                continue
            field_name = record._get_field_name()
            field_record = ResField._get("assessment.vendor.domain",
                                         field_name)
            if not field_record:
                f_vals = {
                    "name": field_name,
                    "field_description": field_description,
                    "ttype": "float",
                    "copied": False,
                    "model_id": model_id}
                ResField.sudo().create(f_vals)
                record.res_field = field_name
            else:
                field_record.field_description = field_description

    def clear_vendor_domain_field(self):
        ResField = self.env["ir.model.fields"]
        for record in self:
            if not record.res_field:
                continue
            field_name = record.res_field
            field_record = ResField._get("assessment.vendor.domain",
                                         field_name)
            if field_record:
                field_record.unlink()
                record.res_field = None
