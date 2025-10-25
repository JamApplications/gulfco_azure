# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError

bu_sales_field = ['customer_group_id',
                    'outlet_code',
                  'outlet_short_name',
                  'external_ref',
                  'sales_leader_id',
                  'collector_id',
                  'buyer_id',
                  'finance_manager_id',
                  'share_soa_email',
                  'share_invoice_email',
                  'latitude',
                  'longitude'
                  'partner_channel_id',
                  'outlet_id',
                  'sub_outlet_id']

bu_scm_field = [
    'delivery_receive_time'
]

ccd_fields = ['name',
              'channel',
              'current_chanel',
              'current_sub_channel',
              'channel_mt',
              'channel_mt_hyper',
              'channel_mt_super',
              'channel_gt',
              'channel_gt_grocery',
              'channel_gt_cs',
              'channel_gt_super',
              'channel_gt_petrol',
              'channel_gt_discount',
              'channel_gt_wholesale',
              'channel_gt_tc',
              'channel_gt_sc',
              'channel_horeca',
              'channel_horeca_hr',
              'channel_horeca_rc',
              'channel_horeca_sa',
              'channel_horeca_caterings',
              'channel_horeca_tc',
              'channel_horeca_pc',
              'channel_ecom',
              'channel_ecom_mp',
              'channel_ecom_app',
              'channel_3pl',
              'detailed_address',
              'community_name',
              'city',
              'po_box',
              'emirate',
              'tl_issued_emirate',
              'trade_number',
              'establish_data',
              'tl_expiry_date',
              'category',
              'owner_name',
              'nationality_id',
              'owner_share',
              'vat_trn',
              'email',
              'credit_limit',
              'property_payment_term_id',
              'property_inbound_payment_method_line_id'
              'trade_license_attachment',
              'trade_license_file_name',
              'caf_attachment',
              'caf_file_name',
              'guarantees_copy_attachment',
              'guarantees_copy_file_name',
              'eid_attachment',
              'eid_file_name',
              'agreement_copy_attachment',
              'agreement_copy_file_name',
              'bank_statement_attachment',
              'bank_statement_file_name',
              'vat_trn_attachment',
              'vat_trn_file_name',
              'poer_attorney_attachment',
              'poer_attorney_file_name',
              'company_photo_attachment',
              'company_photo_file_name',
              'passport_copy_attachment',
              'passport_copy_file_name',
              'memorandum_association_attachment',
              'memorandum_association_file_name',
              'customer_type',
              'is_credit_hold',
              'credit_hold_reason_id'
              'delivery_receive_time',
              'is_key_account',
              ]

allow_first_time_fields = [
    'name',
    'vat_trn',
    'establish_data',
    'tl_expiry_date',
    'customer_type',
]

class ResPartnerAmendment(models.Model):
    _inherit = "res.partner"

    customer_amendment_ids = fields.One2many('customer.amendment', 'partner_id', string="Customer Amendment")
    customer_amendment_count = fields.Integer(compute="compute_customer_amendment_count")

    @api.depends('customer_amendment_ids')
    def compute_customer_amendment_count(self):
        for record in self:
            record.customer_amendment_count = len(record.customer_amendment_ids)

    def action_show_customer_amendment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Amendment {}'.format(self.name),
            'res_model': 'customer.amendment',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id','in',self.customer_amendment_ids.ids)]
        }

    def customer_amendment_bu_sales(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'BU Sales Amendment {}'.format(self.name),
            'res_model': 'customer.amendment',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_type': 'sales_amendment',
                'default_name': '{} OF Amendment'.format(self.name)
            },
            'target': 'current',
        }

    def customer_amendment_bu_scm(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'BU SCM Amendment {}'.format(self.name),
            'res_model': 'customer.amendment',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_type': 'scm_amendment',
                'default_name': '{} OF Amendment'.format(self.name)

            },
            'target': 'current',
        }

    def customer_amendment_ccd(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'BU CCD Amendment {}'.format(self.name),
            'res_model': 'customer.amendment',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_type': 'ccd_amendment',
                'default_name': '{} OF Amendment'.format(self.name)
            },
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        is_res_partner_action = self._context.get('is_res_partner_action')
        partners = super().create(vals_list)
        for partner in partners:
            if partner.contact_type in ['customer','supplier'] and is_res_partner_action and not self.env.context.get('default_registration_type') and partner.type != 'fsm_location':
                if partner.contact_type == 'customer':
                    contact_type = 'Customer'
                else:
                    contact_type = 'Vendor'
                raise ValidationError('Create {} from registration menu'.format(contact_type))
        return partners

    def write(self, vals):
        if not vals:
            return True
        if self.env.context.get('is_res_partner_action') and not self.env.context.get('from_customer_amendment'):
            for partner in self:
                if partner.contact_type == 'customer' and partner.active:
                    if 'credit_limit' in vals and (partner.credit_limit == vals.get('credit_limit')):
                        vals.pop('credit_limit')
                    readonly_fields = []
                    if self.env.user.has_group('gulfco_contact_registration_custom.group_ccd_approval'):
                        for field in bu_sales_field + bu_scm_field:
                            if field in vals:
                                old_value = getattr(partner, field)
                                new_value = vals[field]
                                if field in allow_first_time_fields:
                                    if old_value and old_value != new_value:
                                        readonly_fields.append(field)
                                elif old_value != new_value:
                                    readonly_fields.append(field)
                    else:
                        for field in bu_sales_field + bu_scm_field + ccd_fields:
                            if field in vals:
                                old_value = getattr(partner, field)
                                new_value = vals[field]
                                if field in allow_first_time_fields:
                                    if old_value and old_value != new_value:
                                        readonly_fields.append(field)
                                elif old_value != new_value:
                                    readonly_fields.append(field)
                    if readonly_fields:
                        raise UserError(_("You cannot modify the following readonly fields on Partner: %s",
                                          ', '.join(readonly_fields)))
                    # readonly_fields = [val for val in vals if val in bu_sales_field + bu_scm_field + ccd_fields]
                    # if readonly_fields:
                    #     raise UserError(_("You cannot modify the following readonly fields on Partner: %s",
                    #                       ', '.join(readonly_fields)))

        res = super(ResPartnerAmendment, self).write(vals)
        return res

