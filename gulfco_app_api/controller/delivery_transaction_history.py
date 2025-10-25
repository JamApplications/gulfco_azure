# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time

from odoo import http, fields, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class DeliveryHistoryController(http.Controller):

    @http.route('/api/v1/delivery_history_report', type='json', auth='none', methods=['POST'], csrf=False)
    def delivery_history_report(self, **kwargs):
        """
        Request JSON:
        {
            "user_id": 123,
            "token": "....",
            "driver_id": 456,            # res.partner id of the driver (picking_driver_id)
            "start_date": "01-09-2025",  # DD-MM-YYYY
            "end_date":   "03-09-2025"   # DD-MM-YYYY
        }
        """
        vals = request.httprequest.json or {}
        user_id    = vals.get('user_id')
        auth_token = vals.get('token')
        driver_id  = vals.get('worker_id')  # res.partner ID (picking_driver_id)
        start_str  = vals.get('start_date')
        end_str    = vals.get('end_date')

        # -------- Basic validation --------
        if not user_id or not auth_token:
            return {'success': False, 'error_msg': 'Missing required fields: user_id and token.'}
        if not driver_id:
            return {'success': False, 'error_msg': 'Missing required field: worker_id.'}

        # -------- Authenticate token --------
        token = request.env['mobile.auth.token'].sudo().search([
            ('user_id', '=', int(user_id)),
            ('mobile_app_auth_token', '=', auth_token)
        ], limit=1)
        if not token:
            return {'success': False, 'error_msg': 'Invalid or expired token.'}

        # -------- Date parsing --------
        fmt = "%d-%m-%Y"
        try:
            start_date = datetime.strptime(start_str, fmt).date() if start_str else None
            end_date   = datetime.strptime(end_str, fmt).date() if end_str else None
        except Exception:
            return {'success': False, 'error_msg': 'Dates must be in DD-MM-YYYY format.'}

        # Datetime boundaries (inclusive day range)
        start_dt = end_dt = None
        if start_date:
            start_dt = datetime.combine(start_date, time.min)
        if end_date:
            end_dt = datetime.combine(end_date, time.max)

        # -------- Helpers --------
        def sg(rec, field, default=''):
            """safe-get attr or m2o name-id pair."""
            try:
                val = getattr(rec, field, default)
                return val if val not in (False, None) else default
            except Exception:
                return default

        def many2one_info(rec):
            return rec and {'id': rec.id, 'name': rec.display_name} or {}

        def get_trx_type(pick):
            # Priority: custom business fields if present, else Odoo code
            return (
                sg(pick, 'direction') or
                sg(pick, 'delivery_type') or
                sg(pick, 'picking_type_code') or
                sg(pick, 'return_collection')
            )
        # Which date field to filter on
        Picking = request.env['stock.picking'].sudo()
        date_field = 'delivery_planned_date' if 'delivery_planned_date' in Picking._fields else 'scheduled_date'

        # -------- Build picking domain --------
        domain = [('picking_driver_id', '=', int(driver_id))]
        if start_dt:
            domain.append((date_field, '>=', fields.Datetime.to_string(start_dt)))
        if end_dt:
            domain.append((date_field, '<=', fields.Datetime.to_string(end_dt)))

        try:
            # -------- Fetch pickings --------
            pickings = Picking.search(domain, order='id desc')

            deliveries = []
            return_collections = []

            SaleOrder = request.env['sale.order'].sudo()
            AccountMove = request.env['account.move'].sudo()

            for p in pickings:
                trx_type = get_trx_type(p)

                # Link SO via procurement group (your code)
                sale_order = SaleOrder.search([
                    ('procurement_group_id', '=', p.group_id.id),
                    ('state', '!=', 'cancel'),
                ], limit=1)

                # Invoice from SO if exists
                invoice_info = {}
                if sale_order and sale_order.invoice_ids:
                    inv = sale_order.invoice_ids[0]
                    invoice_info = {
                        'id': inv.id,
                        'name': inv.name,
                        'date': sg(inv, 'invoice_date') or sg(inv, 'date'),
                        'state': inv.state,
                        'amount_total': inv.amount_total,
                        'amount_untaxed': inv.amount_untaxed,
                        'amount_tax': inv.amount_tax,
                        'partner': many2one_info(inv.partner_id),
                        'lines': [
                            {
                                'id': l.id,
                                'product_id': l.product_id.id,
                                'product_name': sg(l.product_id, 'display_name'),
                                'default_code': sg(l.product_id, 'default_code'),
                                'quantity': l.quantity,
                                'price_unit': l.price_unit,
                                'price_subtotal': l.price_subtotal,
                            } for l in inv.invoice_line_ids
                        ],
                    }

                # Sale order compact info (with some key fields)
                sale_order_info = {}
                if sale_order:
                    sale_order_info = {
                        'id': sale_order.id,
                        'name': sale_order.name,
                        'date_order': sg(sale_order, 'date_order'),
                        'commitment_date': sg(sale_order, 'commitment_date'),
                        'client_order_ref': sg(sale_order, 'client_order_ref'),
                        'po_number': sg(sale_order, 'po_number'),
                        'po_date': sg(sale_order, 'po_date'),
                        'po_expiry_date': sg(sale_order, 'po_expiry_date'),  # if you have it
                        'partner': many2one_info(sale_order.partner_id),
                        'invoice_status': sg(sale_order, 'invoice_status'),
                        'amount_total': sale_order.amount_total,
                        'amount_tax': sale_order.amount_tax,
                        'amount_untaxed': sale_order.amount_untaxed,
                        'invoice': invoice_info
                    }

                # Move lines detail
                move_rows = []
                for mv in p.move_ids_without_package:
                    prod = mv.product_id
                    move_rows.append({
                        'id': mv.id,
                        'product_id': prod.id,
                        'product': sg(prod, 'display_name'),
                        'default_code': sg(prod, 'default_code'),
                        'division': sg(prod, 'division'),
                        'product_packaging_id': sg(mv.product_packaging_id, 'id'),
                        'product_packaging_name': sg(mv.product_packaging_id, 'name'),
                        'uom_id': sg(mv.product_uom, 'id') or sg(mv.product_uom, 'id'),
                        'uom_name': sg(mv.product_uom, 'name'),
                        'ordered_qty': mv.product_uom_qty,
                        'reserved_qty': mv.reserved_quantity,
                        'quantity': mv.quantity,
                        'state': mv.state,
                    })

                row = {
                    'id': p.id,
                    'name': p.name,
                    'date_deadline': sg(p, 'date_deadline'),
                    'date_done': sg(p, 'date_done'),
                    'date': sg(p, 'date'),
                    'po_expiry_date': sg(p, 'po_expiry_date'),  # if present on picking; else None
                    'scheduled_date': sg(p, 'scheduled_date'),
                    'city': sg(p.partner_id, 'city'),
                    'commitment_date': sale_order and sg(sale_order, 'commitment_date') or '',
                    'delivery_type': sg(p, 'delivery_type'),
                    'direction': sg(p, 'direction'),
                    'division': sg(p, 'division'),
                    'driver_detail': {
                        'id': sg(p, 'picking_driver_id') and p.picking_driver_id.id or None,
                        'name': sg(p, 'picking_driver_id') and p.picking_driver_id.display_name or '',
                        'phone': sg(p.picking_driver_id, 'phone'),
                        'mobile': sg(p.picking_driver_id, 'mobile'),
                    },
                    'grn_state': sg(p, 'state'),  # if you have a custom GRN state, rename here
                    'group_id': sg(p, 'group_id') and p.group_id.id or None,
                    'invoice_no': invoice_info.get('name') or '',
                    'location_id': many2one_info(p.location_id),
                    'location_dest_id': many2one_info(p.location_dest_id),
                    'trx_type': trx_type,
                    'move_ids': move_rows,
                    'sale_order': sale_order_info,
                }

                if p.trx_type == 'return_collection':
                    return_collections.append(row)
                else:
                    deliveries.append(row)

            # --------- RMAs (by worker or salesperson, filtered by date) ---------
            # Input allows driver scope; RMAs typically tied to salesperson/responsible
            rma_domain = ['|',
                          ('responsible_worker_id', '=', int(driver_id)),
                          ('sales_person_id', '=', int(driver_id))]

            # apply date range on RMA.date
            if start_dt:
                rma_domain.append(('date', '>=', fields.Datetime.to_string(start_dt)))
            if end_dt:
                rma_domain.append(('date', '<=', fields.Datetime.to_string(end_dt)))

            RMA = request.env['rma'].sudo()
            rmas = RMA.search(rma_domain, order='id desc')

            rma_rows = []
            for r in rmas:
                inv = r.refund_id
                invoice_info = {}
                if inv:
                    invoice_info = {
                        'id': inv.id,
                        'name': inv.name,
                        'date': sg(inv, 'invoice_date') or sg(inv, 'date'),
                        'state': inv.state,
                        'amount_total': inv.amount_total,
                        'amount_untaxed': inv.amount_untaxed,
                        'amount_tax': inv.amount_tax,
                        'partner': many2one_info(inv.partner_id),
                    }

                rma_rows.append({
                    'id': r.id,
                    'name': r.name,
                    'collection_request_date': sg(r, 'collection_request_date'),
                    'date': sg(r, 'date'),
                    'deadline': sg(r, 'deadline'),
                    'division': sg(r, 'division'),
                    'emirate': sg(r, 'emirate'),
                    'state': sg(r, 'state'),
                    'grv_amount': r.grv_amount,
                    'grv_no': sg(r, 'grv_no'),
                    'origin': sg(r, 'origin'),
                    'operation_type': sg(r, 'operation_type'),
                    'operation_id': many2one_info(r.operation_id),
                    'partner': many2one_info(r.partner_id),
                    'responsible_worker': many2one_info(r.responsible_worker_id),
                    'sales_person': many2one_info(r.sales_person_id),
                    'location_id': many2one_info(r.location_id),
                    'picking_id': many2one_info(r.picking_id),
                    'refund': invoice_info,
                    'line_ids': [
                        {
                            'id': ln.id,
                            'product_id': ln.product_id.id,
                            'product_name': sg(ln.product_id, 'display_name'),
                            'default_code': sg(ln.product_id, 'default_code'),
                            'quantity': ln.product_uom_qty,
                            'uom': sg(ln.product_uom_id, 'name'),
                            'price_unit': sg(ln, 'price_unit'),
                            'total': sg(ln, 'total'),
                        } for ln in r.line_ids
                    ],
                })

            return {
                'success': True,
                'filters': {
                    'driver_id': int(driver_id),
                    'date_field': date_field,  # delivery_planned_date or scheduled_date
                    'start_date': start_str,
                    'end_date': end_str,
                },
                'deliveries': deliveries,
                'return_collections': return_collections,
                'rmas': rma_rows,
            }

        except Exception as e:
            _logger.exception("Error in delivery_history_report")
            return {'success': False, 'error_msg': str(e)}