import logging
import re
_logger = logging.getLogger(__name__)
from odoo import models, fields, api
import base64
import openpyxl
import io
from datetime import datetime, date


class ProductRegistrationWizard(models.TransientModel):
    _name = 'product.registration.wizard'
    _description = 'Product Registration Wizard'

    file = fields.Binary(string="Import XLSX File", required=True)
    filename = fields.Char(string='File_name')

    def create_data(self):
        try:
            decoded_file = base64.b64decode(self.file)
            workbook = openpyxl.load_workbook(filename=io.BytesIO(decoded_file))
            sheet = workbook.active
            # Extract headers from the second row and Remove also None Value in Header And all Alphabet to convert lower case
            headers = [cell.value.lower() for cell in sheet[2] if cell.value is not None]
            record_ids = []
            # division = self.env['product.template'].fields_get('division')['division']['selection']
            # division_key = {label: key for key, label in division}
            for row in sheet.iter_rows(min_row=3, values_only=True):
                # filtered_row = [value for value in row if value is not None]
                # data_dict = dict(zip(headers, filtered_row))
                data_dict = dict(zip(headers, row))
                division_name = False
                if data_dict.get('product category/ division').lower() in ['food', 'mars']:
                    division_name = data_dict.get('product category/ division').lower()
                elif re.sub(r'[^\w]', '', data_dict.get('product category/ division')) in ['NonFood', 'nonfood', 'NONFOOD']:
                    division_name = 'non_food'

                item_code = data_dict.get('item gulfco code')
                barcode = data_dict.get('barcode (is barcode per eah)')

                # Skip and log if required fields are missing
                if not item_code:
                    skip_message = f"Skipped row - Missing required fields. ITEM CODE: {item_code}"
                    _logger.warning(skip_message)
                    self.env['ir.logging'].sudo().create({
                        'name': 'Product Creation Skipped',
                        'type': 'server',
                        'level': 'warning',
                        'dbname': self._cr.dbname,
                        'message': skip_message,
                        'path': 'product.template',
                        'line': 'N/A',
                        'func': 'create_data',
                    })
                    continue

                try:
                    uom_id = self._get_uom(data_dict.get('uom'))
                    costing_dept_code_id = self._get_costing_dept(data_dict.get('costing dept code'),data_dict.get('costing dept plan'))
                    brand_id = self._get_or_create_brand(data_dict.get('brand'))
                    supplier_id = self._get_or_create_supplier(data_dict.get('supplier'))
                    route_id = self._get_route(data_dict.get('promotion/regular')) if data_dict.get(
                        'promotion/regular') in ['REGULAR', 'PROMOTION'] else False
                    categ_id = self._get_or_create_category(data_dict)
                    product_vals = {
                        'item_type': 'tradable' if data_dict.get('item type') == 'Goods (Storable) Tracable ' else 'consumable',
                        'is_storable': True if data_dict.get('item type') == 'Goods (Storable) Tracable ' else False,
                        'active': False,
                        'sale_ok': True if data_dict.get('can be sales') in ['=TRUE()', True, 1] else False,
                        'purchase_ok': True if data_dict.get('can be purchase') in ['=TRUE()', True, 1] else False,
                        'govt_auth_name': data_dict.get('govt authority name') or 'Put Govt Authority Name',
                        'govt_comments': data_dict.get('comments from govt authority') or 'Put GOVT Comment',
                        'registration_date': date.today().strftime("%Y-%m-%d"),
                        'default_code': item_code or 'Put Internal Reference',
                        'name': data_dict.get('description in english') or 'Put the Product Name',
                        'item_description': data_dict.get('description in english') or 'Put Product Description',
                        'uom_id': uom_id,
                        'division': division_name,
                        'costing_dept_code_id': costing_dept_code_id,
                        'barcode': barcode or 'Put The Barcode',
                        'brand_id': brand_id,
                        'categ_id': categ_id,
                        'storage_condition': data_dict.get('storage condition'),
                        'sale_clearance_required': data_dict.get('is municipality clearance required for sale') == 'Y'[0],
                    }

                    if route_id:
                        product_vals['route_ids'] = [(6, 0, [route_id])]
                    if supplier_id:
                        product_vals['seller_ids'] = [(0, 0, {'partner_id': supplier_id})]

                    existing_product = self.env['product.template'].sudo().search([
                        ('barcode', '=', barcode)
                    ], limit=1)

                    if not existing_product or not barcode:
                        product = self.env['product.template'].sudo().create(product_vals)
                        record_ids.append(product.id)
                        # product.product_variant_ids.sudo().write({
                        #     'packaging_ids': [(0, 0, {'name': data_dict.get('Packaging'), 'sales': True, 'purchase': True})]
                        # })
                except Exception as e:
                    error_message = (
                        f"Error creating product. ITEM CODE: {item_code}, "
                        f"Barcode: {barcode} - {str(e)}"
                    )
                    _logger.error(error_message)
                    self.env['ir.logging'].sudo().create({
                        'name': 'Product Creation Error',
                        'type': 'server',
                        'level': 'error',
                        'dbname': self._cr.dbname,
                        'message': error_message,
                        'path': 'product.template',
                        'line': 'N/A',
                        'func': 'create_data',
                    })

        except Exception as e:
            _logger.error(f"Error processing file: {str(e)}")

        action = self.env["ir.actions.actions"]._for_xml_id("product_registration.product_registration_action")
        action['domain'] = ['|', '&', ('active', 'in', [False]), ('registration_status', '=', 'approved'), '&',
                            ('active', 'in', [False]), ('registration_status', '!=', 'approved'),
                            ('id', 'in', record_ids)]
        return action

    def _get_uom(self, uom_name):
        if not uom_name:
            return False
        uom = self.env['uom.uom'].sudo().search([('name', '=', uom_name)], limit=1)
        return uom.id if uom else False

    def _get_costing_dept(self, dept_name, plan):
        if not dept_name:
            return False
        dept = self.env['account.analytic.account'].sudo().search([('name', '=', dept_name)], limit=1)
        if not dept and plan:
            plan_id = self.env['account.analytic.plan'].sudo().search([('name', '=', plan)], limit=1)
            if not plan_id:
                plan_id = self.env['account.analytic.plan'].sudo().create({
                    'name': plan
                })
            dept = self.env['account.analytic.account'].sudo().create({
                'name': dept_name,
                'plan_id':plan_id.id
            })
        return dept.id if dept else False

    def _get_or_create_brand(self, brand_name):
        if not brand_name:
            return False
        brand = self.env['product.brand'].sudo().search([('name', '=', brand_name)], limit=1)
        return brand.id if brand else self.env['product.brand'].sudo().create({'name': brand_name}).id

    def _get_or_create_supplier(self, supplier_name):
        if not supplier_name:
            return False
        supplier = self.env['res.partner'].sudo().search([('name', '=', supplier_name)], limit=1)
        return supplier.id if supplier else self.env['res.partner'].sudo().create(
            {'name': supplier_name, 'contact_type': 'supplier'}).id

    def _get_route(self, route_name):
        if not route_name:
            return False
        search_field = 'is_buy_route' if route_name == 'REGULAR' else 'is_manufacture_route'
        route = self.env['stock.route'].sudo().search([(search_field, '=', True)], limit=1)
        return route.id if route else False

    def _get_or_create_category(self, data_dict):
        """ Create or retrieve category structure """
        category_fields = [
            ('main category', None),
            ('category(parent2)', 'parent1'),
            ('sub category 1', 'parent2'),
            ('sub category 2', 'sub_category_1'),
            ('sub category 3', 'sub_category_2')
        ]

        parent_id = None
        for field, parent_key in category_fields:
            category_name = data_dict.get(field)
            if not category_name:
                continue

            category = self.env['product.category'].sudo().search([
                ('name', '=', category_name)
            ], limit=1)

            if not category:
                category = self.env['product.category'].sudo().create({
                    'name': category_name,
                    'parent_id': parent_id
                })
            parent_id = category.id

        return parent_id