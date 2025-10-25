# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import base64
import json
from collections import defaultdict
from datetime import datetime, timedelta
from importlib.metadata import pass_none
from unittest import registerResult
import pytz

from dateutil.relativedelta import relativedelta

from odoo import fields, http, SUPERUSER_ID, _
from odoo.http import request, content_disposition
from odoo.tools import format_datetime, format_date, is_html_empty

_logger = logging.getLogger(__name__)


class ContactRegistration(http.Controller):

    @http.route('/get_bank_info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_bank_info(self, bank_id):
        bank = request.env['res.bank'].sudo().search(
            [('id', '=', int(bank_id))], limit=1)
        print("bank: details", bank, bank.name)
        return bank.name if bank else {}

    @http.route('/submit_vendor_registration', type='http', auth='public', methods=['POST'], website=True)
    def submit_vendor_registration(self, **kwargs):
        print("\n :submit vendore registation data:", kwargs)
        name = kwargs.get('company_name') or None
        email = kwargs.get('email') or None
        mobile = kwargs.get('mobile') or None
        telephone = kwargs.get('telephone') or None
        street = kwargs.get('complete_address')
        street2 = kwargs.get('area_zone_name')
        city = kwargs.get('city_name')
        zip = kwargs.get('zip_code')
        po_box = kwargs.get('po_box')
        website = kwargs.get('website_url')
        if kwargs.get('state_id'):
            state_id = request.env['res.country.state'].sudo().search([('id', '=', int(kwargs.get('state_id')))]).id
        else:
            state_id = None
        if kwargs.get('country_id'):
            country_id = request.env['res.country'].sudo().search([('id', '=', int(kwargs.get('country_id')))]).id
        else:
            country_id = None
        # country_id = kwargs.get('country_id')

        parent_group_name = kwargs.get('parent_group_name')


        # legal Document Data
        trade_number = kwargs.get('trade_license_no') or None
        issuance_authority = kwargs.get('issuance_authority') or None

        local_tz = pytz.timezone(request.env.user.tz or 'UTC')
        issue_date = datetime.strptime(kwargs.get('issued_date'), '%Y-%m-%d')
        local_issue_date = local_tz.localize(issue_date)

        expiry_date = datetime.strptime(kwargs.get('expiry_date'), '%Y-%m-%d')
        local_expiry_date = local_tz.localize(expiry_date)


        legal_document_issue_date = local_issue_date.date()
        legal_document_expiry_date = local_expiry_date.date()
        vat_trn = kwargs.get('trn')

        vendor_code = request.env['ir.sequence'].next_by_code('vendor.registration.code')

        # Here you can add logic to create a new user or store the data in a model
        # For example, creating a new res.users record
        vals = {'name': name,
                'email': email,
                'mobile': mobile,
                'phone': telephone,
                'street': street,
                # 'detailed_address': street,
                'street2': street2,
                'city': city,
                'zip': zip,
                'po_box': po_box,
                'website': website,
                'state_id': state_id,
                'country_id': country_id,
                'parent_group_name': parent_group_name,
                'company_type': 'company',

                # Legal Documents data
                'trade_number': trade_number,
                'issuance_authority': issuance_authority,
                'legal_document_issue_date': legal_document_issue_date,
                'legal_document_expiry_date': legal_document_expiry_date,
                'vat_trn': vat_trn,

                'unregistered_bank': kwargs.get('unregistered_bank') if kwargs.get('bank_not_found') else False,
                'vendor_code': vendor_code,



                # Mandatory data need to add
                'active': False,
                'registration_type': 'vendor_registration',
                'contact_type': 'supplier',
                'supplier_rank': 1,
                'vendor_state': 'draft',

               }




        registered_vendor = request.env['res.partner'].sudo().create(vals)
        print("registered_vendor:", registered_vendor)

        if kwargs.get('owner_name') and kwargs.get('owner_email'):
            owner_vals = {
                'type': 'contact',
                'parent_id': registered_vendor.id,
                'name': kwargs.get('owner_name'),
                'phone': kwargs.get('owner_tel') or None,
                'mobile': kwargs.get('owner_mobile') or None,
                'email': kwargs.get('owner_email') or None,

            }
            vendor_contact = request.env['res.partner'].create(owner_vals)
        if kwargs.get('signatory_name') and kwargs.get('signatory_email'):
            signatory_vals = {
                'type': 'contact',
                'parent_id': registered_vendor.id,
                'name': kwargs.get('signatory_name'),
                'phone': kwargs.get('signatory_tel') or None,
                'mobile': kwargs.get('signatory_mobile') or None,
                'email': kwargs.get('signatory_email') or None,

            }
            vendor_contact = request.env['res.partner'].create(signatory_vals)
        if kwargs.get('finance_manager_name') and kwargs.get('finance_manager_email'):
            finance_manager_vals = {
                'type': 'contact',
                'parent_id': registered_vendor.id,
                'name': kwargs.get('finance_manager_name'),
                'phone': kwargs.get('finance_manager_tel') or None,
                'mobile': kwargs.get('finance_manager_mobile') or None,
                'email': kwargs.get('finance_manager_email') or None,

            }
            vendor_contact = request.env['res.partner'].create(finance_manager_vals)
        if kwargs.get('sales_manager_name') and kwargs.get('sales_manager_email'):
            sales_manager_vals = {
                'type': 'contact',
                'parent_id': registered_vendor.id,
                'name': kwargs.get('sales_manager_name'),
                'phone': kwargs.get('sales_manager_tel') or None,
                'mobile': kwargs.get('sales_manager_mobile') or None,
                'email': kwargs.get('sales_manager_email') or None,

            }
            vendor_contact = request.env['res.partner'].create(sales_manager_vals)


        #  Document upload Data
        trade_license_attachment = request.httprequest.files.get('trade_license_attachment')
        if trade_license_attachment:
            # Read the file and encode it in base64
            trade_license_attachment_data = base64.b64encode(trade_license_attachment.read())
            trade_license_attachment_name = trade_license_attachment.filename

            # Update the partner record with the binary data
            registered_vendor.write({
                'trade_license_attachment': trade_license_attachment_data,
                'trade_license_file_name': trade_license_attachment_name,
            })

        vat_certificates = request.httprequest.files.get('vat_certificates')
        if vat_certificates:
            # Read the file and encode it in base64
            vat_certificates_data = base64.b64encode(vat_certificates.read())
            vat_certificates_name = vat_certificates.filename

            # Update the partner record with the binary data
            registered_vendor.write({
                'vat_trn_attachment': vat_certificates_data,
                'vat_trn_file_name': vat_certificates_name,
            })

        bank_latter_acc_no = request.httprequest.files.get('bank_latter_acc_no')
        if bank_latter_acc_no:
            # Read the file and encode it in base64
            bank_latter_acc_no_data = base64.b64encode(bank_latter_acc_no.read())
            bank_latter_acc_no_name = bank_latter_acc_no.filename

            # Update the partner record with the binary data
            registered_vendor.write({
                'bank_account_attachment': bank_latter_acc_no_data,
                'bank_account_attachment_file_name': bank_latter_acc_no_name,
            })

        noc_trans_payment = request.httprequest.files.get('noc_trans_payment')
        if noc_trans_payment:
            # Read the file and encode it in base64
            noc_trans_payment_data = base64.b64encode(noc_trans_payment.read())
            noc_trans_payment_name = noc_trans_payment.filename

            # Update the partner record with the binary data
            registered_vendor.write({
                'noc_payment_attachment': noc_trans_payment_data,
                'noc_payment_file_name': noc_trans_payment_name,
            })

        vendor_register_vrf = request.httprequest.files.get('vendor_register_vrf')
        if noc_trans_payment:
            # Read the file and encode it in base64
            vendor_register_vrf_data = base64.b64encode(vendor_register_vrf.read())
            vendor_register_vrf_name = vendor_register_vrf.filename

            # Update the partner record with the binary data
            registered_vendor.write({
                'vendor_registration_attachment': vendor_register_vrf_data,
                'vendor_registration_file_name': vendor_register_vrf_name,
            })

        other_docs = request.httprequest.files.get('other_docs')
        if other_docs:
            # Read the file and encode it in base64
            other_docs_data = base64.b64encode(other_docs.read())
            other_docs_name = other_docs.filename

            # Update the partner record with the binary data
            registered_vendor.write({
                'other_attachment': other_docs_data,
                'other_attachment_file_name': other_docs_name,
            })

        #  Bank Account Data for partner
        acc_number = kwargs.get('account_number')
        account_name = kwargs.get('account_name')
        branch_name = kwargs.get('bank_branch_name')
        if kwargs.get('bank_id'):
            bank_id = request.env['res.bank'].sudo().search([('id', '=', int(kwargs.get('bank_id')))]).id
        else:
            bank_id = None
        branch_code = kwargs.get('branch_code')
        iban_number = kwargs.get('iban')
        sort_code = kwargs.get('sort_code')
        swift_number = kwargs.get('swift_code')
        if kwargs.get('currency_id'):
            currency_id = request.env['res.currency'].sudo().search([('id', '=', int(kwargs.get('currency_id')))]).id
            registered_vendor.write({
                'property_purchase_currency_id': currency_id,
            })
        else:
            currency_id = None

        bank_vals = {
            'acc_number': acc_number,
            'partner_id': registered_vendor.id,
            'account_name': account_name,
            'branch_name': branch_name,
            'bank_id': bank_id,
            'branch_code': branch_code,
            'iban_number': iban_number,
            'swift_number': swift_number,
            'sort_code': sort_code,
            'currency_id': currency_id,
        }

        registered_vendor_bank = request.env['res.partner.bank'].sudo().create(bank_vals)

        return request.render(
            'gulfco_contact_registration_custom.request_registration_submit_response',
        )

    @http.route('/submit_customer_registration', type='http', auth='public', methods=['POST'], website=True)
    def submit_customer_registration(self, **kwargs):
        print("\n :submit Customer data:", kwargs)
        name = kwargs.get('customer_name') or None
        company_type = kwargs.get('company_type') or None
        email = kwargs.get('email') or None
        mobile = kwargs.get('mobile') or None
        telephone = kwargs.get('telephone') or None
        street = kwargs.get('complete_address')
        street2 = kwargs.get('area_zone_name')
        city = kwargs.get('city_name')
        zip = kwargs.get('zip_code')
        po_box = kwargs.get('po_box')
        website = kwargs.get('website_url')
        if kwargs.get('state_id'):
            state_id =  request.env['res.country.state'].sudo().search([('id', '=', int(kwargs.get('state_id')))]).id
        else:
            state_id = None
        if kwargs.get('country_id'):
            country_id =  request.env['res.country'].sudo().search([('id', '=', int(kwargs.get('country_id')))]).id
        else:
            country_id = None
        # country_id = kwargs.get('country_id')


        customer_type = kwargs.get('customer_type') or None
        customer_category = kwargs.get('customer_category') or None
        trn = kwargs.get('customer_trn') or None
        establish_data = kwargs.get('establish_data') or None
        tl_expiry_date = kwargs.get('tl_expiry_date') or None

        local_tz = pytz.timezone(request.env.user.tz or 'UTC')
        tl_expiry_date = datetime.strptime(kwargs.get('tl_expiry_date'), '%Y-%m-%d')
        local_tl_expiry_date = local_tz.localize(tl_expiry_date)


        legal_local_tl_expiry_date = local_tl_expiry_date.date()

        #perssonla info Data
        if kwargs.get('nationality'):
            nationality_id =  request.env['res.country'].sudo().search([('id', '=', int(kwargs.get('nationality')))]).id
        else:
            nationality_id = None
        # kwargs.get('nationality') or None
        emirate_id = kwargs.get('emirate_id') or None

        tl_issued_emirate = kwargs.get('trade_license_issue') or None
        trade_number = kwargs.get('trade_license') or None

        #channel info data
        channel = kwargs.get('channel') or None

        #outlet info data
        external_ref = kwargs.get('ext_reference') or None

        #owner info data
        owner_name = kwargs.get('owner_name')
        owner_share = kwargs.get('owner_share')

        # Here you can add logic to create a new user or store the data in a model
        # For example, creating a new res.users record
        vals = {'name': name,
                'email': email,
                'mobile': mobile,
                'phone': telephone,
                'street': street,
                # 'detailed_address': street,
                'street2': street2,
                'city': city,
                'zip': zip,
                'po_box': po_box,
                'website':website,
                'state_id': state_id,
                'country_id': country_id,

                'customer_type': customer_type,
                'category': customer_category,
                'vat_trn' : trn,

                #personal Info Data
                'nationality_id': nationality_id,
                'emirate': emirate_id,
                # 'emirate_id': emirate,
                'tl_issued_emirate': tl_issued_emirate,
                'trade_number': trade_number,
                'establish_data': establish_data,
                'tl_expiry_date': legal_local_tl_expiry_date or None,

                #channel Info data:
                'channel': channel,
                    # dependent channel values added after  create records

                #outlet info
                # 'outlet_code': outlet_code,
                # 'outlet_short_name': outlet_short_name,
                'external_ref': external_ref,

                #owner info data
                'owner_name': owner_name,
                'owner_share': owner_share,


                # Mandatory Data to register
                'active': False,
                'registration_type': 'customer_registration',
                'contact_type': 'customer',
                'company_type': company_type,
                'customer_rank': 1,
                'create_source': 'portal',
                }

        if customer_type == 'cash':
            vals['customer_cash_state'] = 'customer_create_request'
        elif customer_type == 'credit':
            vals['customer_credit_state'] = 'customer_create_request'

        registered_customer = request.env['res.partner'].sudo().create(vals)

        if registered_customer.channel == 'MT':
            registered_customer.channel_mt = kwargs.get('sub_channel1')
            if registered_customer.channel_mt == 'HyperMarket':
                registered_customer.channel_mt_hyper = kwargs.get('sub_channel2')
            elif registered_customer.channel_mt == 'SuperMarket':
                registered_customer.channel_mt_super = kwargs.get('sub_channel2')

        elif registered_customer.channel == 'GT':
            registered_customer.channel_gt = kwargs.get('sub_channel1')
            if registered_customer.channel_gt == 'Grocery':
                registered_customer.channel_gt_grocery = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'ConvenienceStore':
                registered_customer.channel_gt_cs = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'Supermarket':
                registered_customer.channel_gt_super = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'PetrolStation':
                registered_customer.channel_gt_petrol = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'DiscountCenter':
                registered_customer.channel_gt_discount = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'Wholesale':
                registered_customer.channel_gt_wholesale = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'TradingCompany':
                registered_customer.channel_gt_tc = kwargs.get('sub_channel2')
            elif registered_customer.channel_gt == 'SpecialAccounts':
                registered_customer.channel_gt_sc = kwargs.get('sub_channel2')
                
        elif registered_customer.channel == 'HORECA':
            registered_customer.channel_horeca = kwargs.get('sub_channel1')
            if registered_customer.channel_horeca == 'HotelsandResorts':
                registered_customer.channel_horeca_hr = kwargs.get('sub_channel2')
            elif registered_customer.channel_horeca == 'RestaurantandCafe':
                registered_customer.channel_horeca_rc = kwargs.get('sub_channel2')
            elif registered_customer.channel_horeca == 'SpecialAccount':
                registered_customer.channel_horeca_sa = kwargs.get('sub_channel2')
            elif registered_customer.channel_horeca == 'Caterings':
                registered_customer.channel_horeca_caterings = kwargs.get('sub_channel2')
            elif registered_customer.channel_horeca == 'HORECATradingCompany':
                registered_customer.channel_horeca_tc = kwargs.get('sub_channel2')
            elif registered_customer.channel_horeca == 'PubsandClubs':
                registered_customer.channel_horeca_pc = kwargs.get('sub_channel2')
            
        elif registered_customer.channel == 'E-Com':
            registered_customer.channel_ecom = kwargs.get('sub_channel1')
            if registered_customer.channel_ecom == 'OnlineMarketPlace':
                registered_customer.channel_ecom_mp = kwargs.get('sub_channel2')
            elif registered_customer.channel_ecom == 'DeliveryApps':
                registered_customer.channel_ecom_app = kwargs.get('sub_channel2')

        elif registered_customer.channel == '3PL':
            registered_customer.channel_3pl = kwargs.get('sub_channel1')



        print("registered_customer:", registered_customer)
        print("\nn jjjj")
        contact_vals = {
            'type': 'contact',
            'parent_id': registered_customer.id,
            'name': kwargs.get('contact_name'),
            'phone': kwargs.get('contact_tel') or None,
            'mobile': kwargs.get('contact_mobile') or None,
            'email': kwargs.get('contact_email') or None,

        }
        customer_contact = request.env['res.partner'].create(contact_vals)

        print("===customer_contact:", customer_contact)

        #  Document upload Data
        trade_license_attachment = request.httprequest.files.get('trade_license_attachment')
        if trade_license_attachment:
            # Read the file and encode it in base64
            trade_license_attachment_data = base64.b64encode(trade_license_attachment.read())
            trade_license_attachment_name = trade_license_attachment.filename

            # Update the partner record with the binary data
            registered_customer.write({
                'trade_license_attachment': trade_license_attachment_data,
                'trade_license_file_name': trade_license_attachment_name,
            })

        vat_certificates_attachment = request.httprequest.files.get('vat_certificates')
        if vat_certificates_attachment:
            # Read the file and encode it in base64
            vat_certificates_data = base64.b64encode(vat_certificates_attachment.read())
            vat_certificates_name = vat_certificates_attachment.filename

            # Update the partner record with the binary data
            registered_customer.write({
                'vat_trn_attachment': vat_certificates_data,
                'vat_trn_file_name': vat_certificates_name,
            })

        bank_statement_six_month_attachment = request.httprequest.files.get('bank_statement_of_six_month')
        if vat_certificates_attachment:
            # Read the file and encode it in base64
            bank_statement_data = base64.b64encode(bank_statement_six_month_attachment.read())
            bank_statement_name = bank_statement_six_month_attachment.filename

            # Update the partner record with the binary data
            registered_customer.write({
                'bank_statement_attachment': bank_statement_data,
                'bank_statement_file_name': bank_statement_name,
            })

        caf_attachment_attachment = request.httprequest.files.get('caf_attachment')
        if vat_certificates_attachment:
            # Read the file and encode it in base64
            caf_attachment_data = base64.b64encode(caf_attachment_attachment.read())
            caf_attachment_name = caf_attachment_attachment.filename

            # Update the partner record with the binary data
            registered_customer.write({
                'caf_attachment': caf_attachment_data,
                'caf_file_name': caf_attachment_name,
            })

        customer_guarantees_copy_attachment = request.httprequest.files.get('customer_guarantees_copy')
        if vat_certificates_attachment:
            # Read the file and encode it in base64
            customer_guarantees_copy_data = base64.b64encode(customer_guarantees_copy_attachment.read())
            customer_guarantees_copy_name = customer_guarantees_copy_attachment.filename

            # Update the partner record with the binary data
            registered_customer.write({
                'guarantees_copy_attachment': customer_guarantees_copy_data,
                'guarantees_copy_file_name': customer_guarantees_copy_name,
            })

        customer_eid_copy_attachment = request.httprequest.files.get('customer_eid_copy')
        if vat_certificates_attachment:
            # Read the file and encode it in base64
            customer_eid_copy_data = base64.b64encode(customer_eid_copy_attachment.read())
            customer_eid_copy_name = customer_eid_copy_attachment.filename

            # Update the partner record with the binary data
            registered_customer.write({
                'eid_attachment': customer_eid_copy_data,
                'eid_file_name': customer_eid_copy_name,
            })

        return request.render(
            'gulfco_contact_registration_custom.request_registration_submit_response',
        )

    @http.route('/portal/get_states', type='json', auth="public", website=True)
    def get_states_for_portal(self, country_id):
        print("\n\n insid cotroller:", self, country_id)
        try:
            states = request.env['res.country.state'].sudo().search([('country_id', '=', int(country_id))])
            state_list = [{'id': state.id, 'name': state.name} for state in states]
            print("statelist:", state_list)
            return state_list
        except Exception as e:
            return [{'None': 'There is no state Found.'}]
            # json.dumps([])

    # /get/channel/1
    @http.route('/get/channel/1', type='json', auth="public", website=True)
    def get_sub_channel_1(self, channel_id):
        print("\n\n insid sub chnnel 1:", self, channel_id)
        # try:
        channel_list = []
        if channel_id == 'MT':
            channel_list.append({'key':'HyperMarket', 'value':'Hyper Market',})
            channel_list.append({'key':'SuperMarket', 'value':'Super Market'})
        elif channel_id == 'GT':
                channel_list.append({'key': 'Grocery', 'value': 'Grocery'},)
                channel_list.append({'key': 'ConvenienceStore', 'value': 'Convenience Store'},)
                channel_list.append({'key': 'Supermarket', 'value': 'Supermarket'},)
                channel_list.append({'key': 'PetrolStation', 'value': 'Petrol Station'},)
                channel_list.append({'key': 'DiscountCenter', 'value': 'Discount Center'},)
                channel_list.append({'key': 'Wholesale', 'value': 'Wholesale'},)
                channel_list.append({'key': 'TradingCompany', 'value': 'Trading Company'},)
                channel_list.append({'key': 'SpecialAccounts', 'value': 'Special Accounts'})
        elif channel_id == 'HORECA':
            channel_list.append({'key': 'HotelsandResorts', 'value': 'Hotels and Resorts'}, )
            channel_list.append({'key': 'RestaurantandCafe', 'value': 'Restaurant and Cafe'}, )
            channel_list.append({'key': 'SpecialAccount', 'value': 'Special Account'}, )
            channel_list.append({'key': 'Caterings', 'value': 'Caterings'}, )
            channel_list.append({'key': 'HORECATradingCompany', 'value': 'HORECA Trading Company'}, )
            channel_list.append({'key': 'PubsandClubs', 'value': 'Pubs and Clubs'}, )
        elif channel_id == 'E-Com':
            channel_list.append({'key': 'OnlineMarketPlace', 'value': 'Online Market Place'}, )
            channel_list.append({'key': 'DeliveryApps', 'value': 'Delivery Apps'}, )
        elif channel_id == '3PL':
            channel_list.append({'key': 'Sales', 'value': 'Sales'}, )
            channel_list.append({'key': 'Logistic', 'value': 'Logistic'}, )
        else:
            return [{'None': 'There is no Channel Found.'}]
        return channel_list
            # states = request.env['res.country.state'].sudo().search([('country_id', '=', int(country_id))])
            # state_list = [{'id': state.id, 'name': state.name} for state in states]
            # print("statelist:", state_list)
            # return state_list
        # except Exception as e:
        #     return [{'None': 'There is no state Found.'}]
            # json.dumps([])

        # /get/channel/2

    @http.route('/get/sub/channel/2', type='json', auth="public", website=True)
    def get_sub_channel_2(self, sub_channel_id):
        print("\n\n insid sub chnnel 2:", self, sub_channel_id)
        # try:
        # MT Channel
        channel_list = []
        if sub_channel_id == 'HyperMarket':
            channel_list.append({'key': 'ChainHM', 'value': 'Chain HM'},)
            channel_list.append({'key': 'COOP', 'value': 'COOP'})
        elif sub_channel_id == 'SuperMarket':
            channel_list.append({'key': 'ChainSM', 'value': 'Chain SM'}, )
            channel_list.append({'key': 'COOP', 'value': 'COOP'})


        # GT Channel
        elif sub_channel_id == 'Grocery':
            channel_list.append({'key': 'GroceryA', 'value': 'Grocery A'}, )
            channel_list.append({'key': 'GroceryB', 'value': 'Grocery B'}, )
            channel_list.append({'key': 'GroceryC', 'value': 'Grocery c'}, )
        elif sub_channel_id == 'ConvenienceStore':
            channel_list.append({'key': 'ConvenienceA', 'value': 'Convenience A'}, )
            channel_list.append({'key': 'ConvenienceB', 'value': 'Convenience B'}, )
            channel_list.append({'key': 'PetrolStation-A', 'value': 'Petrol Station-A'}, )
            channel_list.append({'key': 'PetrolStation-B', 'value': 'Petrol Station-B'}, )
            channel_list.append({'key': 'PetrolStation-C', 'value': 'Petrol Station-C'}, )
        elif sub_channel_id == 'Supermarket':
            channel_list.append({'key': 'SM-A', 'value': 'SM-A'}, )
            channel_list.append({'key': 'SM-B', 'value': 'SM-B'}, )
            channel_list.append({'key': 'COOP', 'value': 'COOP'}, )
        elif sub_channel_id == 'PetrolStation':
            channel_list.append({'key': 'PS-A', 'value': 'PS-A'}, )
            channel_list.append({'key': 'PS-B', 'value': 'PS-B'}, )
            channel_list.append({'key': 'PS-C', 'value': 'PS-C'}, )
        elif sub_channel_id == 'DiscountCenter':
            channel_list.append({'key': 'DiscountCenter', 'value': 'Discount Center'}, )
        elif sub_channel_id == 'Wholesale':
            channel_list.append({'key': 'Wholesale', 'value': 'Wholesale'}, )
        elif sub_channel_id == 'TradingCompany':
            channel_list.append({'key': 'TradingCompany', 'value': 'Trading Company'}, )
            channel_list.append({'key': 'Roasteries', 'value': 'Roasteries'}, )
        elif sub_channel_id == 'SpecialAccounts':
            channel_list.append({'key': 'Pharmacy', 'value': 'Pharmacy'})
            channel_list.append({'key': 'Roasteries', 'value': 'Roasteries'})
            channel_list.append({'key': 'ShipChandlers', 'value': 'Ship Chandlers'})
            channel_list.append({'key': 'Others', 'value': 'Others'})


        # HORECA Channel
        elif sub_channel_id == 'HotelsandResorts':
            channel_list.append({'key': 'Chain', 'value': 'Chain'})
            channel_list.append({'key': 'Single', 'value': 'Single'})
        elif sub_channel_id == 'RestaurantandCafe':
            channel_list.append({'key': 'Chain', 'value': 'Chain'})
            channel_list.append({'key': 'Single', 'value': 'Single'})
        elif sub_channel_id == 'SpecialAccount':
            channel_list.append({'key': 'AirportLounge', 'value': 'Airport Lounge'},)
            channel_list.append({'key': 'SportsLeisures', 'value': 'Sports Leisures'},)
            channel_list.append({'key': 'Roasteries', 'value': 'Roasteries'},)
            channel_list.append({'key': 'Education', 'value': 'Education'},)
            channel_list.append({'key': 'GovernmentEntities', 'value': 'Government Entities'},)
            channel_list.append({'key': 'JAMGroup', 'value': 'JAM Group'},)
            channel_list.append({'key': 'Cinemas', 'value': 'Cinemas'},)
            channel_list.append({'key': 'Hospitals', 'value': 'Hospitals'},)
            channel_list.append({'key': 'Pharmacy', 'value': 'Pharmacy'},)
            channel_list.append({'key': 'ShipChandlers', 'value': 'Ship Chandlers'},)
            channel_list.append({'key': 'Others', 'value': 'Others'})
        elif sub_channel_id == 'Caterings':
            channel_list.append({'key': 'Caterings', 'value': 'Caterings'})
            channel_list.append({'key': 'Airlines', 'value': 'Airlines'})
        elif sub_channel_id == 'HORECATradingCompany':
            channel_list.append({'key': 'HORECATradingCompany', 'value': 'HORECA Trading Company'})
        elif sub_channel_id == 'PubsandClubs':
            channel_list.append({'key': 'PubsandClubs', 'value': 'Pubsand Clubs'})

        # E-COM Channel
        elif sub_channel_id == 'OnlineMarketPlace':
            channel_list.append({'key': 'OnlineMarketPlace', 'value': 'Online Market Place'}, )
        elif sub_channel_id == 'DeliveryApps':
            channel_list.append({'key': 'DeliveryApps', 'value': 'Delivery Apps'}, )

        # '3PL' Channel  --- There is no sub channel 2 for 3PL channel
        # elif sub_channel_id in ['Sales', 'Logistic']:
            # channel_list.append({'key': '', 'value': 'Data not define'}, )
        #     channel_list.append({'key': 'Sales', 'value': 'Sales'}, )
        #     channel_list.append({'key': 'Logistic', 'value': 'Logistic'}, )
        else:
            return [{'None': 'There is no Channel Found.'}]
        return channel_list

    @http.route('/portal/trade_license/check', type='json', auth='public')
    def portal_check_trade_license(self, tr):
        exists = request.env['res.partner'].sudo().search_count([
            ('trade_number', '=', tr)
        ]) > 0
        return {'exists': exists}