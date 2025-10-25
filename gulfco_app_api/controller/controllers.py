from odoo import http, fields, models, api, _, SUPERUSER_ID
from odoo.http import request
from odoo.fields import Datetime, time
from datetime import datetime, timedelta, date
import logging
import base64
import pytz
from odoo.exceptions import ValidationError
_logger = logging.getLogger("GulfcoAppApi")
from collections import defaultdict

class GulfcoAppApiController(http.Controller):

    def _get_image_url_dynamic(self, model, record_id, field_name):
        base = request.httprequest.host_url.rstrip('/')
        return f"{base}/web/image/{model}/{record_id}/{field_name}"


    def convert_datetime_to_date(self, datetime_value):
        """
        Converts a datetime.date, datetime.datetime, or ISO8601 string to a date.

        :param datetime_value: date, datetime, str, or None
        :return: datetime.date or None
        """
        if not datetime_value:
            return None

        # If it's already a date (but not a full datetime), return it
        if isinstance(datetime_value, date) and not isinstance(datetime_value, datetime):
            return datetime_value

        # If it's a string, parse ISO
        if isinstance(datetime_value, str):
            try:
                dt = datetime.fromisoformat(datetime_value)
                return dt.date()
            except ValueError:
                raise ValueError("Invalid ISO8601 date/datetime string")

        # If it's a datetime, strip time
        if isinstance(datetime_value, datetime):
            return datetime_value.date()

        raise TypeError("Must be date, datetime, or ISO string")

    @http.route('/api/v1/delivery/journey', auth='public', type='json', csrf=False, methods=['POST'])
    def get_delivery_journey(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id = int(payload.get('user_id', 0))
            worker_id = int(payload.get('worker_id', 0))
            auth_token = payload.get('auth_token')

            if not user_id or not auth_token:
                return {"success": False, "error_msg": "Missing user ID or auth token."}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "error_msg": "User not found."}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {"success": False, "error_msg": "Invalid or expired token."}

            # ---- new: treat delivery_planned_date as a Date field ----
            today = date.today()
            tomorrow = today + timedelta(days=1)

            partner_id = user.partner_id
            if worker_id != 0:
                partner_id = request.env['res.partner'].sudo().browse(worker_id)
            pickings = request.env['stock.picking'].sudo().search([
                ('picking_driver_id', '=', partner_id.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'in', ['loaded_dispatched']),
                ('delivery_planned_date', '>=', today),
                ('delivery_planned_date', '<',  tomorrow),
            ], order='priority_no asc')

            collection_pickings = request.env['stock.picking'].sudo().search([
                ('picking_driver_id', '=', partner_id.id),
                ('trx_type', '=', 'return_collection'),
                ('state', 'in', ['driver_assigned']),
                ('delivery_planned_date', '>=', today),
                ('delivery_planned_date', '<',  tomorrow),
            ], order='priority_no asc')

            data = []
            return_collections = []
            for picking in pickings:
                # fetch related sale order if any
                sale_order = None
                invoice = None
                ref = ""
                trx_ref = ""
                trx_date = ""
                if picking.group_id:
                    sale_order = request.env['sale.order'].sudo().search([
                        ('procurement_group_id', '=', picking.group_id.id),
                        ('state', '!=', 'cancel'),
                    ], limit=1)

                    if sale_order:
                        ref = sale_order.name
                        if sale_order.invoice_ids and len(sale_order.invoice_ids) > 0:
                            invoice = sale_order.invoice_ids[0]
                            trx_ref = invoice.name
                            trx_date = invoice.date



                qty_in_pallet = sum(picking.move_ids.mapped('qty_in_pallet_case'))
                partner = picking.partner_id

                # convert sale_order.expected_date to pure date string
                expected_date = ""
                if sale_order and sale_order.expected_date:
                    ed = self.convert_datetime_to_date(sale_order.expected_date)
                    expected_date = ed.isoformat() if ed else ""

                # convert delivery_planned_date to pure date string
                scheduled_date = ""
                if picking.delivery_planned_date:
                    sd = self.convert_datetime_to_date(picking.delivery_planned_date)
                    scheduled_date = sd.isoformat() if sd else ""

                def safe_get(val, fallback=""):
                    return val if val not in (False, None, "null", "None") else fallback

                data.append({
                    "picking_id":           safe_get(picking.id, 0),
                    "customer_id":          safe_get(partner.id, 0),
                    "customer_name":        safe_get(partner.name),
                    "customer_code":        safe_get(partner.customer_code),
                    "trn_no":               safe_get(partner.vat_trn),
                    "reference":            safe_get(ref),
                    "external_reference":   safe_get(partner.external_ref),
                    "outlet_code":          safe_get(partner.outlet_code),
                    "outlet_short_name":    safe_get(partner.outlet_short_name),
                    "trx_ref":              safe_get(trx_ref),
                    "latitude":             safe_get(partner.latitude),
                    "longitude":            safe_get(partner.longitude),
                    "partner_latitude":     safe_get(partner.partner_latitude),
                    "partner_longitude":    safe_get(partner.partner_longitude),
                    "street":               safe_get(partner.street),
                    "street2":              safe_get(partner.street2),
                    "contact_address":      safe_get(partner.contact_address),
                    "contact_address_complete": safe_get(partner.contact_address_complete),
                    "contact_address_inline":   safe_get(partner.contact_address_inline),
                    "detailed_address":     safe_get(partner.detailed_address),
                    "peppol_eas":           safe_get(partner.peppol_eas),
                    "trx_date":             trx_date,
                    "scheduled_date":       scheduled_date,
                    "trx_type":             safe_get(picking.trx_type),
                    "trx_sequence":         safe_get(picking.name),
                    "department_id":        safe_get(partner.department.id),
                    "department_name":      safe_get(partner.department.name),
                    "po_number":            sale_order and safe_get(sale_order.po_number) or "",
                    "validity_date":        sale_order and safe_get(sale_order.validity_date) or "",
                    "po_expiry_date":       sale_order and safe_get(sale_order.po_expiry_date) or "",
                    "expected_date":        expected_date,
                    "po_date":              sale_order and safe_get(sale_order.po_date) or "",
                    "qty_in_pallet":        int(qty_in_pallet) if qty_in_pallet else 0,
                    "invoice_id":           invoice.id if invoice else 0,
                })
            for picking in collection_pickings:
                # fetch related sale order if any
                sale_order = None
                if picking.group_id:
                    sale_order = request.env['sale.order'].sudo().search([
                        ('procurement_group_id', '=', picking.group_id.id),
                        ('state', '!=', 'cancel'),
                    ], limit=1)

                qty_in_pallet = sum(picking.move_ids.mapped('qty_in_pallet_case'))
                partner = picking.partner_id

                # convert sale_order.expected_date to pure date string
                expected_date = ""
                if sale_order and sale_order.expected_date:
                    ed = self.convert_datetime_to_date(sale_order.expected_date)
                    expected_date = ed.isoformat() if ed else ""

                # convert delivery_planned_date to pure date string
                scheduled_date = ""
                if picking.delivery_planned_date:
                    sd = self.convert_datetime_to_date(picking.delivery_planned_date)
                    scheduled_date = sd.isoformat() if sd else ""

                def safe_get(val, fallback=""):
                    return val if val not in (False, None, "null", "None") else fallback

                return_collections.append({
                    "picking_id":           safe_get(picking.id, 0),
                    "customer_id":          safe_get(partner.id, 0),
                    "customer_name":        safe_get(partner.name),
                    "customer_code":        safe_get(partner.customer_code),
                    "trn_no":               safe_get(partner.vat_trn),
                    "reference":            safe_get(partner.ref),
                    "external_reference":   safe_get(partner.external_ref),
                    "outlet_code":          safe_get(partner.outlet_code),
                    "outlet_short_name":    safe_get(partner.outlet_short_name),
                    "trx_ref":              safe_get(partner.id, 0),
                    "latitude":             safe_get(partner.latitude),
                    "longitude":            safe_get(partner.longitude),
                    "partner_latitude":     safe_get(partner.partner_latitude),
                    "partner_longitude":    safe_get(partner.partner_longitude),
                    "street":               safe_get(partner.street),
                    "street2":              safe_get(partner.street2),
                    "contact_address":      safe_get(partner.contact_address),
                    "contact_address_complete": safe_get(partner.contact_address_complete),
                    "contact_address_inline":   safe_get(partner.contact_address_inline),
                    "detailed_address":     safe_get(partner.detailed_address),
                    "peppol_eas":           safe_get(partner.peppol_eas),
                    "trx_date":             scheduled_date,
                    "trx_type":             safe_get(picking.trx_type),
                    "trx_sequence":         safe_get(picking.name),
                    "department_id":        safe_get(partner.department.id),
                    "department_name":      safe_get(partner.department.name),
                    "po_number":            sale_order and safe_get(sale_order.po_number) or "",
                    "validity_date":        sale_order and safe_get(sale_order.validity_date) or "",
                    "po_expiry_date":       sale_order and safe_get(sale_order.po_expiry_date) or "",
                    "expected_date":        expected_date,
                    "po_date":              sale_order and safe_get(sale_order.po_date) or "",
                    "qty_in_pallet":        int(qty_in_pallet) if qty_in_pallet else 0,
                })

            return {"success": True, "data": data, "return_collection": return_collections}

        except Exception as e:
            _logger.exception("Error in /api/v1/delivery/journey: %s", str(e))
            return {
                "success": False,
                "error_msg": "Internal server error.",
                "error_code": -5,
            }


    @http.route('/api/v1/fsm/visit/end', auth='none', type='json', csrf=False, methods=['POST'])
    def end_fsm_visit(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id        = int(payload.get('user_id', 0))
            auth_token     = payload.get('auth_token')
            fsm_order_id   = int(payload.get('visit_id', 0))
            date_end_str   = payload.get('end_date')    # optional, YYYY-MM-DD
            end_time_str   = payload.get('end_time')    # optional, hh:mm:ss
            duration       = payload.get('duration')    # optional
            # (you can add other optional fields here)

            # --- Basic validation ---
            if not user_id or not auth_token:
                return {"success": False, "error_msg": "Missing user ID or auth token."}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "error_msg": "User not found."}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {"success": False, "error_msg": "Invalid or expired token."}

            if not fsm_order_id:
                return {"success": False, "error_msg": "Missing required field: visit_id"}

            fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)
            if not fsm_order.exists():
                return {"success": False, "error_msg": f"FSM Order ID {fsm_order_id} not found."}

            # --- Build update vals ---
            vals = {}

            # Compose end datetime if either date or time is provided
            if date_end_str or end_time_str:
                # parse date part
                if date_end_str:
                    try:
                        date_part = datetime.strptime(date_end_str, "%Y-%m-%d").date()
                    except ValueError:
                        return {
                            "success": False,
                            "error_msg": "Invalid format for end_date. Expected YYYY-MM-DD"
                        }
                else:
                    date_part = fields.Date.context_today(request.env['res.users'])

                # parse time part
                if end_time_str:
                    try:
                        time_part = datetime.strptime(end_time_str, "%H:%M:%S").time()
                    except ValueError:
                        return {
                            "success": False,
                            "error_msg": "Invalid format for end_time. Expected hh:mm:ss"
                        }
                else:
                    time_part = time.min

                # combine and convert from user tz to UTC
                local_dt = datetime.combine(date_part, time_part)
                user_tz = user.tz or request.env['ir.config_parameter'].sudo().get_param(
                    'web.base.default_timezone') or 'UTC'
                try:
                    local_zone = pytz.timezone(user_tz)
                except Exception:
                    local_zone = pytz.UTC
                local_dt = local_zone.localize(local_dt)
                utc_dt   = local_dt.astimezone(pytz.UTC)
                vals['date_end'] = utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            # preserve/override duration if passed
            if duration is not None:
                vals['duration'] = duration

            # (attach or update any other optional fields here)
            # e.g. if payload.get('notes'): vals['notes'] = payload['notes']

            # --- Perform the update ---
            fsm_order.sudo().write(vals)

            return {
                "success": True,
                "message": "FSM visit ended successfully.",
                "fsm_order_id": fsm_order.id,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/fsm/visit/end: %s", str(e))
            return {
                "success": False,
                "error_msg": "Internal server error.",
                "error_code": -5,
                "exception": str(e),
            }

    @http.route('/api/v1/fsm/visit/start', auth='none', type='json', csrf=False, methods=['POST'])
    def start_fsm_visit(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id        = int(payload.get('user_id', 0))
            auth_token     = payload.get('auth_token')
            fsm_order_id   = int(payload.get('visit_id', 0))
            date_start_str   = payload.get('start_date')    # optional, YYYY-MM-DD
            start_time_str   = payload.get('start_time')    # optional, hh:mm:ss
            duration       = payload.get('duration')    # optional
            # (you can add other optional fields here)

            # --- Basic validation ---
            if not user_id or not auth_token:
                return {"success": False, "error_msg": "Missing user ID or auth token."}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "error_msg": "User not found."}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {"success": False, "error_msg": "Invalid or expired token."}

            if not fsm_order_id:
                return {"success": False, "error_msg": "Missing required field: visit_id"}

            fsm_order = request.env['fsm.order'].sudo().browse(fsm_order_id)
            if not fsm_order.exists():
                return {"success": False, "error_msg": f"FSM Order ID {fsm_order_id} not found."}

            # --- Build update vals ---
            vals = {}

            # Compose end datetime if either date or time is provided
            if date_start_str or start_time_str:
                # parse date part
                if date_start_str:
                    try:
                        date_part = datetime.strptime(date_start_str, "%Y-%m-%d").date()
                    except ValueError:
                        return {
                            "success": False,
                            "error_msg": "Invalid format for end_date. Expected YYYY-MM-DD"
                        }
                else:
                    date_part = fields.Date.context_today(request.env['res.users'])

                # parse time part
                if start_time_str:
                    try:
                        time_part = datetime.strptime(start_time_str, "%H:%M:%S").time()
                    except ValueError:
                        return {
                            "success": False,
                            "error_msg": "Invalid format for end_time. Expected hh:mm:ss"
                        }
                else:
                    time_part = time.min

                # combine and convert from user tz to UTC
                local_dt = datetime.combine(date_part, time_part)
                user_tz = user.tz or request.env['ir.config_parameter'].sudo().get_param(
                    'web.base.default_timezone') or 'UTC'
                try:
                    local_zone = pytz.timezone(user_tz)
                except Exception:
                    local_zone = pytz.UTC
                local_dt = local_zone.localize(local_dt)
                utc_dt   = local_dt.astimezone(pytz.UTC)
                vals['date_start'] = utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            # preserve/override duration if passed
            if duration is not None:
                vals['duration'] = duration

            # (attach or update any other optional fields here)
            # e.g. if payload.get('notes'): vals['notes'] = payload['notes']

            # --- Perform the update ---
            fsm_order.sudo().write(vals)

            return {
                "success": True,
                "message": "FSM visit started successfully.",
                "fsm_order_id": fsm_order.id,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/fsm/visit/start: %s", str(e))
            return {
                "success": False,
                "error_msg": "Internal server error.",
                "error_code": -5,
                "exception": str(e),
            }

    @http.route('/api/v1/fsm/create', auth='none', type='json', csrf=False, methods=['POST'])
    def create_fsm_order(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id = int(payload.get('user_id', 0))
            auth_token = payload.get('auth_token')
            customer_id = int(payload.get('customer_id', 0))
            person_id_partner = int(payload.get('person_id_partner', 0))
            worker_id = int(payload.get('worker_id', 0))
            date_start_str = payload.get('start_date')  # optional, format YYYY-MM-DD
            date_end = payload.get('date_end')  # optional
            duration = payload.get('duration')  # optional
            picking_id = payload.get('picking_id')  # may be None
            fsm_location = payload.get('fsm_location')  # may be None
            dayroute_id = int(payload.get('dayroute_id', 0))
            start_time_str = payload.get('start_time')  # optional, format hh:mm:ss

            # Basic validation
            if not user_id or not auth_token:
                return {"success": False, "error_msg": "Missing user ID or auth token."}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "error_msg": "User not found."}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {"success": False, "error_msg": "Invalid or expired token."}

            if not customer_id:
                return {"success": False, "error_msg": "Missing required fields: customer_id"}

            vals = {'customer_id': customer_id}

            # Handle date_start composition and timezone conversion
            if date_start_str or start_time_str:
                # Default date: today if not provided
                if date_start_str:
                    try:
                        date_part = datetime.strptime(date_start_str, "%Y-%m-%d").date()
                    except ValueError:
                        return {"success": False, "error_msg": "Invalid format for start_date. Expected YYYY-MM-DD"}
                else:
                    date_part = fields.Date.context_today(request.env['res.users'])

                # Default time: midnight if not provided
                if start_time_str:
                    try:
                        time_part = datetime.strptime(start_time_str, "%H:%M:%S").time()
                    except ValueError:
                        return {"success": False, "error_msg": "Invalid format for start_time. Expected hh:mm:ss"}
                else:
                    time_part = time.min

                # Combine and convert from user tz to UTC
                local_dt = datetime.combine(date_part, time_part)
                user_tz = user.tz or request.env['ir.config_parameter'].sudo().get_param(
                    'web.base.default_timezone') or 'UTC'
                try:
                    local_zone = pytz.timezone(user_tz)
                except Exception:
                    local_zone = pytz.UTC
                local_dt = local_zone.localize(local_dt)
                utc_dt = local_dt.astimezone(pytz.UTC)
                vals['date_start'] = utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            # Preserve legacy date_end and duration
            if date_end:
                vals['date_end'] = date_end
            if duration:
                vals['duration'] = duration

            # Attach picking if provided
            if picking_id:
                try:
                    pid = int(picking_id)
                    vals['picking_ids'] = [(4, pid)]
                except (ValueError, TypeError):
                    _logger.warning("Invalid picking_id passed to FSM create: %r", picking_id)


            if fsm_location:
                vals['location_id'] = fsm_location

            elif not fsm_location and user.user_type == 'delivery_user':
                loc = request.env['fsm.location'].sudo().search([('shipping_address_id', '=', customer_id)], limit=1)
                if loc:
                    vals['location_id'] = loc.id
                else:
                    loc = request.env['fsm.location'].sudo().search([('partner_id', '=', customer_id)],
                                                                    limit=1)
                    if loc:
                        vals['location_id'] = loc.id

            else:
                # Set location based on customer
                loc = request.env['fsm.location'].sudo().search([('partner_id', '=', customer_id)], limit=1)
                if loc:
                    vals['location_id'] = loc.id
                else:
                    my_customer = request.env['res.partner'].sudo().browse(customer_id)

                    if my_customer and my_customer.service_location_id:
                        vals['location_id'] = my_customer.service_location_id.id
                    else:
                        loc = request.env['fsm.location'].sudo().search([('ref', '=', "DEFAULT")], limit=1)
                        if loc:
                            vals['location_id'] = loc.id

            # Determine team and person
            partner_rec = False
            if person_id_partner != 0:
                vals['person_id_partner'] = person_id_partner
                partner_rec = request.env['res.partner'].sudo().browse(int(person_id_partner))
            elif worker_id != 0:
                vals['person_id_partner'] = worker_id
                partner_rec = request.env['res.partner'].sudo().browse(int(worker_id))
            else:
                partner_rec = request.env['res.partner'].sudo().search([('internal_user', '=', user_id)], limit=1)
            partner_id = partner_rec.id if partner_rec else user.partner_id.id
            _logger.info("CREATE FSM")
            _logger.info(partner_id)
            _logger.info(partner_rec)
            _logger.info(worker_id)

            if partner_id:
                _logger.info(partner_id)
                crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [partner_id]),('active','=',True)],
                                                                 limit=1)
                _logger.info(crm_team)

                if crm_team:
                    fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
                    _logger.info(fsm_team)

                    vals['sales_team_id'] = crm_team.id

                    if fsm_team:
                        vals['team_id'] = fsm_team.id
                        vals['person_id_partner'] = partner_id
            _logger.info("out side fsm team")

            company_id = False
            if request.env.company:
                company_id = request.env.company
            if not company_id:
                company_id = request.env['res.company'].sudo().search([], limit=1)
            if company_id:
                vals['company_id'] = company_id.id
            # wrap in a savepoint so only this create is rolled back
            warehouse = request.env['stock.warehouse'].sudo().search([('active','=', True)], limit=1)
            if warehouse:
                vals['warehouse_id'] = warehouse.id
            try:
                fsm_order = request.env['fsm.order'].sudo().create(vals)
            except:
                _logger.info("error in creation fsm")
                fsm_team = request.env['fsm.team'].sudo().search([('sequence','=',0)])
                if fsm_team:
                    vals['team_id'] = fsm_team.id
                fsm_order = request.env['fsm.order'].sudo().create(vals)


            # if we got here, creation succeeded
            return {
                "success": True,
                "message": "FSM Order created successfully.",
                "fsm_order_id": fsm_order.id,
            }
        except Exception as e:
            _logger.exception("Error in /api/v1/fsm/create: %s", str(e))
            return {
                "success": False,
                "error_msg": "Internal server error.",
                "error_code": -5,
                "exception": str(e),
            }



    # ------------------------------------------------------------------
    # 1. RESCHEDULE
    # ------------------------------------------------------------------
    @http.route('/api/v1/delivery/reschedule', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_reschedule_picking(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id        = int(payload.get('user_id', 0))
            auth_token     = payload.get('auth_token')
            # visit_id       = int(payload.get('visit_id', 0))
            picking_id     = int(payload.get('picking_id', 0))
            scheduled_date = payload.get('scheduled_date')
            remark         = payload.get('remark_picking')

            if not (user_id and auth_token):
                return {"success": False, "message": "Missing user ID or auth token.", "data": {}}
            if not (picking_id and scheduled_date and remark):
                return {"success": False, "message": "Missing required data.", "data": {}}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            token_ok = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token_ok:
                return {"success": False, "message": "Invalid or expired token.", "data": {}}

            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {"success": False, "message": "Invalid Picking ID.", "data": {}}

            picking.write({
                'delivery_planned_date': scheduled_date,
                'note'          : remark,
                'remark_picking'        : remark,
                'state'         : 'rescheduled',
            })
            if hasattr(picking, 'cust_rescheduled'):
                picking.cust_rescheduled()

            return {
                "success": True,
                "message": "Picking rescheduled successfully.",
                "data": {"picking_id": picking.id, "scheduled_date": scheduled_date}
            }
        except Exception as e:
            _logger.exception("Error in reschedule API: %s", str(e))
            return {"success": False, "message": "Internal server error.", "error_code": -5, "data": {}}

    # ------------------------------------------------------------------
    # 2. FULL DELIVER
    # ------------------------------------------------------------------
    @http.route('/api/v1/delivery/full/deliver', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_full_deliver_picking(self, **kwargs):
        try:
            payload            = request.httprequest.json or {}
            user_id            = int(payload.get('user_id', 0))
            auth_token         = payload.get('auth_token')
            visit_id           = payload.get('visit_id')
            picking_id         = int(payload.get('picking_id', 0))
            deliver_date       = payload.get('deliver_date')
            remark             = payload.get('remark_picking')
            invoice_attachment = payload.get('invoice_attachement')

            missing = [n for n, v in [
                ('user_id', user_id), ('auth_token', auth_token),
                ('picking_id', picking_id), ('deliver_date', deliver_date),
                ('remark_picking', remark)
            ] if not v]
            if missing:
                return {"success": False, "message": f"Missing required fields: {', '.join(missing)}.", "data": {}}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            if not request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id), ('mobile_app_auth_token', '=', auth_token)
            ], limit=1):
                return {"success": False, "message": "Invalid or expired authentication token.", "data": {}}

            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {"success": False, "message": "Picking not found.", "data": {}}

            picking.write({
                'date_done'            : deliver_date,
                'note'                 : remark,
                'remark_picking'       : remark,
                'state'                : 'done',
                'has_packages'         : True,
            })
            for move in picking.move_line_ids:
                move.write({'qty_done': move.quantity_product_uom})

            if invoice_attachment:
                request.env['ir.attachment'].sudo().create({
                    'name'     : f"Delivery Invoice - {picking.name}",
                    'type'     : 'binary',
                    'datas'    : invoice_attachment,
                    'res_model': 'stock.picking',
                    'res_id'   : picking.id,
                    'mimetype': 'image/jpeg',
                })

            if picking.state != "loaded_dispatched":
                picking.delivery_load_dispatched()
            picking.loaded_dispatched_delivery()

            return {"success": True, "message": "Picking delivered and validated successfully.", "data": {"picking_id": picking.id, "delivered_at": deliver_date}}
        except Exception as e:
            _logger.exception("Error in full deliver API: %s", str(e))
            return {"success": False, "message": "Internal server error.", "message_details": str(e),"error_code": -5, "data": {}}

    # ------------------------------------------------------------------
    # 3. FULL RETURN (CREATE RMA)
    # ------------------------------------------------------------------
    @http.route('/api/v1/delivery/full/return', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_full_return_picking(self, **kwargs):
        try:
            payload            = request.httprequest.json or {}
            user_id            = int(payload.get('user_id', 0))
            worker_id            = int(payload.get('worker_id', 0))
            auth_token         = payload.get('auth_token')
            visit_id           = int(payload.get('visit_id', 0))
            picking_id         = int(payload.get('picking_id', 0))
            invoice_id         = int(payload.get('invoice_id', 0))
            return_date        = payload.get('deliver_date')
            product_line_ids        = payload.get('product_line_ids')
            remark             = payload.get('remark_picking')
            # invoice_attachment = payload.get('invoice_attachement')
            operation_id = payload.get('operation_id')

            missing = [n for n, v in [
                ('user_id', user_id), ('auth_token', auth_token),
                ('picking_id', picking_id),
                ('deliver_date', return_date),
                ('remark_picking', remark),
                ('invoice_id', invoice_id)
            ] if not v]
            if missing:
                return {"success": False, "message": f"Missing required fields: {', '.join(missing)}.", "data": {}}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            if not request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id), ('mobile_app_auth_token', '=', auth_token)
            ], limit=1):
                return {"success": False, "message": "Invalid or expired authentication token.", "data": {}}

            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {"success": False, "message": "Picking not found.", "data": {}}

            worker_partner = user.partner_id
            if worker_id != 0:
                worker_partner = request.env['res.partner'].sudo().browse(worker_id)
            team = False
            if worker_partner:
                team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', [worker_partner.id])],
                                                                 limit=1)
                if team:
                    fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', team.id)], limit=1)

            # -------------------------- RMA HEADER -------------------------
            rma = request.env['rma'].sudo().with_user(SUPERUSER_ID).create({
                'partner_id'           : picking.partner_id.id,
                'user_id'              : user_id,
                'date'                 : return_date or fields.Datetime.now(),
                'responsible_worker_id': worker_partner.id,
                'crm_team_id'          : team if team else False,
                'origin'               : f"Delivery {visit_id}",
                'visit_id'             : visit_id,
                'picking_id'           : picking_id,
                'operation_id'         : operation_id,
                'rma_type'             : 'base_on_invoice',
                'invoice_id'           : invoice_id,
                'company_id'           : user.sudo().with_user(SUPERUSER_ID).company_id.id,
            })

            # -------------------------- RMA LINES --------------------------
            # Initial GRV (likely 0 now; will recompute later)
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # ---------------- Lines: FIX for duplicate products ----------------
            # Keep ALL existing behavior. We only change how we choose which line to update:
            # build a queue per product and consume ONE line per payload row.
            existing_lines_pool = defaultdict(list)
            for l in rma.line_ids.sorted(key=lambda r: r.id):
                existing_lines_pool[l.product_id.id].append(l)

            updated_line_ids = []

            def _safe_int(x):
                try: return int(x or 0)
                except Exception: return 0

            def _safe_float(x):
                try: return float(x or 0)
                except Exception: return 0.0

            def _pop_matching_line(product_id, product_packaging_id, return_reason_id, return_reason_type_id, return_caused_by_id):
                """Pop ONE unused existing line for this product. Prefer an exact match if optional fields provided."""
                bucket = existing_lines_pool.get(product_id) or []

                def _is_exact(line):
                    if product_packaging_id and (line.product_packaging_id.id or 0) != product_packaging_id:
                        return False
                    if return_reason_id and (line.return_reason_id.id or 0) != return_reason_id:
                        return False
                    if return_reason_type_id and (line.return_reason_type_id.id or 0) != return_reason_type_id:
                        return False
                    if return_caused_by_id and (line.return_caused_by_id.id or 0) != return_caused_by_id:
                        return False
                    return True

                # exact match first
                for i, line in enumerate(bucket):
                    if _is_exact(line):
                        bucket.pop(i)
                        if not bucket:
                            existing_lines_pool.pop(product_id, None)
                        return line

                # fallback: any remaining line for this product
                if bucket:
                    line = bucket.pop(0)
                    if not bucket:
                        existing_lines_pool.pop(product_id, None)
                    return line
                return None
            _logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> product lines >>>>>>>>>>>>>")
            _logger.info(product_line_ids)
            for prod in product_line_ids:
                product_id = _safe_int(prod.get('product_id'))
                returned_qty = _safe_float(prod.get('quantity'))
                product_packaging_qty = _safe_float(prod.get('product_packaging_qty'))
                product_packaging_id = _safe_int(prod.get('product_packaging_id'))

                return_caused_by_id = _safe_int(prod.get('return_caused_by_id'))
                return_reason_id = _safe_int(prod.get('return_reason_id'))
                return_reason_type_id = _safe_int(prod.get('return_type_id'))

                # production_date = prod.get('production_date')  # kept for future use
                # expiry_date = prod.get('expiry_date')
                # lot = prod.get('lot') or 0
                # if not lot and production_date and expiry_date:
                #     lot = f"{production_date} - {expiry_date}"

                # consume ONE existing line per payload row (no new creation; preserve prices/taxes)
                existing_line = _pop_matching_line(
                    product_id, product_packaging_id, return_reason_id, return_reason_type_id, return_caused_by_id
                )
                _logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> exisgint lines >>>>>>>>>>>>>")
                _logger.info(existing_line)
                _logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> exisgint lines >>>>>>>>>>>>>")
                if existing_line:
                    existing_line.sudo().with_user(SUPERUSER_ID).write({
                        'product_uom_qty': returned_qty,
                        'return_reason_id': return_reason_id or False,
                        'return_reason_type_id': return_reason_type_id or False,
                        'return_caused_by_id': return_caused_by_id or False,
                        # DO NOT touch price_unit/taxes/exercise fields (preserve original)
                        'exercise_price': existing_line.exercise_price,
                        # 'lot_number': lot if rma_type == 'base_on_product' and lot else False,
                        # 'production_date': production_date,
                        # 'expiry_date': expiry_date,
                    })
                    updated_line_ids.append(existing_line.id)
                else:
                    _logger.warning(f"No unused RMA line left to match product {product_id} on RMA {rma.id}")

            # Build helper sets
            other_lines = rma.line_ids.filtered(lambda l: l.id not in updated_line_ids)
            to_update_lines = rma.line_ids.filtered(lambda l: l.id in updated_line_ids)

            # Mirror selected fields into rma.invoice.line (keep your behavior)
            for one in to_update_lines:
                request.env['rma.invoice.line'].sudo().create({
                    'product_uom_qty': one.product_uom_qty,
                    'product_packaging_qty': one.product_packaging_qty,
                    # 'product_packaging_id': one.product_packaging_id.id,
                    'return_reason_id': one.return_reason_id.id,
                    'return_reason_type_id': one.return_reason_type_id.id,
                    'return_caused_by_id': one.return_caused_by_id.id,
                    'product_id': one.product_id.id,
                    'price_unit': one.price_unit,
                    'product_uom_id': one.product_uom_id.id,
                    'rma_id': one.rma_id.id,
                    'move_id': one.move_id.id if one.move_id else False,
                    'move_line_id': one.move_line_id.id if one.move_line_id else False,
                    'system_unit_price': one.system_unit_price,
                    'tax_id': [(4, one.tax_id.id)] if one.tax_id else False,
                    'discount': one.discount,
                    'exercise_price': one.exercise_price,
                    'analytic_distribution': one.analytic_distribution,
                })

            # Recompute (before unlink)
            rma.sudo().compute_line_ids()

            # Delete lines not provided by API in this call (preserve your cleanup)
            try:
                if other_lines:
                    other_lines.with_user(SUPERUSER_ID).unlink()
            except Exception as e:
                _logger.info("Failed to unlink other_lines: %s", str(e))

            # Recompute and GRV again
            rma.sudo().compute_line_ids()
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))




            # for move in picking.move_lines:
            #     qty           = move.product_uom_qty
            #     price_unit    = move.price_unit or 0.0
            #     total         = qty * price_unit
            #     request.env['rma.line'].sudo().create({
            #         'rma_id'              : rma.sudo().id,
            #         'product_id'          : move.sudo().product_id.id,
            #         'brand_id'            : move.sudo().product_id.categ_id.id if hasattr(move.sudo().product_id, 'brand_id') else False,
            #         'product_uom_qty'     : qty,
            #         'price_unit'          : price_unit,
            #         'total'               : total,
            #         # These will be filled by mobile later
            #         'return_reason_id'       : False,
            #         'return_reason_type_id'  : False,
            #         'return_caused_by'       : False,
            #     })

            # Invoice attachment saved on RMA if provided
            # if invoice_attachment:
            #     request.env['ir.attachment'].sudo().create({
            #         'name'     : f"Return Invoice - {picking.name}",
            #         'type'     : 'binary',
            #         'datas'    : invoice_attachment,
            #         'res_model': 'rma',
            #         'res_id'   : rma.id,
            #     })

            # Add the ram to the visit
            visit = request.env['fsm.order'].sudo().browse(visit_id)
            visit.rma_id = rma.id
            grv_amount = abs(sum(line.total for line in rma.sudo().line_ids))

            rma.grv_amount = grv_amount
            rma.action_submit_rma()
            return {
                "success": True,
                "message": "RMA created successfully.",
                "data": {
                    "picking_id": picking.id,
                    "rma_id"    : rma.id,
                    "return_date": return_date
                }
            }
        except Exception as e:
            _logger.exception("Error in full return API: %s", str(e))
            return {"success": False, "message": "Internal server error.", "error_code": -5, "data": {}}

    # ------------------------------------------------------------------
    # 5. GET RETURN (SPEC DATA)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 5. GET RETURN (SPEC DATA) - MULTI-CONFIG SUPPORT
    # ------------------------------------------------------------------
    @http.route('/api/v1/delivery/get/return/data', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_get_return_data(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id = int(payload.get('user_id', 0))
            worker_id = int(payload.get('worker_id', 0))
            auth_token = payload.get('auth_token')

            # Required fields check
            missing_fields = [n for n, v in [('user_id', user_id), ('auth_token', auth_token)] if not v]
            if missing_fields:
                return {
                    "success": False,
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                    "data": {}
                }

            # User & token validation
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            valid_token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not valid_token:
                return {
                    "success": False,
                    "message": "Authentication failed. Invalid or expired token.",
                    "data": {}
                }

            # Resolve partner/worker
            partner = request.env['res.partner'].sudo().search([('user_id', '=', user_id)], limit=1)
            if worker_id:
                partner = request.env['res.partner'].sudo().browse(worker_id)
            if not partner:
                return {"success": False, "message": "No partner linked to this user.", "data": {}}

            # Teams
            crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', partner.id)], limit=1)
            if not crm_team:
                return {"success": False, "message": "User is not assigned to a CRM team.", "data": {}}

            fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
            if not fsm_team:
                return {"success": False, "message": "User is not linked to any FSM team.", "data": {}}

            # ✅ Fetch ALL configs for this sales team (M2M uses 'in', no limit)
            configs = request.env['rma.return.caused.by'].sudo().search([
                ('sales_teams', 'in', [crm_team.id])
            ])
            if not configs:
                return {
                    "success": False,
                    "message": "No RMA configuration found for user's team.",
                    "data": {}
                }

            # Helpers
            def recs_to_list(records):
                return [{"id": r.id, "name": r.name} for r in records]

            def recs_to_list_with_op(records):
                return [{"id": r.id, "name": r.name, "operation_type": r.operation_type} for r in records]

            # Build unions across all configs
            caused_by_all = configs.mapped('return_caused_by_ids')  # recordset union
            reasons_all = configs.mapped('return_reason_ids')  # recordset union
            types_all = configs.mapped('return_reason_type_ids')  # recordset union

            rma_operation = request.env['rma.operation'].sudo().search([])

            # Backward compatible top-level payload (unions)
            data = {
                "main_config_ids": configs.ids,  # list instead of single id
                "return_caused_by": recs_to_list(caused_by_all),
                "return_reasons": recs_to_list(reasons_all),
                "rma_operation": recs_to_list_with_op(rma_operation),
                "return_types": [
                    {
                        "id": rtype.id,
                        "name": rtype.name,
                        "return_reasons": [
                            {"id": reason.id, "name": reason.name}
                            for reason in reasons_all.filtered(lambda r: r.type.id == rtype.id)
                        ]
                    }
                    for rtype in types_all
                ],
            }

            # Optional: per-config granularity (if you ever need it on the app side)
            data["by_config"] = [
                {
                    "config_id": cfg.id,
                    "return_caused_by": recs_to_list(cfg.return_caused_by_ids),
                    "return_reasons": recs_to_list(cfg.return_reason_ids),
                    "return_types": [
                        {
                            "id": rtype.id,
                            "name": rtype.name,
                            "return_reasons": [
                                {"id": reason.id, "name": reason.name}
                                for reason in cfg.return_reason_ids.filtered(lambda r: r.type.id == rtype.id)
                            ]
                        }
                        for rtype in cfg.return_reason_type_ids
                    ],
                }
                for cfg in configs
            ]

            return {
                "success": True,
                "message": "RMA return configuration retrieved successfully.",
                "data": data
            }

        except Exception as e:
            _logger.exception("Error in /delivery/get/return/data: %s", str(e))
            return {
                "success": False,
                "message": "Internal server error. Please contact support.",
                "error_code": -5,
                "err_message": str(e),
                "data": {}
            }

    # @http.route('/api/v1/delivery/get/return/data', auth='public', type='json', csrf=False, methods=['POST'])
    # def delivery_get_return_data(self, **kwargs):
    #     try:
    #         payload = request.httprequest.json or {}
    #         user_id = int(payload.get('user_id', 0))
    #         worker_id = int(payload.get('worker_id', 0))
    #         auth_token = payload.get('auth_token')
    #
    #         missing_fields = [n for n, v in [('user_id', user_id), ('auth_token', auth_token)] if not v]
    #         if missing_fields:
    #             return {
    #                 "success": False,
    #                 "message": f"Missing required fields: {', '.join(missing_fields)}",
    #                 "data": {}
    #             }
    #
    #         user = request.env['res.users'].sudo().browse(user_id)
    #         if not user.exists():
    #             return {"success": False, "message": "User not found.", "data": {}}
    #
    #         valid_token = request.env['mobile.auth.token'].sudo().search([
    #             ('user_id', '=', user_id),
    #             ('mobile_app_auth_token', '=', auth_token)
    #         ], limit=1)
    #
    #         if not valid_token:
    #             return {
    #                 "success": False,
    #                 "message": "Authentication failed. Invalid or expired token.",
    #                 "data": {}
    #             }
    #
    #         partner = request.env['res.partner'].sudo().search([('user_id', '=', user_id)], limit=1)
    #         if worker_id != 0:
    #             partner = request.env['res.partner'].sudo().browse(worker_id)
    #         if not partner:
    #             return {"success": False, "message": "No partner linked to this user.", "data": {}}
    #
    #         crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', partner.id)], limit=1)
    #         if not crm_team:
    #             return {"success": False, "message": "User is not assigned to a CRM team.", "data": {}}
    #
    #         fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
    #         if not fsm_team:
    #             return {"success": False, "message": "User is not linked to any FSM team.", "data": {}}
    #
    #         return_data = request.env['rma.return.caused.by'].sudo().search([
    #             ('sales_teams', '=', crm_team.id)
    #         ], limit=1)
    #
    #         if not return_data:
    #             return {
    #                 "success": False,
    #                 "message": "No RMA configuration found for user's team.",
    #                 "data": {}
    #             }
    #
    #         def m2m_to_list(records):
    #             return [{"id": rec.id, "name": rec.name} for rec in records]
    #
    #         def m2m_to_list_operation(records):
    #             return [{"id": rec.id, "name": rec.name, "operation_type": rec.operation_type} for rec in records]
    #
    #         rma_operation = request.env['rma.operation'].sudo().search([])
    #
    #         return {
    #             "success": True,
    #             "message": "RMA return configuration retrieved successfully.",
    #             "data": {
    #                 "main_config_id": return_data.id,
    #                 "return_caused_by": m2m_to_list(return_data.return_caused_by_ids),
    #                 "return_reasons": m2m_to_list(return_data.return_reason_ids),
    #                 "rma_operation": m2m_to_list(rma_operation),
    #                 "return_types": [
    #                     {
    #                         "id": rtype.id,
    #                         "name": rtype.name,
    #                         "return_reasons": [
    #                             {
    #                                 "id": reason.id,
    #                                 "name": reason.name
    #                             }
    #                             for reason in return_data.return_reason_ids.filtered(lambda r: r.type.id == rtype.id)
    #                         ]
    #                     }
    #                     for rtype in return_data.return_reason_type_ids
    #                 ],
    #             }
    #         }
    #
    #     except Exception as e:
    #         _logger.exception("Error in /delivery/get/return/data: %s", str(e))
    #         return {
    #             "success": False,
    #             "message": "Internal server error. Please contact support.",
    #             "error_code": -5,
    #             "err_message": str(e),
    #             "data": {}
    #         }
    # ------------------------------------------------------------------
    #  GET DELIVERY DETAILS
    # ------------------------------------------------------------------

    @http.route('/api/v1/delivery/details', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_get_picking_details(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id = int(payload.get('user_id', 0))
            worker_id = int(payload.get('worker_id', 0))
            auth_token = payload.get('auth_token')
            picking_id = int(payload.get('picking_id', 0))
            team_id     = int(payload.get('team_id', 0))  # optional explicit sales team


            missing = [n for n, v in [('user_id', user_id), ('auth_token', auth_token), ('picking_id', picking_id)] if not v]
            if missing:
                return {"success": False, "message": f"Missing required fields: {', '.join(missing)}.", "data": {}}

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            if not request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id), ('mobile_app_auth_token', '=', auth_token)
            ], limit=1):
                return {"success": False, "message": "Invalid or expired authentication token.", "data": {}}

            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {"success": False, "message": "Picking not found.", "data": {}}
            # ---------------- Get team from CRM/FSM logic ----------------
            team = False
            if team_id:
                team = request.env['crm.team'].sudo().browse(team_id)
            else:
                partner = request.env['res.partner'].sudo().search([('user_id', '=', user_id)], limit=1)
                if worker_id != 0:
                    partner = request.env['res.partner'].sudo().browse(worker_id)

                if partner:
                    crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', partner.id)], limit=1)
                    if crm_team:
                        fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
                        if fsm_team:
                            team = crm_team

            # ---------------- Header fields ------------------------------

            data = {
                'batch_sequence': getattr(picking, 'batch_sequence', 0),
                'bill_of_entry_no': getattr(picking, 'bill_of_entry_no', ''),
                'bl_no_asn_no': getattr(picking, 'bl_no_asn_no', ''),
                'carrier_tracking_ref': getattr(picking, 'carrier_tracking_ref', ''),
                'carrier_tracking_url': getattr(picking, 'carrier_tracking_url', ''),
                'date': picking.delivery_planned_date,
                'delivery_type': getattr(picking, 'delivery_type', ''),
                'destination_country_code': getattr(picking, 'destination_country_code', ''),
                'direction': getattr(picking, 'direction', ''),
                'driver_detail': getattr(picking, 'driver_detail', ''),
                'emirates_id': {'id': picking.emirates_id.id, 'name': picking.emirates_id.name} if picking.emirates_id else {},
                'forklift_partner_id': {'id': picking.forklift_partner_id.id, 'name': picking.forklift_partner_id.name} if picking.forklift_partner_id else {},
                'visit_id': picking.fsm_order_id.id if picking.fsm_order_id else False,
                'id': picking.id,
                'invoice_no': getattr(picking, 'invoice_no', ''),
                'location_dest_id': {'id': picking.location_dest_id.id, 'name': picking.location_dest_id.name},
                'location_id': {'id': picking.location_id.id, 'name': picking.location_id.name},
                'lot_id': {'id': picking.lot_id.id, 'name': picking.lot_id.name} if hasattr(picking, 'lot_id') and picking.lot_id else {},
                'move_type': picking.move_type,
                'name': picking.name,
                'note': picking.note,
                'origin': picking.origin,
                'owner_id': {'id': picking.owner_id.id, 'name': picking.owner_id.name} if picking.owner_id else {},
                'packing_slip': getattr(picking, 'packing_slip', ''),
                'partner_id': {'id': picking.partner_id.id, 'name': picking.partner_id.name},
                'picker_partner_id': {'id': picking.picker_partner_id.id, 'name': picking.picker_partner_id.name} if picking.picker_partner_id else {},
                'picking_driver_id': {'id': picking.picking_driver_id.id, 'name': picking.picking_driver_id.name} if hasattr(picking, 'picking_driver_id') and picking.picking_driver_id else {},
                'qty_in_pallet_case': getattr(picking, 'qty_in_pallet_case', 0.0),
                'remark_picking': getattr(picking, 'remark', ''),
                'request_order_id': picking.request_order_id.id if hasattr(picking, 'request_order_id') and picking.request_order_id else False,
                'sale_id': picking.sale_id.id if picking.sale_id else False,
                'scheduled_date': picking.scheduled_date,
                'shipping_doc_ref': getattr(picking, 'shipping_doc_ref', ''),
                'shipping_volume': getattr(picking, 'shipping_volume', 0.0),
                'shipping_weight': getattr(picking, 'shipping_weight', 0.0),
                'status_label': getattr(picking, 'status_label', ''),
                'status': picking.state,
                'stock_request_count': getattr(picking, 'stock_request_count', 0),
                'trx_type': getattr(picking, 'trx_type', ''),
                'vehicle_number': getattr(picking, 'vehicle_number', ''),
                'user_id': picking.user_id.id if picking.user_id else False,
                'warehouse_address_id': {'id': picking.warehouse_address_id.id, 'name': picking.warehouse_address_id.name} if hasattr(picking, 'warehouse_address_id') and picking.warehouse_address_id else {},
                'weight': getattr(picking, 'weight', 0.0),
                'weight_bulk': getattr(picking, 'weight_bulk', 0.0),
                'weight_uom_name': getattr(picking, 'weight_uom_name', ''),
            }

            move_lines_json = []
            for move in picking.move_ids_without_package:
                product = move.sudo().product_id
                qty = move.product_uom_qty
                packaging_data = [p.name for p in product.packaging_ids] if product.packaging_ids else []

                line_json = {
                    'product_id': product.id,
                    'product_name': product.name,
                    'image': self._get_image_url_dynamic(model=product._name, record_id=product.id, field_name='image_1920'),
                    'item_no': product.default_code or '',
                    'barcode': product.barcode or '',
                    'lst_price': product.list_price,
                    'uom': move.product_uom.name,
                    'uom_id': move.product_uom.id,
                    'taxes_id': product.taxes_id.id if product.taxes_id else False,
                    'taxes_name': product.taxes_id.name if product.taxes_id else '',
                    'description': product.description_sale or '',
                    'quantity': qty,
                    'product_packaging': packaging_data,
                    'brand_id': product.brand_id.id if hasattr(product, 'brand_id') and product.brand_id else 0,
                    'brand_name': product.brand_id.name if hasattr(product, 'brand_id') and product.brand_id else 'Unbranded',
                    'division': getattr(move, 'division', ''),
                    'picker_partner_id': {'id': move.picker_partner_id.id, 'name': move.picker_partner_id.name} if hasattr(move, 'picker_partner_id') and move.picker_partner_id else {},
                    'product_picking_id': move.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.name,
                    'move_remark': getattr(move, 'move_remark', ''),
                }
                move_lines_json.append(line_json)

            data['move_lines'] = move_lines_json
            # ---------------- Return‑reason metadata by sales team ---------
            reason_data = []
            type_data   = {}
            if team:
                rc_records = request.env['rma.return.caused.by'].sudo().search([('sales_teams', '=', team.id)])
                for rc in rc_records:
                    for reason in rc.return_reason_ids:
                        reason_data.append({'id': reason.id, 'name': reason.name, 'type_id': reason.type.id if reason.type else False})
                    for t in rc.return_reason_type_ids:
                        type_data[t.id] = t.name
            data['return_reasons'] = reason_data
            data['return_reason_types'] = [{'id': tid, 'name': tname} for tid, tname in type_data.items()]
            data['sales_team'] = {'id': team.id, 'name': team.name} if team else {}

            return {"success": True, "message": "Picking details retrieved successfully.", "data": data}

        except Exception as e:
            _logger.exception("Error in /api/v1/delivery/details: %s", e)
            return {"success": False, "message": str(e), "data": {}}

    @http.route('/api/v1/delivery/invoice/details', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_get_invoice_details(self, **kwargs):
        try:
            payload = request.httprequest.json or {}
            user_id = int(payload.get('user_id', 0))
            worker_id = int(payload.get('worker_id', 0))
            auth_token = payload.get('auth_token')
            invoice_id = int(payload.get('invoice_id', 0))
            picking_id = int(payload.get('picking_id', 0))
            team_id = int(payload.get('team_id', 0))  # optional explicit sales team

            # ---- required fields
            missing = [n for n, v in [('user_id', user_id), ('auth_token', auth_token), ('invoice_id', invoice_id),
                                      ('picking_id', picking_id)] if not v]
            if missing:
                return {"success": False, "message": f"Missing required fields: {', '.join(missing)}.", "data": {}}

            # ---- user & token
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            token_ok = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token_ok:
                return {"success": False, "message": "Invalid or expired authentication token.", "data": {}}

            # ---- data sources
            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists():
                return {"success": False, "message": "Invoice not found.", "data": {}}

            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {"success": False, "message": "Picking not found.", "data": {}}

            # ---- team resolution (explicit > worker > user)
            team = False
            if team_id and team_id != 0:
                team = request.env['crm.team'].sudo().browse(team_id)
            else:
                partner = request.env['res.partner'].sudo().search([('user_id', '=', user_id)], limit=1)
                if worker_id:
                    partner = request.env['res.partner'].sudo().browse(worker_id)
                if partner:
                    crm_team = request.env['crm.team'].sudo().search([('partner_member_ids', 'in', partner.id)],
                                                                     limit=1)
                    if crm_team:
                        fsm_team = request.env['fsm.team'].sudo().search([('sales_team_id', '=', crm_team.id)], limit=1)
                        if fsm_team:
                            team = crm_team

            # =========================
            #  HEADER (split correctly)
            # =========================
            data = {
                # ---- picking-sourced header
                'id': picking.id,
                'name': picking.name,
                'status': picking.state,
                'status_label': getattr(picking, 'status_label', ''),
                'move_type': picking.move_type,
                'scheduled_date': picking.scheduled_date,
                'date': picking.delivery_planned_date,
                'origin': picking.origin,
                'partner_id': {'id': picking.partner_id.id,
                               'name': picking.partner_id.name} if picking.partner_id else {},
                'location_id': {'id': picking.location_id.id,
                                'name': picking.location_id.name} if picking.location_id else {},
                'location_dest_id': {'id': picking.location_dest_id.id,
                                     'name': picking.location_dest_id.name} if picking.location_dest_id else {},
                'owner_id': {'id': picking.owner_id.id, 'name': picking.owner_id.name} if picking.owner_id else {},
                'visit_id': picking.fsm_order_id.id if getattr(picking, 'fsm_order_id', False) else False,
                'note': picking.note,

                # misc picking extras (safe getattr)
                'batch_sequence': getattr(picking, 'batch_sequence', 0),
                'bill_of_entry_no': getattr(picking, 'bill_of_entry_no', ''),
                'bl_no_asn_no': getattr(picking, 'bl_no_asn_no', ''),
                'carrier_tracking_ref': getattr(picking, 'carrier_tracking_ref', ''),
                'carrier_tracking_url': getattr(picking, 'carrier_tracking_url', ''),
                'delivery_type': getattr(picking, 'delivery_type', ''),
                'destination_country_code': getattr(picking, 'destination_country_code', ''),
                'direction': getattr(picking, 'direction', ''),
                'driver_detail': getattr(picking, 'driver_detail', ''),
                'emirates_id': {'id': picking.emirates_id.id, 'name': picking.emirates_id.name} if getattr(picking,
                                                                                                           'emirates_id',
                                                                                                           False) else {},
                'forklift_partner_id': {'id': picking.forklift_partner_id.id,
                                        'name': picking.forklift_partner_id.name} if getattr(picking,
                                                                                             'forklift_partner_id',
                                                                                             False) else {},
                'picker_partner_id': {'id': picking.picker_partner_id.id,
                                      'name': picking.picker_partner_id.name} if getattr(picking, 'picker_partner_id',
                                                                                         False) else {},
                'picking_driver_id': {'id': picking.picking_driver_id.id,
                                      'name': picking.picking_driver_id.name} if getattr(picking, 'picking_driver_id',
                                                                                         False) else {},
                'qty_in_pallet_case': getattr(picking, 'qty_in_pallet_case', 0.0),
                'packing_slip': getattr(picking, 'packing_slip', ''),
                'request_order_id': picking.request_order_id.id if getattr(picking, 'request_order_id',
                                                                           False) else False,
                'sale_id': picking.sale_id.id if picking.sale_id else False,
                'shipping_doc_ref': getattr(picking, 'shipping_doc_ref', ''),
                'shipping_volume': getattr(picking, 'shipping_volume', 0.0),
                'shipping_weight': getattr(picking, 'shipping_weight', 0.0),
                'trx_type': getattr(picking, 'trx_type', ''),
                'vehicle_number': getattr(picking, 'vehicle_number', ''),
                'user_id': picking.user_id.id if picking.user_id else False,
                'warehouse_address_id': {'id': picking.warehouse_address_id.id,
                                         'name': picking.warehouse_address_id.name} if getattr(picking,
                                                                                               'warehouse_address_id',
                                                                                               False) else {},
                'weight': getattr(picking, 'weight', 0.0),
                'weight_bulk': getattr(picking, 'weight_bulk', 0.0),
                'weight_uom_name': getattr(picking, 'weight_uom_name', ''),

                # ---- invoice-sourced header
                'invoice': {
                    'id': invoice.id,
                    'name': invoice.name,  # invoice number / sequence
                    'invoice_date': invoice.invoice_date,
                    'invoice_origin': invoice.invoice_origin,
                    'ref': invoice.ref,
                    'partner_id': {'id': invoice.partner_id.id,
                                   'name': invoice.partner_id.name} if invoice.partner_id else {},
                    'currency_id': {'id': invoice.currency_id.id,
                                    'name': invoice.currency_id.name} if invoice.currency_id else {},
                    'amount_untaxed': invoice.amount_untaxed,
                    'amount_tax': invoice.amount_tax,
                    'amount_total': invoice.amount_total,
                    'state': invoice.state,
                    'payment_state': getattr(invoice, 'payment_state', ''),
                    'move_type': invoice.move_type,
                },
            }

            # =========================
            #  LINES (from INVOICE)
            # =========================
            # product lines only: exclude sections / notes (display_type is False)
            # account.move.line fields: quantity, price_unit, price_subtotal, product_uom_id, product_id, tax_ids, name
            inv_lines = invoice.invoice_line_ids.sudo()
            move_lines_json = []
            for line in inv_lines:
                product = line.product_id
                uom = line.product_uom_id or product.uom_id
                taxes = line.tax_ids[:1]  # keep same single-tax shape as your old structure; adjust if you need multi
                packaging_data = [p.name for p in (product.packaging_ids or [])]

                move_lines_json.append({
                    # product basics
                    'product_id': product.id,
                    'product_name': product.display_name or product.name or line.name,
                    'image': self._get_image_url_dynamic(model=product._name, record_id=product.id,
                                                         field_name='image_1920'),

                    # identifiers
                    'item_no': product.default_code or '',
                    'barcode': product.barcode or '',

                    # pricing & qty (from invoice line)
                    'lst_price': product.list_price,  # product catalog price (not invoice price)
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': getattr(line, 'price_subtotal', 0.0),

                    # uom & taxes
                    'uom': uom.name if uom else '',
                    'uom_id': uom.id if uom else False,
                    'taxes_id': taxes.id if taxes else False,
                    'taxes_name': taxes.name if taxes else '',

                    # misc (best-effort to keep front-end keys stable)
                    'description': line.name or (product.description_sale or ''),
                    'product_packaging': packaging_data,
                    'brand_id': getattr(product, 'brand_id', False).id if getattr(product, 'brand_id', False) else 0,
                    'brand_name': getattr(product, 'brand_id', False).name if getattr(product, 'brand_id',
                                                                                      False) else 'Unbranded',
                    'division': '',  # not available at invoice line by default
                    'picker_partner_id': {},  # invoice context has no picker
                    'product_picking_id': False,  # this is from stock.move; N/A for invoice lines
                    'product_uom_qty': line.quantity,
                    'product_uom': uom.name if uom else '',
                    'move_remark': '',
                })
            data['move_lines'] = move_lines_json

            # =========================
            #  RMA CONFIG (same shape as /get/return/data)
            # =========================
            def recs_to_list(records):
                return [{"id": r.id, "name": r.name} for r in records]

            def recs_to_list_with_op(records):
                return [{"id": r.id, "name": r.name, "operation_type": r.operation_type} for r in records]

            configs = request.env['rma.return.caused.by'].sudo().search([
                ('sales_teams', 'in', [team.id])  # correct M2M operator
            ]) if team else request.env['rma.return.caused.by'].sudo().browse([])
            if configs:
                caused_by_all = configs.mapped('return_caused_by_ids')
                reasons_all = configs.mapped('return_reason_ids')
                types_all = configs.mapped('return_reason_type_ids')
            else:
                caused_by_all = request.env['rma.return.caused.by'].sudo().browse().return_caused_by_ids
                reasons_all = request.env['rma.return.caused.by'].sudo().browse().return_reason_ids
                types_all = request.env['rma.return.caused.by'].sudo().browse().return_reason_type_ids

            rma_operation = request.env['rma.operation'].sudo().search([])

            data.update({
                "main_config_ids": configs.ids if configs else [],
                "return_caused_by": recs_to_list(caused_by_all),
                "return_reasons": recs_to_list(reasons_all),
                "rma_operation": recs_to_list_with_op(rma_operation),
                "return_types": [
                    {
                        "id": rtype.id,
                        "name": rtype.name,
                        "return_reasons": [
                            {"id": reason.id, "name": reason.name}
                            for reason in reasons_all.filtered(lambda r: r.type.id == rtype.id)
                        ],
                    }
                    for rtype in types_all
                ],
                "by_config": [
                    {
                        "config_id": cfg.id,
                        "return_caused_by": recs_to_list(cfg.return_caused_by_ids),
                        "return_reasons": recs_to_list(cfg.return_reason_ids),
                        "return_types": [
                            {
                                "id": rtype.id,
                                "name": rtype.name,
                                "return_reasons": [
                                    {"id": reason.id, "name": reason.name}
                                    for reason in cfg.return_reason_ids.filtered(lambda r: r.type.id == rtype.id)
                                ],
                            }
                            for rtype in cfg.return_reason_type_ids
                        ],
                    }
                    for cfg in configs
                ],
                "sales_team": {'id': team.id, 'name': team.name} if team else {},
            })

            return {"success": True, "message": "Invoice & picking details retrieved successfully.", "data": data}

        except Exception as e:
            _logger.exception("Error in /api/v1/delivery/invoice/details: %s", e)
            return {"success": False, "message": "Internal server error.", "data": {}, "err_message": str(e)}

    @http.route('/api/v1/delivery/rma/create', auth='public', type='json', csrf=False, methods=['POST'])
    def create_rma(self, **kwargs):
        """
        Create RMA based on INVOICE (base_on_invoice).
        Keeps duplicate-safe line mapping like your full-return flow.
        """
        try:
            payload = request.httprequest.json or {}

            # ---- required keys ----
            required = {
                'user_id': int,
                'auth_token': str,
                'partner_id': int,
                'visit_id': int,
                'picking_id': int,
                'invoice_id': int,              # <- NEW: now required
                'return_caused_by_id': int,
                'operation_id': int,
                'product_line_ids': list,
            }
            missing = [k for k in required if payload.get(k) in (None, '', [])]
            if missing:
                return {
                    'success': False,
                    'error_msg': _("Missing required fields: %s") % ", ".join(missing)
                }

            # ---- auth ----
            user_id    = int(payload['user_id'])
            worker_id  = int(payload.get('worker_id', 0))
            auth_token = payload['auth_token']

            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {'success': False, 'error_msg': _("Invalid user ID.")}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id','=',user_id),
                ('mobile_app_auth_token','=',auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': _("Invalid or expired auth token.")}

            # ---- header inputs ----
            partner_id       = int(payload['partner_id'])
            visit_id         = int(payload['visit_id'])
            picking_id       = int(payload['picking_id'])
            invoice_id       = int(payload['invoice_id'])   # <- NEW
            header_caused_by = int(payload['return_caused_by_id'])
            return_reason_id = int(payload['return_reason_id'])
            return_reason_type_id = int(payload['return_type_id'])
            operation_id     = int(payload['operation_id'])
            remarks          = (payload.get('remarks') or '').strip()
            lines_payload    = payload['product_line_ids'] or []

            # ---- validate partner / picking / invoice ----
            partner = request.env['res.partner'].sudo().browse(partner_id)
            if not partner.exists():
                return {'success': False, 'error_msg': _("Invalid partner_id.")}

            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {'success': False, 'error_msg': _("Invalid picking_id.")}

            account_move = request.env['account.move'].sudo().browse(invoice_id)
            if not account_move.exists():
                return {'success': False, 'error_msg': _("Invalid invoice_id.")}

            # ---- resolve worker → team (mirrors your reference) ----
            worker_partner = user.partner_id
            if worker_id:
                wp = request.env['res.partner'].sudo().browse(worker_id)
                if wp.exists():
                    worker_partner = wp

            crm_team = request.env['crm.team'].sudo().search(
                [('partner_member_ids', 'in', [worker_partner.id])],
                limit=1
            )
            if not crm_team:
                p = request.env['res.partner'].sudo().search([('user_id','=',user_id)], limit=1)
                if p:
                    crm_team = request.env['crm.team'].sudo().search(
                        [('partner_member_ids','in',[p.id])], limit=1
                    )
            if not crm_team:
                return {'success': False, 'error_msg': _("User is not assigned to a sales team.")}

            # ---- create RMA header (BASE ON INVOICE) ----
            RMA = request.env['rma'].sudo()
            rma_vals = {
                'partner_id':            partner_id,
                'user_id':               user_id,
                'date':                  fields.Datetime.now(),  # server time
                'responsible_worker_id': worker_partner.id,
                'crm_team_id':           crm_team.id,
                'visit_id':              visit_id,
                'picking_id':            picking_id,
                'invoice_id':            invoice_id,            # <- NEW
                'remarks':               remarks,
                'return_caused_by_id':   header_caused_by,
                'return_reason_id':      return_reason_id,
                'return_reason_type_id': return_reason_type_id,
                'rma_type':              'base_on_invoice',     # <- NEW
                'operation_id':          operation_id,
                'currency_id':           request.env.company.currency_id.id,
                'company_id':            user.company_id.id,
            }
            rma = RMA.with_user(SUPERUSER_ID).create(rma_vals)

            # Initial GRV (recomputed later)
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # ---------- duplicate-safe line updates ----------
            existing_lines_pool = defaultdict(list)
            for l in rma.line_ids.sorted(key=lambda rec: rec.id):
                existing_lines_pool[l.product_id.id].append(l)

            def _safe_int(x):
                try: return int(x or 0)
                except Exception: return 0

            def _safe_float(x):
                try: return float(x or 0.0)
                except Exception: return 0.0


            def _pop_matching_line(product_id, product_packaging_id, return_reason_id, return_reason_type_id, return_caused_by_id):
                """Pop ONE unused existing line for this product. Prefer an exact match if optional fields provided."""
                bucket = existing_lines_pool.get(product_id) or []

                def _is_exact(line):
                    if product_packaging_id and (line.product_packaging_id.id or 0) != product_packaging_id:
                        return False
                    if return_reason_id and (line.return_reason_id.id or 0) != return_reason_id:
                        return False
                    if return_reason_type_id and (line.return_reason_type_id.id or 0) != return_reason_type_id:
                        return False
                    if return_caused_by_id and (line.return_caused_by_id.id or 0) != return_caused_by_id:
                        return False
                    return True

                # exact match first
                for i, line in enumerate(bucket):
                    if _is_exact(line):
                        bucket.pop(i)
                        if not bucket:
                            existing_lines_pool.pop(product_id, None)
                        return line

                # fallback: any remaining line
                if bucket:
                    line = bucket.pop(0)
                    if not bucket:
                        existing_lines_pool.pop(product_id, None)
                    return line
                return None

            updated_line_ids = []
            to_mirror_lines  = []   # collect touched lines to mirror into rma.invoice.line

            for row in lines_payload:
                product_id         = _safe_int(row.get('product_id'))
                returned_qty       = _safe_float(row.get('quantity'))
                return_caused_by_id= _safe_int(row.get('return_caused_by_id'))
                return_reason_id   = _safe_int(row.get('return_reason_id'))
                return_type_id     = _safe_int(row.get('return_type_id'))
                product_packaging_qty = _safe_float(row.get('product_packaging_qty'))
                product_packaging_id = _safe_int(row.get('product_packaging_id'))

                existing_line = _pop_matching_line(product_id,product_packaging_qty, return_reason_id, return_type_id, return_caused_by_id)
                if existing_line:
                    existing_line.sudo().with_user(SUPERUSER_ID).write({
                        'product_uom_qty':       returned_qty,
                        'return_reason_id':      return_reason_id or False,
                        'return_reason_type_id': return_type_id or False,
                        'return_caused_by_id':   return_caused_by_id or False,
                        # keep financials as-is
                        'exercise_price':        existing_line.exercise_price,
                    })
                    updated_line_ids.append(existing_line.id)
                    to_mirror_lines.append(existing_line)
                else:
                    _logger.warning(
                        "RMA %s: no unused line left to match product %s (reason=%s, type=%s, cause=%s)",
                        rma.id, product_id, return_reason_id, return_type_id, return_caused_by_id
                    )

            # Recompute, prune untouched, recompute again
            rma.sudo().compute_line_ids()
            other_lines = rma.line_ids.filtered(lambda l: l.id not in updated_line_ids)
            if other_lines:
                try:
                    other_lines.with_user(SUPERUSER_ID).unlink()
                except Exception as e:
                    _logger.info("RMA %s: failed to unlink untouched lines: %s", rma.id, str(e))

            rma.sudo().compute_line_ids()
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # Mirror into rma.invoice.line (same pattern as your full-return)
            for one in to_mirror_lines:
                request.env['rma.invoice.line'].sudo().create({
                    'product_uom_qty':        one.product_uom_qty,
                    'product_packaging_qty':  one.product_packaging_qty,
                    # 'product_packaging_id': one.product_packaging_id.id,
                    'return_reason_id':       one.return_reason_id.id,
                    'return_reason_type_id':  one.return_reason_type_id.id,
                    'return_caused_by_id':    one.return_caused_by_id.id,
                    'product_id':             one.product_id.id,
                    'price_unit':             one.price_unit,
                    'product_uom_id':         one.product_uom_id.id,
                    'rma_id':                 one.rma_id.id,
                    'move_id':                one.move_id.id if one.move_id else False,
                    'move_line_id':           one.move_line_id.id if one.move_line_id else False,
                    'system_unit_price':      one.system_unit_price,
                    'tax_id':                 [(4, one.tax_id.id)] if one.tax_id else False,
                    'discount':               one.discount,
                    'exercise_price':         one.exercise_price,
                    'analytic_distribution':  one.analytic_distribution,
                })

            # Submit workflow
            rma.action_submit_rma()

            _logger.info("RMA #%s (base_on_invoice) created by user %s", rma.id, user_id)
            if picking:
                picking.state = "returned"

            return {
                'success': True,
                'message': _("RMA created successfully."),
                'rma_id': rma.id,
                'invoice_id': invoice_id,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/delivery/rma/create: %s", e)
            return {'success': False, 'error_msg': _("Internal server error."), 'detail': str(e)}
    # ------------------------------------------------------------------
    #  PARTIAL DELIVERY RETURN (CREATE RMA) — Invoice-based (mobile → RMA)
    # ------------------------------------------------------------------
    @http.route('/api/v1/delivery/partial/return', auth='public', type='json', csrf=False, methods=['POST'])
    def delivery_partial_return_picking(self, **kwargs):
        """
        Create an invoice-based RMA.
        - Only the lines provided by mobile are applied.
        - For each sent line, we UPDATE a pre-existing RMA line (created from the invoice).
        - Any RMA lines not represented by the mobile payload are deleted.
        """
        try:
            payload = request.httprequest.json or {}

            # 1) Required top-level fields
            required = [
                'user_id', 'auth_token', 'partner_id',
                'visit_id', 'picking_id', 'invoice_id',
                'return_caused_by_id', 'operation_id', 'product_line_ids'
            ]
            missing = [k for k in required if payload.get(k) in (None, '', [])]
            if missing:
                return {'success': False,
                        'error_msg': _("Missing required fields: %s") % ", ".join(missing)}

            # 2) Auth
            uid       = int(payload['user_id'])
            worker_id = int(payload.get('worker_id', 0))
            token     = payload['auth_token']

            user = request.env['res.users'].sudo().browse(uid)
            if not user.exists():
                return {'success': False, 'error_msg': _("Invalid user ID.")}

            if not request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', uid), ('mobile_app_auth_token', '=', token)
            ], limit=1):
                return {'success': False, 'error_msg': _("Invalid or expired auth token.")}

            # 3) Validate partner / picking / invoice
            partner_id = int(payload['partner_id'])
            visit_id   = int(payload['visit_id'])
            picking    = request.env['stock.picking'].sudo().browse(int(payload['picking_id']))
            invoice    = request.env['account.move'].sudo().browse(int(payload['invoice_id']))

            if not request.env['res.partner'].sudo().browse(partner_id).exists():
                return {'success': False, 'error_msg': _("Invalid partner_id.")}
            if not picking.exists():
                return {'success': False, 'error_msg': _("Invalid picking_id.")}
            if not invoice.exists():
                return {'success': False, 'error_msg': _("Invalid invoice_id.")}

            # 4) Resolve worker → CRM team
            worker_partner = user.partner_id
            if worker_id:
                wp = request.env['res.partner'].sudo().browse(worker_id)
                if wp.exists():
                    worker_partner = wp

            crm_team = request.env['crm.team'].sudo().search(
                [('partner_member_ids', 'in', worker_partner.id)], limit=1
            )
            if not crm_team:
                p = request.env['res.partner'].sudo().search([('user_id', '=', uid)], limit=1)
                if p:
                    crm_team = request.env['crm.team'].sudo().search(
                        [('partner_member_ids', 'in', p.id)], limit=1
                    )
            if not crm_team:
                return {'success': False, 'error_msg': _("User is not assigned to a sales team.")}

            # 5) Create the RMA header (BASE ON INVOICE)
            remarks          = (payload.get('remarks') or '').strip()
            header_cause_id  = int(payload['return_caused_by_id'])
            operation_id     = int(payload['operation_id'])
            header_reason_id = int(payload.get('return_reason_id', 0) or 0)       # optional on header
            header_type_id   = int(payload.get('return_type_id', 0) or 0)         # optional on header

            RMA = request.env['rma'].sudo()
            rma_vals = {
                'partner_id'            : partner_id,
                'user_id'               : uid,
                'date'                  : fields.Datetime.now(),
                'responsible_worker_id' : worker_partner.id,
                'crm_team_id'           : crm_team.id,
                'visit_id'              : visit_id,
                # 'picking_id'            : picking.id,
                'invoice_id'            : invoice.id,
                'remarks'               : remarks,
                'return_caused_by_id'   : header_cause_id,
                'return_reason_id'      : header_reason_id or False,
                'return_reason_type_id' : header_type_id or False,
                'operation_id'          : operation_id,
                'rma_type'              : 'base_on_invoice',
                'currency_id'           : request.env.company.currency_id.id,
                'company_id'            : user.company_id.id,
            }
            rma = RMA.with_user(SUPERUSER_ID).create(rma_vals)
            _logger.info("Partial RMA #%s (invoice-based) created by user %s", rma.id, uid)

            # Prepare GRV (recomputed later)
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # 6) UPDATE existing RMA lines (created from invoice) instead of creating new ones
            # Build a pool by product (duplicate-safe). Extend the key if you also need to
            # differentiate by packaging, lot, etc.
            existing_pool = defaultdict(list)
            for ln in rma.line_ids.sorted(key=lambda rec: rec.id):
                existing_pool[ln.product_id.id].append(ln)

            def _i(x):
                try: return int(x or 0)
                except Exception: return 0

            def _f(x):
                try: return float(x or 0.0)
                except Exception: return 0.0

            def _pop_matching_line(product_id, reason_id, type_id, cause_id):
                """Pick ONE not-yet-used RMA line for this product, preferring an exact attribute match."""
                bucket = existing_pool.get(product_id) or []

                def exact(line):
                    if reason_id and (line.return_reason_id.id or 0) != reason_id:
                        return False
                    if type_id and (line.return_reason_type_id.id or 0) != type_id:
                        return False
                    if cause_id and (line.return_caused_by_id.id or 0) != cause_id:
                        return False
                    return True

                # exact match first
                for idx, ln in enumerate(bucket):
                    if exact(ln):
                        bucket.pop(idx)
                        if not bucket:
                            existing_pool.pop(product_id, None)
                        return ln

                # fallback: any remaining line for this product
                if bucket:
                    ln = bucket.pop(0)
                    if not bucket:
                        existing_pool.pop(product_id, None)
                    return ln
                return None

            updated_ids   = []
            mirrored_rows = []
            lines_payload = payload['product_line_ids'] or []

            for idx, row in enumerate(lines_payload, start=1):
                # Validate per-line required keys
                for key in ('product_id', 'quantity', 'return_reason_id', 'return_type_id'):
                    if row.get(key) in (None, ''):
                        return {'success': False,
                                'error_msg': _("Line %s: missing %s") % (idx, key)}

                prod_id      = _i(row.get('product_id'))
                qty          = _f(row.get('quantity'))
                reason_id    = _i(row.get('return_reason_id'))
                type_id      = _i(row.get('return_type_id'))
                cause_id     = _i(row.get('return_caused_by_id') or header_cause_id)

                rma_line = _pop_matching_line(prod_id, reason_id, type_id, cause_id)

                if rma_line:
                    # Only update the fields that come from mobile — keep price/taxes/uom/etc.
                    rma_line.sudo().with_user(SUPERUSER_ID).write({
                        'product_uom_qty'       : qty,
                        'return_reason_id'      : reason_id or False,
                        'return_reason_type_id' : type_id or False,
                        'return_caused_by_id'   : cause_id or False,
                        # 'product_packaging_id' : packaging_id or False,
                        # 'product_packaging_qty': packaging_qty or 0.0,
                        'exercise_price'        : rma_line.exercise_price,  # preserve
                    })
                    updated_ids.append(rma_line.id)
                    mirrored_rows.append(rma_line)
                else:
                    _logger.warning(
                        "RMA %s: no unused line left to match product %s (reason=%s type=%s cause=%s)",
                        rma.id, prod_id, reason_id, type_id, cause_id
                    )

            # 7) Recompute, prune untouched, recompute again
            rma.sudo().compute_line_ids()
            leftovers = rma.line_ids.filtered(lambda l: l.id not in updated_ids)
            if leftovers:
                try:
                    leftovers.with_user(SUPERUSER_ID).unlink()
                except Exception as e:
                    _logger.info("RMA %s: failed to unlink untouched lines: %s", rma.id, str(e))

            rma.sudo().compute_line_ids()
            rma.grv_amount = abs(sum(line.total for line in rma.line_ids))

            # 8) Mirror updated lines into rma.invoice.line
            for one in mirrored_rows:
                request.env['rma.invoice.line'].sudo().create({
                    'product_uom_qty'       : one.product_uom_qty,
                    'product_packaging_qty' : getattr(one, 'product_packaging_qty', 0.0),
                    # 'product_packaging_id': one.product_packaging_id.id if one.product_packaging_id else False,
                    'return_reason_id'      : one.return_reason_id.id,
                    'return_reason_type_id' : one.return_reason_type_id.id,
                    'return_caused_by_id'   : one.return_caused_by_id.id,
                    'product_id'            : one.product_id.id,
                    'price_unit'            : one.price_unit,
                    'product_uom_id'        : one.product_uom_id.id,
                    'rma_id'                : one.rma_id.id,
                    'move_id'               : one.move_id.id if getattr(one, 'move_id', False) else False,
                    'move_line_id'          : one.move_line_id.id if getattr(one, 'move_line_id', False) else False,
                    'system_unit_price'     : getattr(one, 'system_unit_price', 0.0),
                    'tax_id'                : [(6, 0, one.tax_id.ids)],
                    'discount'              : one.discount,
                    'exercise_price'        : getattr(one, 'exercise_price', 0.0),
                    'analytic_distribution' : one.analytic_distribution,
                })

            # 9) Workflow + picking status
            rma.action_submit_rma()
            if picking:
                picking.state = "delivered_partial"

            return {
                'success'   : True,
                'message'   : _("Partial-delivery RMA (invoice-based) updated successfully."),
                'rma_id'    : rma.id,
                'invoice_id': invoice.id,
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/delivery/partial/return: %s", e)
            return {
                'success'   : False,
                'error_msg' : _("Internal server error."),
                'detail'    : str(e)
            }
    # API: Link a Picking with an FSM Visit + Execute action_collect
    # ------------------------------------------------------------------
    @http.route('/api/v1/delivery/return/collect', auth='public', type='json', csrf=False, methods=['POST'])
    def api_link_fsm_visit_and_collect(self, **kwargs):
        """
        Body (JSON):
        {
            "user_id": <int>,
            "auth_token": "<str>",
            "visit_id": <int>,
            "picking_id": <int>,
            "force_update": <bool, optional>  # if True, overwrite existing fsm_order_id
        }

        Response:
        {
            "success": True/False,
            "message": "...",
            "data": {
                "picking_id": <int>,
                "visit_id": <int>,
                "picking_name": <str>,
                "fsm_order_id": <int>
            }
        }
        """
        try:
            payload    = request.httprequest.json or {}
            user_id    = int(payload.get('user_id', 0))
            worker_id    = int(payload.get('worker_id', 0))
            auth_token = payload.get('auth_token')
            _logger.info("PPPPPPPPPPPPPPPPPPPPPPPP")
            _logger.info("value of visit ")
            _logger.info(payload.get("visit_id"))

            visit_id   = int(payload.get('visit_id', 0))
            picking_id = int(payload.get('picking_id', 0))
            force_upd  = bool(payload.get('force_update', False))

            # ---------- Basic presence validation ----------
            missing = [n for n, v in [
                ('user_id', user_id),
                ('auth_token', auth_token),
                ('visit_id', visit_id),
                ('picking_id', picking_id),
            ] if not v]
            if missing:
                return {
                    "success": False,
                    "message": f"Missing required fields: {', '.join(missing)}.",
                    "data": {}
                }

            # ---------- User validation ----------
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {"success": False, "message": "User not found.", "data": {}}

            token_ok = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token_ok:
                return {
                    "success": False,
                    "message": "Invalid or expired authentication token.",
                    "data": {}
                }

            # ---------- Visit validation (optional but safer) ----------
            fsm_order = request.env['fsm.order'].sudo().browse(visit_id)
            if not fsm_order.exists():
                return {
                    "success": False,
                    "message": "FSM Visit (fsm.order) not found.",
                    "data": {}
                }

            # (Optional) You can further check that this visit belongs to same customer, etc.
            # Example: if picking.partner_id.id != fsm_order.partner_id.id: ...

            # ---------- Picking validation ----------
            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return {"success": False, "message": "Picking not found.", "data": {}}

            # ---------- Guard: picking already linked? ----------
            if picking.fsm_order_id and picking.fsm_order_id.id != visit_id and not force_upd:
                return {
                    "success": False,
                    "message": (
                        "Picking already linked to a different FSM visit "
                        f"(fsm_order_id={picking.fsm_order_id.id}). Set force_update=true to overwrite."
                    ),
                    "data": {
                        "picking_id": picking.id,
                        "current_fsm_order_id": picking.fsm_order_id.id
                    }
                }

            # ---------- Write link ----------
            picking.write({'fsm_order_id': visit_id})

            # ---------- Execute picking action ----------
            # Ensure the method exists to avoid AttributeError
            if hasattr(picking, 'action_collect'):
                # Some Odoo methods expect recordsets; SAFEGUARD with sudo if needed
                picking.action_collect()
            else:
                _logger.warning("Picking %s has no method action_collect()", picking.id)
                # Decide: treat as success or failure; here we continue.

            return {
                "success": True,
                "message": "Picking linked to FSM visit and collection action executed.",
                "data": {
                    "picking_id"   : picking.id,
                    "visit_id"     : visit_id,
                    "picking_name" : picking.name,
                    "fsm_order_id" : picking.fsm_order_id.id,
                }
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/delivery/return/collect: %s", e)
            return {
                "success": False,
                "message": "Internal server error.",
                "message_details": str(e),
                "error_code": -5,
                "data": {}
            }

    # ---------- small helpers ----------
    def _parse_int(self, val, default=0):
        try:
            return int(val) if val not in (None, "") else default
        except Exception:
            return default

    def _split_version(self, v):
        """'1.2.10' -> [1,2,10]; '1.2.0-beta' -> [1,2,0]."""
        if not v:
            return []
        out = []
        for part in str(v).split('.'):
            if part.isdigit():
                out.append(int(part))
            else:
                digits = ''.join(ch for ch in part if ch.isdigit())
                out.append(int(digits) if digits else 0)
        return out

    def _is_version_older(self, curr, latest):
        a, b = self._split_version(curr), self._split_version(latest)
        L = max(len(a), len(b))
        a += [0] * (L - len(a))
        b += [0] * (L - len(b))
        return a < b

    def _actor_partner(self, user, worker_id):
        """Return the partner we consider the 'actor' (worker if provided & exists, else user's partner)."""
        if worker_id:
            p = request.env['res.partner'].sudo().browse(worker_id)
            if p and p.exists():
                return p
        return user.partner_id

    @http.route('/api/v1/app_status', type='json', auth='public', methods=['POST'], csrf=False)
    def app_status(self, **kw):
        """
        One gate to rule them all:
        - Validates auth token
        - (Optional) admin hard-stop
        - Custodian requirements (for sales/order roles)
        - Payment transfer in progress
        - App version policy (must be on latest)
        """
        try:
            payload     = request.httprequest.json or {}
            user_id     = self._parse_int(payload.get('user_id'))
            worker_id   = self._parse_int(payload.get('worker_id'))
            auth_token  = payload.get('auth_token')
            app_version = payload.get('app_version')  # e.g. "1.4.2"

            # ---------- Basic presence validation ----------
            missing = [n for n, v in (('user_id', user_id),
                                      ('auth_token', auth_token),
                                      ('app_version', app_version)) if not v]
            if missing:
                return {
                    "success": False,
                    "app_enabled": False,
                    "reason_code": "BAD_REQUEST",
                    "message": f"Missing required fields: {', '.join(missing)}.",
                    "data": {}
                }

            # ---------- User & token ----------
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                return {
                    "success": False, "app_enabled": False,
                    "reason_code": "USER_NOT_FOUND",
                    "message": "User not found.", "data": {}
                }

            token_ok = request.env['mobile.auth.token'].sudo().search_count([
                ('user_id', '=', user.id),
                ('mobile_app_auth_token', '=', auth_token)
            ])
            if not token_ok:
                return {
                    "success": False, "app_enabled": False,
                    "reason_code": "BAD_TOKEN",
                    "message": "Invalid or expired authentication token.",
                    "data": {}
                }

            partner = self._actor_partner(user, worker_id)

            # ---------- App admin hard-stop (optional) ----------
            mobile_app = request.env['gulfco.mobile.app'].sudo().search([('current_app', '=', True)], limit=1)
            # NEW: worker permission flag from worker.config (per current app & worker)
            update_customer_geo_location = False
            allow_to_pay_in_multiple_ways = False
            allow_to_cancel_sale_order = False
            if mobile_app and partner:
                wc = request.env['worker.config'].sudo().search([
                    ('app_id', '=', mobile_app.id),
                    ('worker_id', '=', partner.id),
                ], limit=1)
                update_customer_geo_location = bool(getattr(wc, 'update_customer_geo_location', False))
                allow_to_pay_in_multiple_ways = bool(getattr(wc, 'allow_to_pay_in_multiple_ways', False))
                allow_to_cancel_sale_order = bool(getattr(wc, 'allow_to_cancel_sale_order', False))

            if mobile_app and getattr(mobile_app, 'app_hard_stop', False):
                stop_msg = mobile_app.hard_stop_reason or \
                           "The application is stopped by your management. Please contact them."
                return {
                    "success": True,
                    "app_enabled": False,
                    "reason_code": "APP_HARD_STOP",
                    "message": stop_msg,
                    "data": {
                        "your_version": app_version,
                        "latest_version": mobile_app.current_version or None,
                    }
                }

            # ---------- Role that requires custodian ----------
            roles_require_custodian = {'sales_user'}
            user_type = getattr(user, 'user_type', False)

            custodian = None
            if user_type in roles_require_custodian:
                custodian = request.env['custodian'].sudo().search([
                    ("responsible_custodian", "=", partner.id)
                ], limit=1)

                if not custodian:
                    return {
                        "success": True,
                        "app_enabled": False,
                        "reason_code": "NO_CUSTODIAN",
                        "message": "You do not have a custodian assigned. Please contact your management.",
                        "data": {"partner_id": partner.id}
                    }

                # ---------- Payment transfer in progress ----------
                transfer = request.env['payments.transfer'].sudo().search([
                    ('state', '=', 'in_progress'),
                    '|', ('from_custodian_id', '=', custodian.id),
                         ('to_custodian_id', '=', custodian.id),
                ], limit=1)

                if transfer:
                    return {
                        "success": True,
                        "app_enabled": False,
                        "reason_code": "TRANSFER_IN_PROGRESS",
                        "message": (
                            "The application is stopped by your management. "
                            "A payment transfer is in progress for your custodian. "
                            "Please complete or close the transfer, or contact management."
                        ),
                        "data": {
                            "transfer_id": transfer.id,
                            "transfer_name": transfer.display_name,
                            "state": transfer.state,
                            "custodian_id": custodian.id,
                        }
                    }

            # ---------- Version policy ----------
            latest_version = None
            min_supported  = None

            if mobile_app:
                # 1) Preferred: the explicit current_version_line_id
                line = mobile_app.current_version_line_id
                if line:
                    latest_version = line.version_code or mobile_app.current_version

                # 2) Else pick “running & is_current_version”
                if not latest_version and mobile_app.version_line_ids:
                    current_running = mobile_app.version_line_ids.filtered(
                        lambda l: l.is_current_version and l.status == 'running'
                    )[:1]
                    if current_running:
                        latest_version = current_running.version_code

                # 3) Else choose the highest running version
                if not latest_version and mobile_app.version_line_ids:
                    running = mobile_app.version_line_ids.filtered(lambda l: l.status == 'running')
                    if running:
                        latest_version = max(
                            running,
                            key=lambda r: self._split_version(r.version_code or '0')
                        ).version_code

                # Min supported (optional): the **lowest** running version
                if mobile_app.version_line_ids:
                    running = mobile_app.version_line_ids.filtered(lambda l: l.status == 'running')
                    if running:
                        min_supported = min(
                            running,
                            key=lambda r: self._split_version(r.version_code or '0')
                        ).version_code

            if not latest_version and mobile_app and mobile_app.current_version:
                latest_version = mobile_app.current_version

            # If a latest is defined, enforce: must be >= latest (hard policy as requested)
            if latest_version and self._is_version_older(app_version, latest_version):
                return {
                    "success": True,
                    "app_enabled": False,
                    "reason_code": "APP_UPDATE_REQUIRED",
                    "message": "A new version of the app is available. Please update to continue.",
                    "data": {
                        "update_customer_geo_location": update_customer_geo_location,
                        "allow_to_pay_in_multiple_ways": allow_to_pay_in_multiple_ways,
                        "allow_to_cancel_sale_order": allow_to_cancel_sale_order,
                        "your_version": app_version,
                        "latest_version": latest_version,
                        "min_supported": min_supported,
                        "update_required": True
                    }
                }

            # ---------- OK ----------
            return {
                "success": True,
                "app_enabled": True,
                "reason_code": "OK",
                "message": "Your app is enabled and up to date. You can continue.",
                "data": {
                    "update_customer_geo_location": update_customer_geo_location,
                    "allow_to_pay_in_multiple_ways": allow_to_pay_in_multiple_ways,
                    "allow_to_cancel_sale_order": allow_to_cancel_sale_order,
                    "your_version": app_version,
                    "latest_version": latest_version,
                    "min_supported": min_supported,
                    "custodian_id": custodian.id if custodian else None,
                    "user_type": user_type,
                }
            }

        except Exception as e:
            _logger.exception("Error in /api/v1/app_status")
            return {
                "success": False,
                "app_enabled": False,
                "reason_code": "SERVER_ERROR",
                "message": "Internal server error.",
                "message_details": str(e),
                "data": {}
            }