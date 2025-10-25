import logging
import re
_logger = logging.getLogger(__name__)
from odoo import models, fields, api
import base64
import openpyxl
import io
from datetime import date, datetime

class CustomerRegistrationWizard(models.TransientModel):
    _name = 'customer.registration.wizard'
    _description = 'Customer Registration Wizard'

    file = fields.Binary(string="Import XLSX File", required=True)
    filename = fields.Char(string='File_name')

    def create_data(self):
        record_ids = []
        try:
            decoded_file = base64.b64decode(self.file)
            workbook = openpyxl.load_workbook(filename=io.BytesIO(decoded_file))
            sheet = workbook.active
            headers = [cell.value.lower() if cell.value else '' for cell in sheet[3]]


            for row in sheet.iter_rows(min_row=4, values_only=True):
                data_dict = dict(zip(headers, row))
                customer_name = data_dict.get('customer name')
                customer_group_id = False
                if data_dict.get('customer group'):
                    customer_group = self.env['customer.group'].sudo().search([('name','=',data_dict.get('customer group'))])
                    if customer_group:
                        customer_group_id = customer_group.id
                # customer_group = data_dict.get('customer group')
                contact_type = data_dict.get('contact type')
                phone = data_dict.get('phone')
                mobile = data_dict.get('mobile')
                email = data_dict.get('email')
                channel = data_dict.get('channel')
                current_sub_channel = data_dict.get('sub channel')
                vat = data_dict.get('trn/tax id')
                outlet_code = data_dict.get('customer outlet code')
                outlet_short_name = data_dict.get('outlet short name')
                external_ref = data_dict.get('external reference')
                street = str(data_dict.get('street 1'))
                street2 = data_dict.get('street 2')
                city = data_dict.get('city')
                po_box = data_dict.get('po box')
                community_name = data_dict.get('province / community name')
                tl_issued_emirate = data_dict.get('tl issued from emirates')
                trade_number = data_dict.get('trade license number')
                establish_data = data_dict.get('established data')
                tl_expiry_date = datetime.strptime('28-5-2025', data_dict.get('tl expiry date')).date() if data_dict.get('tl expiry date') else False
                user_id = self._get_salesperson(data_dict.get('salesperson'))
                sales_leader_id = self._get_supervisor(data_dict.get("supervisor/salesman"))
                # x_customer_category = data_dict.get("customer category")
                credit_limit = data_dict.get("credit limit")
                x_owner_name = data_dict.get("owner name")
                x_owner_share = data_dict.get("owner share %")
                # x_emirates_id = data_dict.get("emirates id")
                customer_type = data_dict.get("customer type").lower()
                x_van_sales = True if data_dict.get("is van sales customer") == '=TRUE()' else False
                partner_latitude = float(data_dict.get("latitude")) or 0
                partner_longitude = float(data_dict.get("longitude")) or 0

                # Skip and log if required fields are missing
                # if not customer_name or not customer_type:
                #     skip_message = f"Skipped row - Missing required fields. CUSTOMER NAME: {customer_name}, CUSTOMER TYPE: {customer_type}"
                #     _logger.warning(skip_message)
                #     self.env['ir.logging'].sudo().create({
                #         'name': 'Customer Creation Skipped',
                #         'type': 'server',
                #         'level': 'warning',
                #         'dbname': self._cr.dbname,
                #         'message': skip_message,
                #         'path': 'res.partner',
                #         'line': 'N/A',
                #         'func': 'create_data',
                #     })
                #     continue
                try:
                    partner_vals = {
                        "sales_leader_id": sales_leader_id,
                        "user_id": user_id,
                        # "x_customer_category": x_customer_category,
                        "credit_limit": credit_limit,
                        "show_credit_limit": True,
                        "owner_name": x_owner_name,
                        'country_id': self._get_country(data_dict.get('nationality')),
                        "owner_share": int(x_owner_share) or 0,
                        # "x_emirates_id": x_emirates_id,
                        "customer_type": customer_type,
                        "is_van_sale_customer": x_van_sales,
                        "partner_latitude": partner_latitude,
                        "partner_longitude": partner_longitude,
                        'property_payment_term_id': self._get_payment_term(data_dict.get('customer payment terms')),
                        'tl_expiry_date': tl_expiry_date or '',
                        'establish_data': establish_data or '',
                        'trade_number': trade_number or '',
                        'tl_issued_emirate': tl_issued_emirate or '',
                        'community_name': community_name or '',
                        'po_box': po_box or '',
                        'outlet_short_name': outlet_short_name or '',
                        'external_ref': external_ref or '',
                        'outlet_code': outlet_code or '',
                        'street': street,
                        'street': street2,
                        'city': city,
                        'company_type': 'company' if contact_type.lower() == 'company' else 'person',
                        'contact_type': data_dict.get('contact type').lower() if data_dict.get('contact type') else False,
                        'name': customer_name or '',
                        'customer_group_id': customer_group_id,
                        'channel': channel or '',
                        'current_sub_channel': current_sub_channel or '',
                        'vat': vat or '',
                        'phone': phone or 'Put Customer Phone',
                        'mobile': mobile or 'Put Customer mobile',
                        'email': email or 'Put Customer Email',
                        'state_id': self._get_state(data_dict.get('state')),
                        'active': False,
                        'registration_type': 'customer_registration',
                    }

                    existing_customer = self.env['res.partner'].sudo().search([
                        '|',('email', '=', email),
                        ('phone', '=', phone), ('active', 'in', [True,False])
                    ], limit=1)

                    if not existing_customer:
                        customer = self.env['res.partner'].sudo().create(partner_vals)
                        record_ids.append(customer.id)
                    else:
                        record_ids.append(existing_customer.id)
                except Exception as e:
                    error_message = (
                        f"Error creating customer. NAME: {customer_name}, EMAIL: {email} - {str(e)}"
                    )
                    _logger.error(error_message)
                    self.env['ir.logging'].sudo().create({
                        'name': 'Customer Creation Error',
                        'type': 'server',
                        'level': 'error',
                        'dbname': self._cr.dbname,
                        'message': error_message,
                        'path': 'res.partner',
                        'line': 'N/A',
                        'func': 'create_data',
                    })
        except Exception as e:
            _logger.error(f"Error processing file: {str(e)}")

        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_contact_registration_custom.action_contacts_customer_registration")
        action['domain'] = [('id', 'in', record_ids),('active', '=', False), '|', ('registration_type', '=', 'customer_registration'), ('customer_rank', '>', 0)]
        action['context'] = {'default_is_company': True, 'default_registration_type':'customer_registration','default_active': False, 'default_contact_type': 'customer'}
        return action

    def _get_supervisor(self, supervisor):
        if not supervisor:
            return False
        supervisor_id = self.env['res.users'].sudo().search([('name', '=', supervisor)], limit=1)
        return supervisor_id.id if supervisor_id else False

    def _get_salesperson(self, salesperson):
        if not salesperson:
            return False
        user_id = self.env['res.users'].sudo().search([('name', '=', salesperson)], limit=1)
        return user_id.id if user_id else False

    def _get_state(self, state_name):
        if not state_name:
            return False
        state = self.env['res.country.state'].sudo().search([('name', 'ilike', state_name)], limit=1)
        return state.id if state else False

    def _get_country(self, country_name):
        if not country_name:
            return False
        country = self.env['res.country'].sudo().search([('name', '=', country_name)], limit=1)
        return country.id if country else False

    def _get_payment_term(self, payment_term_name):
        if not payment_term_name:
            return False
        payment_term = self.env['account.payment.term'].sudo().search([('name', '=', payment_term_name)], limit=1)
        return payment_term.id if payment_term else False

    def _get_payment_method(self, payment_method_name):
        if not payment_method_name:
            return False
        payment_method = self.env['account.payment.method'].sudo().search([('name', '=', payment_method_name)], limit=1)
        return payment_method.id if payment_method else False
