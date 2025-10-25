# -*- coding: utf-8 -*-
import requests
from pytz import country_timezones
from datetime import date, timedelta
from collections import defaultdict
from odoo import http
from odoo.exceptions import AccessError, MissingError
import calendar
import imghdr
from odoo.fields import Command
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.addons.web.controllers.home import CREDENTIAL_PARAMS
from urllib.parse import parse_qs
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Datetime
from datetime import datetime, timedelta, date
import copy
import itertools
SIGN_UP_PARAMS = ['name', 'login', 'password', 'confirm_password']
from odoo.http import content_disposition, request
import random
import string
import io
from PIL import Image
import base64
from datetime import datetime
import logging
from itertools import groupby
_logger = logging.getLogger("============API Authenticate========")
from odoo.tools import float_round
default_token_size = 16
import time
from collections import OrderedDict
import re


class VanOperation(http.Controller):

    # --- Helper (internal, no HTTP) ---------------------------------------------
    def _create_payment_collection_internal(self, values, user):
        """
        Internal version of /api/v1/create_payment_collection.
        Expects same keys:
          user_id, worker_id, auth_token, amount, journal_id, payment_method_id,
          bank_id, customer_id, cheque_date, cheque_number, note, cheque_pic,
          is_pdc_payable, invoice_id (optional)
        Returns: dict(success=bool, ...).
        """
        try:
            # --- Basic lookups / guards ---
            user_id = int(values.get('user_id') or 0)
            worker_id = int(values.get('worker_id') or 0)
            auth_token = values.get('auth_token')
            amount = float(values.get('amount') or 0.0)
            journal_id = values.get('journal_id')
            payment_method_id = values.get('payment_method_id')  # may be None
            bank_id = int(values.get('bank_id') or 0)
            customer_id = values.get('customer_id')
            cheque_owner = values.get('cheque_owner')
            partner = request.env['res.partner'].sudo().browse(customer_id)
            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid partner ID.'}

            journal = request.env['account.journal'].sudo().browse(journal_id)
            if not journal.exists():
                return {'success': False, 'error_msg': 'Invalid journal ID.'}

            # token check (keep same security model you already use)
            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired token.'}

            # worker (collector)
            worker_partner = request.env['res.partner'].sudo().browse(worker_id) if worker_id else user.partner_id
            # custodian_id = request.env['custodian'].sudo().search(
            #     [("responsible_custodian", "=", worker_partner.id)], limit=1)
            request.env.cr.execute("""
                SELECT id
                FROM custodian
                WHERE responsible_custodian = %s
                LIMIT 1
            """, (worker_partner.id,))
            row = request.env.cr.fetchone()

            custodian_id = request.env['custodian'].browse(row[0]) if row else False

            # build vals
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': amount,
                'cheque_owner': cheque_owner,
                'currency_id': user.company_id.currency_id.id,
                'company_id': user.company_id.id,
                'responsible_id': worker_partner.id,
                'collector_name': worker_partner.name,
                'journal_id': journal.id,
            }
            if custodian_id:
                payment_vals['custodian_id'] = custodian_id.id
            if payment_method_id:
                payment_method_line_obj = request.env['account.payment.method.line'].sudo().browse(payment_method_id)
                if payment_method_line_obj:
                    is_pdc_payable = payment_method_line_obj.is_pdc_payable

                    if is_pdc_payable:
                        payment_vals['is_pdc_payable'] = True
                    else:
                        is_cdc_payable = payment_method_line_obj.is_cdc_payable
                        if is_cdc_payable:
                            payment_vals['is_cdc_payable'] = True
                payment_vals['payment_method_line_id'] = int(payment_method_id)

            # optional fields
            cheque_number = values.get('cheque_number') or False
            note = values.get('note') or ''
            cheque_pic = values.get('cheque_pic') or False
            is_pdc_payable = bool(values.get('is_pdc_payable'))
            cheque_date = values.get('cheque_date') or False
            if cheque_date:
                cheque_date = fields.Date.to_date(cheque_date)
                payment_vals['due_date'] = cheque_date
                payment_vals['date'] = date.today()
            else:
                payment_vals['due_date'] = fields.Date.today()
                payment_vals['date'] = date.today()
            # if is_pdc_payable:
            #     payment_vals['is_pdc_payable'] = True
            if bank_id:
                payment_vals['pdc_bank_id'] = bank_id
            if cheque_number:
                payment_vals['pdc_ref'] = cheque_number
            if note:
                payment_vals['pdc_payable_note'] = note
                payment_vals['memo'] = note
            if cheque_pic:
                try:
                    cheque_binary = base64.b64decode(cheque_pic + '===')
                    payment_vals['cheque_scanning'] = base64.b64encode(cheque_binary).decode()
                except Exception as e:
                    return {'success': False, 'error_msg': f'Invalid cheque_pic base64: {str(e)}'}

            # link invoice if provided
            invoice_id = values.get('invoice_id')
            if invoice_id:
                payment_vals['invoice_ids'] = [(4, int(invoice_id))]

            _logger.info(">>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<")
            _logger.info(payment_vals)
            _logger.info(">>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<")

            payment = request.env['account.payment'].with_user(user.id).sudo().create(payment_vals)
            invoices = request.env['account.move'].sudo().browse(invoice_id).exists() if invoice_id else request.env[
                'account.move']

            # CDC vs PDC swap if needed (kept from your route)
            if payment.payment_mode == 'cdc':
                if cheque_number:
                    payment.cdc_ref = cheque_number
                    payment.pdc_ref = False
                if bank_id:
                    payment.cdc_bank_id = bank_id
                    payment.pdc_bank_id = False

            payment.with_user(user.id).sudo().action_post()
            access_token = payment._ensure_portal_token()
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            receipt_voucher_4inch_pdf_url = f"{base_url}/my/receipt_voucher_4inch_pdf/{payment.id}?access_token={access_token}&report_type=pdf&download=true"

            # 🔧 EXPLICIT RECONCILIATION (works whether full or partial payment)
            try:
                if invoices:
                    # Make sure invoices are posted
                    for inv in invoices.filtered(lambda m: m.state != 'posted'):
                        inv.action_post()

                    # Helper that is robust across Odoo versions (internal_type vs account_type)
                    def _is_recv_pay(line):
                        acc = line.account_id
                        # v14-v15: internal_type; v16-v17: account_type
                        t_new = getattr(acc, 'account_type', False)
                        t_old = getattr(acc, 'internal_type', False)
                        return t_new in ('asset_receivable', 'liability_payable') or t_old in ('receivable', 'payable')

                    for inv in invoices:
                        inv_recv_lines = inv.line_ids.filtered(_is_recv_pay)
                        if not inv_recv_lines:
                            continue

                        # Take payment lines that hit the same account(s) as the invoice receivable/payable
                        pay_lines = payment.move_id.line_ids.filtered(
                            lambda l: l.account_id.id in inv_recv_lines.mapped('account_id').ids and not l.reconciled
                        )

                        lines_to_rec = (pay_lines + inv_recv_lines).filtered(lambda l: not l.reconciled)
                        if lines_to_rec:
                            lines_to_rec.reconcile()
            except Exception as rec_e:
                _logger.warning("Payment<->Invoice reconciliation skipped: %s", rec_e)

            return {
                'success': True,
                'payment_id': payment.id,
                'payment_name': payment.name,
                'amount': payment.amount,
                'receipt_voucher_4inch_pdf_url': receipt_voucher_4inch_pdf_url,
                'message': 'Collection created.',
            }
        except Exception as e:
            _logger.exception("Error in _create_payment_collection_internal: %s", str(e))
            return {'success': False, 'error_msg': 'System error during payment creation.'}

    @http.route('/api/v1/create_sale_order_with_delivery_v2', type='json', auth='user', methods=['POST'], csrf=False)
    def create_sale_order_with_delivery_v2(self, **kwargs):
        """
        Same as create_sale_order_with_delivery, but:
          - No automatic cash payment.
          - If 'payment' payload is provided, create payments dynamically using
            the same fields as /api/v1/create_payment_collection.
        Expected extra JSON:
          "payment": {
            "enabled": true,                 # toggle
            "apply": "per_invoice",          # "per_invoice" (default) or "single"
            "amount": 0,                     # optional, falls back to invoice residual
            "journal_id": 1,                 # required
            "payment_method_id": 42,         # optional
            "bank_id": 7,                    # optional
            "cheque_number": "CH-123",       # optional
            "cheque_date": "2025-09-14",     # optional (YYYY-MM-DD)
            "cheque_pic": "<base64>",        # optional
            "is_pdc_payable": false,         # optional
            "note": "Thanks",                # optional
            "allow_credit_payment": false,   # optional
            "worker_id": 0,                  # optional override
            "cheque_owner": "Owner"          # optional free text
          }
        """
        response = {}
        values = request.httprequest.json
        sale_order_start_datetime = datetime.now()

        try:
            user_id = int(values.get('user_id', 0))
            auth_token = values.get('auth_token')
            sale_order_id = values.get('sale_order_id')
            is_active = values.get('is_active', False)
            po_number = values.get('po_number', False)

            user = request.env['res.users'].browse(user_id)
            if not user.exists() or not auth_token:
                return {'success': False, 'error_msg': 'Invalid user ID or missing auth token.'}

            # token = request.env['mobile.auth.token'].sudo().search_count([
            #     ('user_id', '=', user_id),
            #     ('mobile_app_auth_token', '=', auth_token)
            # ])        
            request.env.cr.execute("""
                SELECT 1 
                FROM mobile_auth_token
                WHERE user_id = %s AND mobile_app_auth_token = %s
                LIMIT 1
            """, (user_id, auth_token))
            token_exists = bool(request.env.cr.fetchone())
            
            if token_exists == 0:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            worker_jr_cash = False
            worker_jr_credit = False

            # ------------------- ACTIVATE EXISTING SO -------------------
            if sale_order_id and is_active:
                so_vals = {}
                sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
                if not sale_order.exists():
                    return {'success': False, 'error_msg': f"Sale Order ID {sale_order_id} not found."}
                
                so_partner = sale_order.partner_id
                
                request.env.cr.execute("""
                    SELECT wj.journal_id
                    FROM worker_journal wj
                    INNER JOIN res_partner_worker_journal_rel rel ON wj.id = rel.worker_journal_id
                    WHERE rel.res_partner_id = %s
                        AND wj.active = true
                        AND wj.journal_type = 'cash_van'
                    LIMIT 1; 
                """, (user.partner_id.id,))                                        
                result = request.env.cr.fetchone()
                worker_jr_cash = result[0] if result else False
                
                request.env.cr.execute("""
                    SELECT wj.journal_id
                    FROM worker_journal wj
                    INNER JOIN res_partner_worker_journal_rel rel ON wj.id = rel.worker_journal_id
                    WHERE rel.res_partner_id = %s
                        AND wj.active = true
                        AND wj.journal_type = 'presale'
                    LIMIT 1; 
                """, (user.partner_id.id,))                                        
                result = request.env.cr.fetchone()
                worker_jr_credit = result[0] if result else False
                
                if po_number:
                    so_vals['po_number'] = po_number

                # Try to align warehouse with van location (does NOT change existing pickings' source locations)
                try:
                    van_location = user.partner_id.van_location
                    if van_location and van_location.warehouse_id:
                        so_vals['warehouse_id'] = van_location.warehouse_id.id
                except Exception as e:
                    _logger.info("error into the warehouse: %s", str(e))

                try:
                    sale_order.order_line._compute_analytic_distribution()

                    if user.partner_id:
                        so_vals['assign_to'] = user.partner_id.id
                        # crm_team = request.env['crm.team'].sudo().search(
                        #     [('partner_member_ids', 'in', [user.partner_id.id])], limit=1)
                        request.env.cr.execute("""
                            SELECT ctrp.crm_team_id
                            FROM crm_team_res_partner_rel ctrp
                            WHERE ctrp.res_partner_id = %s
                            LIMIT 1
                        """, (user.partner_id.id,))
                        result = request.env.cr.fetchone()
                        if result:
                            crm_team = request.env['crm.team'].browse(result[0])
                            so_vals['team_id'] = crm_team.id

                    # journals from worker.journal
                    # worker_jr_cash_obj = request.env['worker.journal'].sudo().search_read([
                    #     ('worker_ids', 'in', [user.partner_id.id]),
                    #     ('active', '=', True),
                    #     ('journal_type', '=', 'cash_van')
                    # ], ['journal_id'], limit=1)            

                    # worker_jr_credit_obj = request.env['worker.journal'].sudo().search_read([
                    #     ('worker_ids', 'in', [user.partner_id.id]),
                    #     ('active', '=', True),
                    #     ('journal_type', '=', 'presale')
                    # ], ['journal_id'], limit=1)

                    if so_partner.customer_type == "cash" or (
                            so_partner.customer_type == "credit" and so_partner.is_credit_hold):
                        worker_jr_obj = worker_jr_cash
                    else:
                        worker_jr_obj = worker_jr_credit
                        # worker_jr_obj = worker_jr_credit_obj[0]['journal_id'][0] if worker_jr_credit_obj else False

                    if worker_jr_obj:
                        so_vals['sale_journal'] = worker_jr_obj

                except Exception as e:
                    _logger.info("Trying To Fix: %s", e)

                so_vals['active'] = True
                sale_order.write(so_vals)

                if sale_order.is_discount_panding:
                    sale_order.approve_discount()
                if sale_order.state != 'sale':
                    start_time = time.time()
                    sale_order.with_user(user).sudo().action_confirm()
                    _logger.info("SO %s confirm: %.2fs", sale_order.name, time.time() - start_time)

                # Pickings flow
                delivery_result = []
                pending_pickings = sale_order.picking_ids.sorted(key=lambda p: p.picking_type_id.sequence)
                for picking in pending_pickings:
                    if picking.state != 'done':
                        picking.write({
                            'draft_trigger': True,
                            'custom_state_trigger': False,
                            'scheduled_date': picking.scheduled_date or fields.Datetime.now(),
                            'date_deadline': picking.date_deadline or fields.Datetime.now() + timedelta(days=3),
                        })

                processed_pickings = set()
                
                while pending_pickings:
                    picking = pending_pickings[0]
                    if picking.id in processed_pickings:
                        break
                    processed_pickings.add(picking.id)

                    if picking.state in ['draft', 'loaded_dispatched']:
                        picking.with_user(user).sudo().action_confirm()

                    if not picking.picker_partner_id:
                        picking.picker_partner_id = so_partner

                    if picking.state != 'done':
                        # First reserve
                        _logger.info("action_assign start: %s", datetime.now())
                        picking.with_user(user).sudo().action_assign()
                        _logger.info("action_assign end: %s", datetime.now())

                        for move in picking.move_ids_without_package:
                            move.picker_partner_id = picking.picker_partner_id

                        # Try put in pack (optional)
                        if not picking.has_packages:
                            try:
                                _logger.info("action_put_in_pack start: %s", datetime.now())
                                picking.with_user(user).sudo().action_put_in_pack()
                                _logger.info("action_put_in_pack end: %s", datetime.now())
                                picking.has_packages = True
                            except Exception as e:
                                _logger.info("can't put in pack: %s", str(e))
                                if 'There is nothing eligible to put in a pack' in str(e):
                                    for one_move in picking.move_ids_without_package:
                                        if one_move.quantity <= 0:
                                            one_move.quantity = one_move.product_uom_qty
                                    try:
                                        picking.with_user(user).sudo().action_put_in_pack()
                                        picking.has_packages = True
                                    except Exception as e2:
                                        _logger.info("inner exception: %s", str(e2))

                        # Validate with recovery
                        try:
                            request.env.cr.execute("""
                                SELECT COUNT(*) 
                                FROM custodian 
                                WHERE responsible_custodian = %s
                            """, (user.partner_id.id,))

                            custodian_count = request.env.cr.fetchone()[0]
                            if custodian_count == 0:
                                return {
                                    'success': False,
                                    'message': "You do not have a custodian call The IT department",
                                    'sale_order': {'id': sale_order.id, 'name': sale_order.name},
                                }
                            _logger.info("button_validate start: %s", datetime.now())
                            is_partial = any(
                                line.quantity < line.product_uom_qty for line in picking.move_ids)
                            if not is_partial:
                                picking.with_user(user).with_context(
                                    mail_create_nosubscribe=False).sudo().button_validate()
                            else:
                                picking.action_cancel()
                            # picking.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()
                            _logger.info("button_validate end: %s", datetime.now())
                        except UserError as e:
                            error_message = str(e)
                            _logger.info("Validation error -> try lot/serial auto assign: %s", error_message)

                            # *** NEGATIVE STOCK FIX ***
                            # Allocate quants under the picking source, consume from each quant.location_id.
                            source_loc = picking.location_id
                            
                            # Pre-fetch all quants outside the loop using SQL for better performance
                            # Group by product and pre-allocate in a single query
                            product_ids = picking.move_ids_without_package.product_id.ids
                            if product_ids:                            
                                # Fetch all quants for all products in one query, sorted by quantity ASC
                                request.env.cr.execute("""
                                    SELECT 
                                        sq.id,
                                        sq.product_id
                                    FROM stock_quant sq
                                    INNER JOIN product_product pp ON sq.product_id = pp.id
                                    INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
                                    WHERE sq.location_id IN (
                                        SELECT id 
                                        FROM stock_location 
                                        WHERE parent_path LIKE (
                                            SELECT parent_path || '%%' 
                                            FROM stock_location 
                                            WHERE id = %s
                                        )
                                    )
                                    AND sq.product_id = ANY(%s)
                                    AND sq.quantity > 0
                                    AND (
                                        -- Include tracked products only if they have lot_id
                                        (pt.tracking IN ('lot', 'serial') AND sq.lot_id IS NOT NULL)
                                        OR pt.tracking NOT IN ('lot', 'serial')
                                    )
                                    ORDER BY sq.product_id, sq.quantity ASC
                                """, (source_loc.id, product_ids))
                                
                                # Group quants by product_id
                                quant_rows = request.env.cr.fetchall()
                                quants_ids_by_product = {}
                                for quant_id, product_id in quant_rows:
                                    if product_id not in quants_ids_by_product:
                                        quants_ids_by_product[product_id] = []
                                    quants_ids_by_product[product_id].append(quant_id)
                                
                                # Convert grouped IDs to recordsets
                                quants_by_product = {}
                                for product_id, quant_ids in quants_ids_by_product.items():
                                    quants_by_product[product_id] = request.env['stock.quant'].browse(quant_ids)
                            
                            move_lines_to_create = []
                            for move in picking.move_ids_without_package:
                                # For tracked products, we must provide lot/serial
                                if move.move_line_ids:
                                    move.move_line_ids.sudo().unlink()

                                needed_qty = move.product_uom_qty
                                allocated = 0.0

                                # domain = [
                                #     ('location_id', 'child_of', source_loc.id),
                                #     ('product_id', '=', move.product_id.id),
                                #     ('quantity', '>', 0),
                                # ]
                                # if move.product_id.tracking in ('lot', 'serial'):
                                #     domain.append(('lot_id', '!=', False))

                                # quants = request.env['stock.quant'].sudo().search(domain, order='quantity asc')
                                quants = quants_by_product.get(move.product_id.id, request.env['stock.quant'])
                                
                                for quant in quants:
                                    if allocated >= needed_qty:
                                        break
                                    take = min(quant.quantity, needed_qty - allocated)
                                    if take <= 0:
                                        continue

                                    move_lines_to_create.append({
                                        'move_id': move.id,
                                        'location_id': quant.location_id.id,  # consume where stock exists
                                        'location_dest_id': move.location_dest_id.id,
                                        'product_id': move.product_id.id,
                                        'product_uom_id': move.product_uom.id,
                                        'lot_id': quant.lot_id.id if move.product_id.tracking != 'none' else False,
                                        'qty_done': take,
                                    })
                                    allocated += take

                                if allocated < needed_qty:
                                    _logger.warning(
                                        "Picking %s / move %s could only allocate %.2f of %.2f from %s",
                                        picking.name, move.id, allocated, needed_qty, source_loc.display_name
                                    )
                                    
                            # Create all move lines in a single batch (much faster)
                            if move_lines_to_create:
                                request.env['stock.move.line'].sudo().create(move_lines_to_create)
                                
                            # Try validate again
                            is_partial = any(
                                line.quantity < line.product_uom_qty for line in picking.move_ids)
                            if not is_partial:
                                picking.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()
                            else:
                                picking.action_cancel()
                            # picking.with_user(user).with_context(mail_create_nosubscribe=False).sudo().button_validate()

                    delivery_result.append({
                        'picking_id': picking.id,
                        'name': picking.name,
                        'state': picking.state,
                        'type': picking.picking_type_id.name,
                    })
                    pending_pickings = sale_order.picking_ids.with_user(user).sudo().filtered(
                        lambda p: p.state not in ['done', 'cancel', 'loaded_dispatched']
                    ).sorted(key=lambda p: p.picking_type_id.sequence)

                # --- invoices and optional dynamic payments ---
                invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                payment_result = []
                pay_cfg = values.get('payment') or {}
                do_pay = bool(pay_cfg.get('enabled'))
                allow_credit_payment = bool(pay_cfg.get('allow_credit_payment'))
                is_credit_customer = (so_partner.customer_type == 'credit'
                                      and not so_partner.is_credit_hold)

                if do_pay:
                    if is_credit_customer and not allow_credit_payment:
                        _logger.info("Skip payment: credit customer and allow_credit_payment=False")
                    else:
                        apply_mode = pay_cfg.get('apply') or 'per_invoice'
                        if apply_mode == 'single':
                            total_residual = sum(invoices.mapped('amount_residual'))
                            amount = float(pay_cfg.get('amount') or total_residual or 0.0)
                            payload = dict(pay_cfg)
                            payload.update({
                                'user_id': user_id,
                                'worker_id': int(pay_cfg.get('worker_id') or 0),
                                'auth_token': auth_token,
                                'amount': amount,
                                'customer_id': so_partner.id,
                                # no invoice_id → open payment
                            })
                            # pass through cheque_owner if provided
                            if 'cheque_owner' in pay_cfg:
                                payload['cheque_owner'] = pay_cfg.get('cheque_owner')
                            res = self._create_payment_collection_internal(payload, user)
                            if not res.get('success'):
                                return {'success': False, 'error_msg': res.get('error_msg') or 'Payment failed.'}
                            payment_result.append({
                                'payment_id': res['payment_id'],
                                'name': res['payment_name'],
                                'amount': res['amount'],
                                'receipt_pdf_download': res['receipt_voucher_4inch_pdf_url'],
                            })
                        else:
                            for inv in invoices:
                                inv_amount = float(pay_cfg.get('amount') or inv.amount_residual or 0.0)
                                payload = dict(pay_cfg)
                                payload.update({
                                    'user_id': user_id,
                                    'worker_id': int(pay_cfg.get('worker_id') or 0),
                                    'auth_token': auth_token,
                                    'amount': inv_amount,
                                    'customer_id': so_partner.id,
                                    'invoice_id': inv.id,
                                })
                                if 'cheque_owner' in pay_cfg:
                                    payload['cheque_owner'] = pay_cfg.get('cheque_owner')
                                res = self._create_payment_collection_internal(payload, user)
                                if not res.get('success'):
                                    return {'success': False, 'error_msg': res.get('error_msg') or 'Payment failed.'}
                                payment_result.append({
                                    'payment_id': res['payment_id'],
                                    'name': res['payment_name'],
                                    'amount': res['amount'],
                                    'receipt_pdf_download': res['receipt_voucher_4inch_pdf_url'],
                                })

                # PDF URL
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                tax_invoice_4inch_pdf_url = None
                if sale_order_id:
                    access_token = sale_order._ensure_portal_token()
                    tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{sale_order.id}?access_token={access_token}&report_type=pdf&download=true"

                # timing
                delta = datetime.now() - sale_order_start_datetime
                hours, remainder = divmod(delta.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                sale_order.api_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

                return {
                    'success': True,
                    'message': 'Sale Order activated and delivery created (V2).',
                    'sale_order': {'id': sale_order.id, 'name': sale_order.name},
                    'delivery': delivery_result,
                    'payment': payment_result,
                    'customer_payment_type': ('cash' if payment_result else 'credit'),
                    'tax_invoice_4inch_pdf': tax_invoice_4inch_pdf_url,
                }

            # ------------------- CREATE NEW SO + DELIVERIES -------------------
            partner_id = values.get('partner_id')
            customer_id = values.get('customer_id')
            order_creation_source = values.get('order_creation_source')
            product_lines = values.get('products', [])

            partner = request.env['res.partner'].sudo().browse(partner_id)
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if not partner.exists():
                return {'success': False, 'error_msg': 'Invalid partner ID.'}
            if not customer.exists():
                return {'success': False, 'error_msg': 'Invalid customer ID.'}

            order_lines = []
            for line in product_lines:
                product_id = line.get('product_id')
                quantity = line.get('quantity')
                price_unit = line.get('price_unit')
                uom_id = line.get('uom_id')
                discount = line.get('discount', 0)
                packaging_id = line.get('product_packaging_id')

                if not all([product_id, quantity, price_unit, uom_id]):
                    return {'success': False, 'error_msg': 'Missing required product fields.'}

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists() or not product.active:
                    template = request.env['product.template'].sudo().browse(product_id)
                    product = template.product_variant_ids[:1] if template.exists() else False
                    if not product or not product.active:
                        return {'success': False, 'error_msg': f"Invalid product ID: {product_id}"}

                if packaging_id:
                    packaging = request.env['product.packaging'].sudo().browse(int(packaging_id))
                    if packaging.exists():
                        quantity *= packaging.qty
                        uom_id = packaging.product_uom_id.id

                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'product_uom': uom_id,
                    'name': product.name,
                }))

            if not order_lines:
                return {'success': False, 'error_msg': 'No valid order lines.'}

            sale_order = request.env['sale.order'].with_user(user).sudo().create({
                'partner_id': customer.id,
                'order_creation_source': order_creation_source,
                'date_order': fields.Datetime.now(),
                'commitment_date': fields.Datetime.now(),
                'order_line': order_lines,
                'company_id': user.company_id.id,
            })
            so_partner = sale_order.partner_id

            worker_journal = worker_jr_cash if (customer.customer_type == "cash" or
                                               (
                                                           customer.customer_type == "credit" and customer.is_credit_hold)) else worker_jr_credit

            if worker_journal:
                sale_order.sale_journal = worker_journal

            sale_order.with_user(user).sudo().action_confirm()

            delivery_result = []
            pending_pickings = sale_order.picking_ids.sorted(key=lambda p: p.picking_type_id.sequence)

            for picking in sale_order.picking_ids:
                picking.draft_trigger = True
                picking.custom_state_trigger = False
                picking.scheduled_date = picking.scheduled_date or fields.Datetime.now()
                picking.date_deadline = picking.date_deadline or fields.Datetime.now() + timedelta(days=3)

            processed_pickings = set()
            while pending_pickings:
                picking = pending_pickings[0]
                if picking.id in processed_pickings:
                    break
                processed_pickings.add(picking.id)

                if picking.state in ['draft', 'loaded_dispatched']:
                    picking.sudo().with_user(user).action_confirm()

                if not picking.picker_partner_id:
                    picking.picker_partner_id = so_partner
                if not picking.picking_driver_id:
                    picking.picking_driver_id = so_partner

                # reserve first
                picking.sudo().with_user(user).action_assign()

                for move in picking.move_ids_without_package:
                    move.picker_partner_id = picking.picker_partner_id

                # try reserve again to ensure lines are consistent
                picking.sudo().with_user(user).action_assign()

                # try put in pack
                if not picking.has_packages:
                    try:
                        picking.sudo().with_user(user).action_put_in_pack()
                        picking.has_packages = True
                    except Exception as e:
                        _logger.info("can't put in pack: %s", str(e))
                        if 'There is nothing eligible to put in a pack' in str(e):
                            for one_move in picking.move_ids_without_package:
                                if one_move.quantity <= 0:
                                    one_move.quantity = one_move.product_uom_qty
                            try:
                                picking.sudo().with_user(user).action_put_in_pack()
                                picking.has_packages = True
                            except Exception as e2:
                                _logger.info("inner exception: %s", str(e2))

                # validate with recovery
                try:
                    picking.with_context(mail_create_nosubscribe=False).sudo().with_user(user).button_validate()
                except UserError as e:
                    _logger.info("Validation error on create branch -> auto-assign lots if needed: %s", str(e))

                    source_loc = picking.location_id

                    # Pre-fetch all quants outside the loop using SQL for better performance
                    # Group by product and pre-allocate in a single query
                    product_ids = picking.move_ids_without_package.product_id.ids
                    if product_ids:
                        # Fetch all quants for all products in one query, sorted by quantity ASC
                        request.env.cr.execute("""
                            SELECT 
                                sq.id,
                                sq.product_id
                            FROM stock_quant sq
                            INNER JOIN product_product pp ON sq.product_id = pp.id
                            INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
                            WHERE sq.location_id IN (
                                SELECT id 
                                FROM stock_location 
                                WHERE parent_path LIKE (
                                    SELECT parent_path || '%%' 
                                    FROM stock_location 
                                    WHERE id = %s
                                )
                            )
                            AND sq.product_id = ANY(%s)
                            AND sq.quantity > 0
                            AND (
                                -- Include tracked products only if they have lot_id
                                (pt.tracking IN ('lot', 'serial') AND sq.lot_id IS NOT NULL)
                                OR pt.tracking NOT IN ('lot', 'serial')
                            )
                            ORDER BY sq.product_id, sq.quantity ASC
                        """, (source_loc.id, product_ids))

                        # Group quants by product_id
                        quant_rows = request.env.cr.fetchall()
                        quants_ids_by_product = {}
                        for quant_id, product_id in quant_rows:
                            if product_id not in quants_ids_by_product:
                                quants_ids_by_product[product_id] = []
                            quants_ids_by_product[product_id].append(quant_id)

                        # Convert grouped IDs to recordsets
                        quants_by_product = {}
                        for product_id, quant_ids in quants_ids_by_product.items():
                            quants_by_product[product_id] = request.env['stock.quant'].browse(quant_ids)

                    move_lines_to_create = []
                    for move in picking.move_ids_without_package:
                        if move.move_line_ids:
                            move.move_line_ids.sudo().unlink()

                        needed_qty = move.product_uom_qty
                        allocated = 0.0

                        # domain = [
                        #     ('location_id', 'child_of', source_loc.id),
                        #     ('product_id', '=', move.product_id.id),
                        #     ('quantity', '>', 0),
                        # ]
                        # if move.product_id.tracking in ('lot', 'serial'):
                        #     domain.append(('lot_id', '!=', False))
                        #
                        # quants = request.env['stock.quant'].sudo().search(domain, order='quantity asc')
                        quants = quants_by_product.get(move.product_id.id, request.env['stock.quant'])

                        for quant in quants:
                            if allocated >= needed_qty:
                                break
                            take = min(quant.quantity, needed_qty - allocated)
                            if take <= 0:
                                continue

                            move_lines_to_create.append({
                                'move_id': move.id,
                                'location_id': quant.location_id.id,  # consume where stock exists
                                'location_dest_id': move.location_dest_id.id,
                                'product_id': move.product_id.id,
                                'product_uom_id': move.product_uom.id,
                                'lot_id': quant.lot_id.id if move.product_id.tracking != 'none' else False,
                                'qty_done': take,
                            })
                            allocated += take

                        if allocated < needed_qty:
                            _logger.warning(
                                "Picking %s / move %s only allocated %.2f of %.2f from %s",
                                picking.name, move.id, allocated, needed_qty, source_loc.display_name
                            )

                    # Create all move lines in a single batch
                    if move_lines_to_create:
                        request.env['stock.move.line'].sudo().create(move_lines_to_create)

                    picking.with_context(mail_create_nosubscribe=False).sudo().with_user(user).button_validate()

                delivery_result.append({
                    'picking_id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'type': picking.picking_type_id.name,
                })

                pending_pickings = sale_order.picking_ids.sudo().with_user(user).filtered(
                    lambda p: p.state not in ['done', 'cancel', 'loaded_dispatched']
                ).sorted(key=lambda p: p.picking_type_id.sequence)

            # Invoices and dynamic payment (same block as above)
            invoices = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            payment_result = []
            pay_cfg = values.get('payment') or {}
            do_pay = bool(pay_cfg.get('enabled'))
            allow_credit_payment = bool(pay_cfg.get('allow_credit_payment'))
            is_credit_customer = (so_partner.customer_type == 'credit'
                                  and not so_partner.is_credit_hold)

            if do_pay:
                if is_credit_customer and not allow_credit_payment:
                    _logger.info("Skip payment: credit customer and allow_credit_payment=False")
                else:
                    apply_mode = pay_cfg.get('apply') or 'per_invoice'
                    if apply_mode == 'single':
                        total_residual = sum(invoices.mapped('amount_residual'))
                        amount = float(pay_cfg.get('amount') or total_residual or 0.0)
                        payload = dict(pay_cfg)
                        payload.update({
                            'user_id': user_id,
                            'worker_id': int(pay_cfg.get('worker_id') or 0),
                            'auth_token': auth_token,
                            'amount': amount,
                            'customer_id': so_partner.id,
                        })
                        if 'cheque_owner' in pay_cfg:
                            payload['cheque_owner'] = pay_cfg.get('cheque_owner')
                        res = self._create_payment_collection_internal(payload, user)
                        if not res.get('success'):
                            return {'success': False, 'error_msg': res.get('error_msg') or 'Payment failed.'}
                        payment_result.append({
                            'payment_id': res['payment_id'],
                            'name': res['payment_name'],
                            'amount': res['amount'],
                            'receipt_pdf_download': res['receipt_voucher_4inch_pdf_url'],
                        })
                    else:
                        for inv in invoices:
                            inv_amount = float(pay_cfg.get('amount') or inv.amount_residual or 0.0)
                            payload = dict(pay_cfg)
                            payload.update({
                                'user_id': user_id,
                                'worker_id': int(pay_cfg.get('worker_id') or 0),
                                'auth_token': auth_token,
                                'amount': inv_amount,
                                'customer_id': so_partner.id,
                                'invoice_id': inv.id,
                            })
                            if 'cheque_owner' in pay_cfg:
                                payload['cheque_owner'] = pay_cfg.get('cheque_owner')
                            res = self._create_payment_collection_internal(payload, user)
                            if not res.get('success'):
                                return {'success': False, 'error_msg': res.get('error_msg') or 'Payment failed.'}
                            payment_result.append({
                                'payment_id': res['payment_id'],
                                'name': res['payment_name'],
                                'amount': res['amount'],
                                'receipt_pdf_download': res['receipt_voucher_4inch_pdf_url'],
                            })

            # PDF URL
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            tax_invoice_4inch_pdf_url = None
            if sale_order:
                access_token = sale_order._ensure_portal_token()
                tax_invoice_4inch_pdf_url = f"{base_url}/my/tax_invoice_4inch_pdf/{sale_order.id}?access_token={access_token}&report_type=pdf&download=true"

            # timing
            sale_order_end_datetime = datetime.now()
            delta = sale_order_end_datetime - sale_order_start_datetime
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            sale_order.api_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

            return {
                'success': True,
                'message': 'Sale Order and Delivery created successfully (V2).',
                'sale_order': {'id': sale_order.id, 'name': sale_order.name},
                'delivery': delivery_result,
                'payment': payment_result,
                'tax_invoice_4inch_pdf': tax_invoice_4inch_pdf_url,
                'customer_payment_type': ('cash' if payment_result else 'credit'),
            }

        except Exception as e:
            _logger.exception("Error in /create_sale_order_with_delivery_v2")
            response = {'success': False, 'error_msg': str(e)}

        return response

    def _cancel_so_with_wizard_fallback(self, env, so, user_id, default_reason="Cancelled via API"):
        """
        Try SO.action_cancel(); if it returns an action for a wizard (e.g. sale.order.cancel),
        programmatically create that wizard and call its action button (action_cancel / confirm).
        """
        try:
            # If the SO has a dedicated "open wizard" method, try that first.
            if hasattr(so, 'action_open_cancel_wizard'):
                res = so.with_user(user_id).sudo().action_open_cancel_wizard()
            elif hasattr(so, 'action_cancel'):
                res = so.with_user(user_id).sudo().action_cancel()
            else:
                # Last resort: force state write
                so.with_user(user_id).sudo().write({'state': 'cancel'})
                return True, None

            # If a wizard action was returned, execute it
            if isinstance(res, dict) and res.get('res_model'):
                wiz_model_name = res['res_model']
                wiz_ctx = res.get('context') or {}
                # Instantiate the wizard in the action’s context so active_id(s) are respected
                WizardModel = env[wiz_model_name].with_context(wiz_ctx).sudo()

                # Provide a reason if the field exists
                create_vals = {}
                try:
                    # Introspect available fields to be robust across customizations
                    fields_in_model = WizardModel._fields
                    if 'order_id' in fields_in_model:
                        create_vals['order_id'] = so.id
                    if 'reason' in fields_in_model:
                        create_vals['reason'] = default_reason
                    elif 'cancel_reason' in fields_in_model:
                        create_vals['cancel_reason'] = default_reason
                except Exception as e:
                    # If we can’t introspect, just create with no extra vals
                    _logger.info('--------------------------------------------')
                    _logger.info(str(e))
                    _logger.info('--------------------------------------------')

                wiz = WizardModel.create(create_vals)

                # Call the wizard’s action button (naming varies across modules)
                if hasattr(wiz, 'action_cancel'):
                    wiz.action_cancel()
                elif hasattr(wiz, 'confirm'):
                    wiz.confirm()
                elif hasattr(wiz, 'action_confirm'):
                    wiz.action_confirm()
                else:
                    # If no known button exists, fail gracefully; the caller will handle messaging.
                    return False, f"Unknown cancel wizard action on {wiz_model_name}"

            return True, None
        except Exception as e:
            return False, str(e)

    @http.route('/api/v1/cancel_sale_order', type='json', auth='public', methods=['POST'], csrf=False)
    def cancel_sale_order(self, **kw):
        """
        Payload:
        {
          "user_id": 123,
          "auth_token": "abc123",
          "sale_order_id": 456
        }

        Notes:
        - No use of account.move.reversal.
        - We unreserve stock on related pickings before canceling them.
        - We reset posted invoices to draft and cancel (requires company to allow cancel of posted entries).
        """
        values = request.httprequest.json or {}
        user_id = int(values.get('user_id') or 0)
        auth_token = values.get('auth_token')
        sale_order_id = int(values.get('sale_order_id') or 0)

        if not user_id or not auth_token or not sale_order_id:
            return {'success': False, 'error_msg': 'Missing user_id, auth_token, or sale_order_id.'}

        # ---- Token check ----
        token_ok = request.env['mobile.auth.token'].sudo().search_count([
            ('user_id', '=', user_id),
            ('mobile_app_auth_token', '=', auth_token)
        ])
        if not token_ok:
            return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

        # sudo(user_id): perform with superuser power but attribute to the real user in chatter
        env_u = request.env

        so = env_u['sale.order'].with_context(
            mail_create_nosubscribe=True,
            mail_auto_subscribe_no_notify=True
        ).with_user(user_id).sudo().browse(sale_order_id)
        if not so.exists():
            return {'success': False, 'error_msg': f'Sale Order {sale_order_id} not found.'}

        out = {
            'sale_order': {'id': so.id, 'name': so.name, 'prev_state': so.state},
            'pickings': {'unreserved': [], 'canceled': [], 'skipped_done': [], 'already_canceled': []},
            'invoices': {'draft_canceled': [], 'posted_reset_and_canceled': [], 'already_canceled': [], 'failed': []},
            'payments': {'canceled': [], 'skipped': [], 'failed': []},
        }

        # try:
        # ================================
        # 1) Payments & Invoices (NO reversal)
        # ================================
        moves = so.invoice_ids  # account.move
        if moves:
            inv_ids = moves.ids
            pay_model = env_u['account.payment']

            # Link payments either via reconciled_invoice_ids (v15+) or invoice_ids (older mappings)
            payments = pay_model.with_user(user_id).sudo().search([
                '|',
                ('reconciled_invoice_ids', 'in', inv_ids),
                ('invoice_ids', 'in', inv_ids)
            ])

            # a) Cancel posted payments first (so we can freely reset invoices)
            for pay in payments:
                try:
                    if getattr(pay, 'state', '') == 'posted':
                        if hasattr(pay, 'action_cancel'):
                            pay.sudo().action_cancel()
                            out['payments']['canceled'].append({'id': pay.id, 'name': pay.name})
                        else:
                            # Fallback: cancel underlying move
                            if pay.move_id and pay.move_id.state == 'posted':
                                if hasattr(pay.move_id, 'button_draft'):
                                    pay.move_id.sudo().button_draft()
                                if hasattr(pay.move_id, 'button_cancel'):
                                    pay.move_id.sudo().button_cancel()
                            out['payments']['canceled'].append({'id': pay.id, 'name': pay.name, 'fallback_move': True})
                    else:
                        out['payments']['skipped'].append({'id': pay.id, 'name': pay.name, 'state': pay.state})
                except Exception as e:
                    _logger.exception("Payment cancel failed: %s", pay.name)
                    out['payments']['failed'].append({'id': pay.id, 'name': pay.name, 'error': str(e)})

            # b) Unreconcile receivable/payable lines before resetting posted invoices
            # for inv in moves:
            #     try:
            #         rec_lines = inv.line_ids.filtered(
            #             lambda l: l.account_internal_type in ('receivable', 'payable') and l.reconciled
            #         )
            #         if rec_lines:
            #             rec_lines.sudo().remove_move_reconcile()
            #     except Exception as e:
            #         _logger.warning("Unreconcile failed on %s: %s", inv.name, e)

            # c) Reset posted invoices to draft, then cancel. Draft invoices: just cancel.
            for inv in moves:
                try:
                    if inv.state == 'posted':
                        # Requires "Allow canceling entries" in Accounting settings or sufficient rights.
                        if hasattr(inv, 'button_draft'):
                            inv.sudo().button_draft()
                        if hasattr(inv, 'button_cancel'):
                            inv.sudo().button_cancel()
                        else:
                            inv.sudo().write({'state': 'cancel'})
                        out['invoices']['posted_reset_and_canceled'].append({'id': inv.id, 'name': inv.name})
                    elif inv.state == 'draft':
                        if hasattr(inv, 'button_cancel'):
                            inv.sudo().button_cancel()
                        else:
                            inv.sudo().write({'state': 'cancel'})
                        out['invoices']['draft_canceled'].append({'id': inv.id, 'name': inv.name})
                    elif inv.state == 'cancel':
                        out['invoices']['already_canceled'].append({'id': inv.id, 'name': inv.name})
                    else:
                        # other states (e.g., 'waiting', rare depending on version)
                        if hasattr(inv, 'button_cancel'):
                            inv.sudo().button_cancel()
                            out['invoices']['draft_canceled'].append({'id': inv.id, 'name': inv.name, 'note': 'non-standard'})
                        else:
                            inv.sudo().write({'state': 'cancel'})
                            out['invoices']['draft_canceled'].append({'id': inv.id, 'name': inv.name, 'note': 'write cancel'})
                except Exception as e:
                    _logger.exception("Invoice cancel failed: %s", inv.name)
                    out['invoices']['failed'].append({'id': inv.id, 'name': inv.name, 'error': str(e)})

        # ================================
        # 2) Pickings: UNRESERVE then cancel (if not done)
        # ================================
        for picking in so.picking_ids:
            try:
                if picking.state == 'cancel':
                    out['pickings']['already_canceled'].append({'id': picking.id, 'name': picking.name})
                    continue
                if picking.state == 'done':
                    out['pickings']['skipped_done'].append({'id': picking.id, 'name': picking.name})
                    continue

                # Explicitly unreserve any reserved quants/move lines
                if hasattr(picking, 'action_unreserve'):
                    picking.sudo().action_unreserve()
                    out['pickings']['unreserved'].append({'id': picking.id, 'name': picking.name})
                else:
                    # Fallback: at least clear reserved on moves (older versions)
                    for mv in picking.move_ids_without_package:
                        if hasattr(mv, '_do_unreserve'):
                            mv.sudo()._do_unreserve()
                    out['pickings']['unreserved'].append({'id': picking.id, 'name': picking.name, 'fallback': True})

                # Now cancel the picking
                if hasattr(picking, 'action_cancel'):
                    picking.sudo().action_cancel()
                else:
                    picking.sudo().write({'state': 'cancel'})
                out['pickings']['canceled'].append({'id': picking.id, 'name': picking.name})
            except Exception as e:
                _logger.exception("Picking unreserve/cancel failed: %s", picking.name)
                # We continue; SO cancel may still proceed.

        # ================================
        # 3) Sale Order: cancel (final)
        # ================================
        try:
            ok, err = self._cancel_so_with_wizard_fallback(request.env, so, user_id)
            if not ok:
                out['sale_order']['error'] = err or 'Wizard cancel failed'
            out['sale_order']['new_state'] = so.state
        except Exception as e:
            _logger.exception("Sale order cancel failed: %s", so.name)
            out['sale_order']['error'] = str(e)

        return {
            'success': True,
            'message': f"Cancellation flow executed for SO {so.name}.",
            'details': out,
        }

    # except Exception as e:
    #     _logger.exception("Unexpected error in cancel_sale_order")
        return {'success': False, 'error_msg': str(e), 'details': out}
