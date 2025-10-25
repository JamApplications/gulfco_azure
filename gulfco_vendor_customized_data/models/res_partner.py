from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    supplier_type = fields.Selection([('local', 'Local'),
                                      ('foreign', 'Foreign'),
                                      ('related', 'Related Party'),
                                      ('employee', 'Employee')],
                                     string="Supplier Type")

    rfq_analysis_ref = fields.Char(string="RFQ & Quote Analysis Ref")
    supplier_hold = fields.Boolean(string="Supplier Hold")

    supplier_classification_id = fields.Many2one('supplier.classification', string='Supplier Classification')

    # this field 'supplier_classification' Not in use
    supplier_classification = fields.Selection(
        [('principle', 'Principle'), ('maintenance', 'Maintenance'), ('stationery', 'Stationery'),
         ('uniform', 'Uniform'), ('ac_spare_parts', 'AC & Spare Parts'), ('printing', 'Printing'),
         ('marketing_advertisement', 'Marketing & Advertisement')],string="Supplier Classification")

    vendor_code = fields.Char(string="Vendor Code")
    parent_group_name = fields.Char(string="Parent Group Name")
    legal_document_issue_date = fields.Date(string="Issued Date")
    issuance_authority = fields.Char(string='Issuance Authority')
    legal_document_expiry_date = fields.Date(string="Expiry Date")
    trade_license_attachment = fields.Binary(string="Trade License")
    trade_license_file_name = fields.Char()
    vat_trn_attachment = fields.Binary(string="VAT/ TRN Certifcates")
    vat_trn_file_name = fields.Char()
    bank_account_attachment = fields.Binary(string="Bank Letter Stating Your Account No")
    bank_account_attachment_file_name = fields.Char()
    noc_payment_attachment = fields.Binary(string="NOC for Transfer of Payments")
    noc_payment_file_name = fields.Char()
    other_document_attachment = fields.Binary(string="Other Documents")
    other_document_file_name = fields.Char()
    vendor_registration_attachment = fields.Binary(string="VENDOR REGISTRATION FORM ( VRF) - Hardcopy")
    vendor_registration_file_name = fields.Char()
    agreement_attachment = fields.Binary(string="Agreements")
    agreement_file_name = fields.Char()
    other_attachment = fields.Binary(string="Other Attachments")
    other_attachment_file_name = fields.Char()
    quotation_attachment = fields.Binary(string="Quotation")
    quotation_attachment_file_name = fields.Char()


    #customer Attachments
    caf_attachment = fields.Binary(string="CAF")
    caf_file_name = fields.Char()

    guarantees_copy_attachment = fields.Binary(string="Guarantees Copy.")
    guarantees_copy_file_name = fields.Char()

    bank_statement_attachment = fields.Binary(string="Bank Statement of 6 months")
    bank_statement_file_name = fields.Char()

    eid_attachment = fields.Binary(string="EID Copy")
    eid_file_name = fields.Char()

    agreement_copy_attachment = fields.Binary(string="Agreement Copy")
    agreement_copy_file_name = fields.Char()

    poer_attorney_attachment = fields.Binary(string="Poer of Attorney")
    poer_attorney_file_name = fields.Char()

    company_photo_attachment = fields.Binary(string="Company Photo")
    company_photo_file_name = fields.Char()

    passport_copy_attachment = fields.Binary(string="Passport Copy")
    passport_copy_file_name = fields.Char()

    memorandum_association_attachment = fields.Binary(string="Memorandum of Association")
    memorandum_association_file_name = fields.Char()

    @api.onchange('contact_type')
    def onchange_contact_type(self):
        if self.contact_type == 'customer':
            self.customer_rank = 1
            self.supplier_rank = 0
        elif self.contact_type == 'supplier':
            self.supplier_rank = 1
            self.customer_rank = 0
        elif self.contact_type == 'both':
            self.customer_rank = 1
            self.supplier_rank = 1

    @api.onchange('supplier_type')
    def onchange_supplier_type(self):
        if self.supplier_type == 'foreign':
            self.rfq_analysis_ref = None

    def _compute_display_name(self):
        super()._compute_display_name()
        for partner in self.filtered(lambda s:s.contact_type == 'customer'):
            if partner.street:
                partner.display_name += f', {partner.street}'
            if partner.street2:
                partner.display_name += f', {partner.street2}'
            if partner.city:
                partner.display_name += f', {partner.city}'
            if partner.state_id:
                partner.display_name += f', {partner.state_id.name}'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self.env.context.get('show_address'):
            # domain = args or []
            domain = expression.AND([[('display_name', operator, name)], args or []])
            partners = self.search_fetch(
                domain, ['name'], limit=limit)
            partner_list = []
            for partner in partners:
                name = partner.with_context(lang=self.env.lang)._get_complete_name()
                if partner.street:
                    name += f', {partner.street}'
                if partner.street2:
                    name += f', {partner.street2}'
                if partner.city:
                    name += f', {partner.city}'
                if partner.state_id:
                    name += f', {partner.state_id.name}'
                partner_list.append((partner.id,name))
            return partner_list
        return super().name_search(name, args, operator, limit)
