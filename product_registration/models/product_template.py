import typing

from odoo import models, fields, api, _
from odoo.api import ValuesType
from odoo.exceptions import ValidationError
from odoo.tools import is_html_empty
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Management'

    govt_authority_ids = fields.One2many(
        comodel_name='govt.authority',
        inverse_name='product_tmpl_id',
        string=' Govt Authority',
        )

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        for rec in self:
            if rec.is_all_edit and not self.env.context.get('is_update'):
                rec.is_all_edit = False
        return res

    def view_edit_update(self):
        self.is_all_edit = True
    is_all_edit = fields.Boolean(string='All Edit')
    registration_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending_internal_approval', 'Pending Internal Approval'),
            ('approved_to_submit_in_municipality', 'Approved to Submit in Municipality'),
            ('submit_to_item_activation', 'Submit To item Activation'),
            ('submit_to_item_active_without_municipality', 'Submit to Item Activation without municipality'),
            ('returned_for_correction', 'Returned for Correction'),
            ('approve_without_municipality', 'Approve - Without Municipality'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('deleted', 'Deleted'),
        ],
        string='Registration Status',
        default='draft',
        copy=False,
        tracking=True,
    )

    govt_comments = fields.Html(
        string="Comments from Govt Authority",
        required=False,
    )
    govt_auth_name = fields.Text(
        string="Govt Authority Name",
        required=False,
    )
    registration_no = fields.Integer(
        string="Registration No",
        required=True,
    )
    registration_date = fields.Date(
        string="Registration Date",
        required=True,
    )
    is_supplier_agreement = fields.Boolean(
        string="Agreement done with Supplier (yes/no)",
        required=True,
    )

    # Attachments
    product_attachment = fields.Binary(string="Product")
    label_attachment = fields.Binary(string="Label")
    msds_attachment = fields.Binary(string="MSDS")
    freesale_attachment = fields.Binary(string="Free Sale Certificate")
    analysis_attachment = fields.Binary(string="Certificate of Analysis")
    ingredient_division_attachment = fields.Binary(string="Ingredient Certificate")
    other_attachment = fields.Binary(string="Another Certificate")

    ingredient_details = fields.Text(string="Ingredient Details")
    municipality_status = fields.Selection([('dm_approved_moccae_progress','DM - Approved - MOCCAE - In Progress'),
                                           ('approved','Approved'),
                                           ('esma_expired','ESMA Expired'),
                                            ('esma_going_expired','ESMA Going to Expire < 60 Days'),
                                            ('dm_approved_esma_moccae_progress','DM - Approved - ESMA - Approved - MOCCAE - In Progess')])

    @api.onchange('item_type','is_storable','tracking')
    def onchange_item_tracking(self):
        if self.item_type == 'tradable' and self.is_storable and self.tracking == 'lot':
            self.use_expiration_date = True
        # if self.item_type == 'consumable':
        #     self.registration_status = 'approved'
        #     self.active = True


    @api.model_create_multi
    def create(self, vals_list):
        registration_mode = self._context.get('registration_mode', False)
        products = super().create(vals_list)
        for product in products:
            # if product.type != 'service' and is_html_empty(product.govt_comments):
            #     raise ValidationError('Please Set Value Comments from Govt Authority')
            if product.type == 'consu' and product.item_type == 'tradable' and not registration_mode:
                product.active = False
                product.registration_status = 'draft'
                # raise ValidationError('Create product from product registration menu')
            if registration_mode:
                product.active = False
            if self.env.context.get('from_create_prod_template') and ((product.type == 'consu' and product.item_type == 'consumable') or product.type != 'consu'):
                product.registration_status = 'approved'
                product.active = True
        return products

    @api.onchange('division')
    def onchange_division(self):
        if self.division == 'mars':
            self.expiration_time = 60
        elif self.division == 'food':
            self.expiration_time = 90
        elif self.division == 'non_food':
            self.expiration_time = 180

    # def write(self, val_list):
    #     res = super().write(val_list)
    #     for product in self:
    #         if product.type != 'service' and is_html_empty(product.govt_comments):
    #             raise ValidationError('Please Set Value Comments from Govt Authority')
    #     return res


    # ============= registration lifecycle =============
    def action_pending_internal_approval(self):
        for product in self:
            if product.registration_status == 'draft':
                product.registration_status = 'pending_internal_approval'

    def action_set_to_draft(self):
        for product in self:
            product.registration_status = 'draft'

    def action_approve_municipality(self):
        for product in self:
            if product.registration_status == 'pending_internal_approval':
                product.registration_status = 'approved_to_submit_in_municipality'

    def action_submit_item_activation(self):
        for product in self:
            if product.govt_authority_ids and 'approved' not in product.govt_authority_ids.mapped('municipality_status'):
                raise UserError('please proceed with activation without Municipality as None of the Municipality line is approved')
            if product.registration_status == 'approved_to_submit_in_municipality':
                product.registration_status = 'submit_to_item_activation'

    def action_submit_item_activation_without_municipality(self):
        for product in self:
            if product.govt_authority_ids and 'approved' in product.govt_authority_ids.mapped('municipality_status'):
                raise UserError('please proceed with activation with submit to item activation as Some of the Municipality line is approved')
            if product.registration_status == 'returned_for_correction':
                product.registration_status = 'submit_to_item_active_without_municipality'

    def action_approve_without_municipality(self):
        for product in self:
            if product.govt_authority_ids and 'approved' in product.govt_authority_ids.mapped('municipality_status'):
                raise UserError('please proceed with activation with submit to item activation as Some of the Municipality line is approved')
            if product.registration_status == 'approved_to_submit_in_municipality':
                product.registration_status = 'approve_without_municipality'
                product.active = True

    # def action_approved_to_submit_in_municipality(self):
    #     for product in self:
    #         product.registration_status = 'approved_to_submit_in_municipality'

    def action_returned_for_correction(self):
        for product in self:
            if product.registration_status == 'pending_internal_approval':
                product.registration_status = 'returned_for_correction'

    def action_approved(self):
        for product in self:
            if product.registration_status in ['submit_to_item_activation','submit_to_item_active_without_municipality',]:
                product.registration_status = 'approved'
                product.active = True
                product.is_all_edit = False

    def action_rejected(self):
        for product in self:
            if product.registration_status in ['pending_internal_approval','submit_to_item_active_without_municipality','submit_to_item_activation']:
                product.registration_status = 'rejected'

    def action_deleted(self):
        for product in self:
            if product.registration_status in ['submit_to_item_active_without_municipality','submit_to_item_activation']:
                product.registration_status = 'deleted'
                product.active = False

    # def action_archive(self):
    #     res = super().action_archive()
    #     for product in self:
    #         product.registration_status = 'rejected'

    # def action_unarchive(self):
    #     res = super().action_unarchive()
    #     for product in self:
    #         product.registration_status = 'approved'
    #     return res

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self._context.get('registration_mode'):
            state_list = ['approved','rejected','deleted']
            if self.env.user.has_group('product_registration.group_submit_for_municipality_registration'):
                state_list.append('draft')
            if self.env.user.has_group('product_registration.group_pending_internal_approval'):
                state_list.append('pending_internal_approval')
            if self.env.user.has_group('product_registration.group_submit_item_activation'):
                state_list.append('approved_to_submit_in_municipality')
            if self.env.user.has_group('product_registration.group_submit_item_activation_approval'):
                state_list.append('submit_to_item_activation')
            if self.env.user.has_group('product_registration.group_submit_item_activation_without_municipality'):
                state_list.append('returned_for_correction')
                state_list.append('approve_without_municipality')
            if self.env.user.has_group('product_registration.group_item_activation_without_municipality_approval'):
                state_list.append('submit_to_item_active_without_municipality')
            domain = domain.copy()
            domain.append((('registration_status', 'in', state_list)))
        return super()._search(domain, offset, limit, order)

class Productproduct_registration(models.Model):
    _inherit = 'product.product'


    def view_edit_update(self):
        self.is_all_edit = True

    def write(self, vals):
        res = super(Productproduct_registration, self).write(vals)
        for rec in self:
            if rec.is_all_edit and not self.env.context.get('is_update'):
                rec.is_all_edit = False
        return res
