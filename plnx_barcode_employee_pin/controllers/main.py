# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from werkzeug import exceptions

from odoo import http
from odoo.http import request
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController

class StockBarcodeControllerExt(StockBarcodeController):
    @http.route('/stock_barcode/get_barcode_data', type='json', auth='user')
    def get_barcode_data(self, model, res_id, emp_id=None):
        employee_id = False
        if emp_id:
            employee_id = request.env['hr.employee'].browse(int(emp_id))

        if not res_id:
            target_record = request.env[model].with_context(allowed_company_ids=self._get_allowed_company_ids())
        else:
            target_record = request.env[model].browse(res_id).with_context(
                allowed_company_ids=self._get_allowed_company_ids())
        if employee_id and model == 'stock.picking' and target_record and (target_record.is_pick_type or target_record.is_out_type):
            data = target_record.with_context(employee_id=employee_id)._get_stock_barcode_data()
        else:
            data = target_record._get_stock_barcode_data()
        data['records'].update(self._get_barcode_nomenclature())
        data['precision'] = request.env['decimal.precision'].precision_get('Product Unit of Measure')
        mute_sound = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.mute_sound_notifications')
        data['config'] = data.get('config', {})
        data['config']['play_sound'] = bool(not mute_sound or mute_sound == "False")
        data['config']['barcode_separator_regex'] = request.env['ir.config_parameter'].sudo().get_param(
            'stock_barcode.barcode_separator_regex', '.^')
        data['config']['barcode_rfid_batch_time'] = int(
            request.env['ir.config_parameter'].sudo().get_param('stock_barcode.barcode_rfid_batch_time', 1000))
        delay_between_scan = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.delay_between_scan')
        if delay_between_scan and delay_between_scan.isnumeric():
            data['config']['delay_between_scan'] = int(delay_between_scan)
        return {
            'data': data,
            'groups': self._get_groups_data(),
        }

class BarcodePinController(http.Controller):

    @http.route('/my/barcode/user/pickings', type='json', auth='user')
    def get_user_pickings(self, emp_id=None):
        employee_id = request.env['hr.employee'].browse(int(emp_id))
        moves =  request.env['stock.move'].sudo().search(['|',
            ('picker_partner_id', '=', employee_id.work_contact_id.id),
            ('forklift_partner_id', '=', employee_id.work_contact_id.id),('state', 'not in', ['cancel', 'done', 'draft']),('picking_type_id', '!=', False)])

        pickings = request.env['stock.picking'].sudo().search([
            ('id', 'in', moves.mapped('picking_id').ids)
        ])

        return [
            {
                'id': p.id,
                'name': p.name,
                'origin': p.origin,
                'picking_type_code': p.picking_type_code,
                'picking_type_id': p.picking_type_id,
                'picking_type_name': p.picking_type_id.name,
            }
            for p in pickings
        ]


    @http.route("/validate/stock_quant/employee/barcode/", type="json", auth="public")
    def get_employee_barcode_stock_quant(self, access_pin, res_id, res_model, **kwargs):
        'return stock quant'
        return request.env["hr.employee"].get_employees_barcode_stock_quant_pin_validated(str(access_pin), res_id, res_model)

    @http.route("/validate/batch_picking/employee/barcode/", type="json", auth="public")
    def get_employee_barcode_batch_picking(self,access_pin, res_id, res_model, **kwargs):
        'Return employee ids for batch pickings if pin validate '
        return request.env["hr.employee"].get_employees_barcode_batch_picking_pin_validated(str(access_pin), res_id, res_model)


    @http.route("/barcode/employee/validation/", type="json", auth="public")
    def get_validate_employee_operation(self, access_pin, res_model, **kwargs):
        'Direct EmpID if return to operation main screen'
        return request.env["hr.employee"]._employees_pin_validated(str(access_pin), res_model)

    @http.route("/validate/employee/barcode", type="json", auth="public")
    def get_validate_employee(self, access_pin, res_id, res_model, **kwargs):
        'Return employee ids for pickings if pin validate '
        return request.env["hr.employee"].get_employees_pin_validated(str(access_pin), res_id, res_model)

    @http.route("/get/user/details", type="json", auth="public")
    def get_current_user(self, user_id,  **kwargs):
        'Return current user allow multi employee field data for barcode access'
        return request.env["res.users"].search([('id', '=', user_id['userId'])], limit=1).allow_multi_employee

