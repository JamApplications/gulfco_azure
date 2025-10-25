# controllers/partner_api.py
from odoo import http
from odoo.http import request


class PartnerApiController(http.Controller):

    @http.route('/api/v1/update_customer_location', type='json', auth='none', methods=['POST'], csrf=False)
    def update_customer_location(self, **kwargs):
        """
        Payload (min):
        {
            "user_id": 123,
            "auth_token": "abc123",
            "partner_id": 456,
            "partner_latitude": 25.1972,     // or "latitude", or "lat"
            "partner_longitude": 55.2744,    // or "longitude", or "lng" / "lon"

            // optional "other data" (whitelisted below)
            "name": "New Name",
            "phone": "+9715...",
            "mobile": "+9715...",
            "email": "x@y.com",
            "street": "Sheikh Zayed Rd",
            "street2": "Office 1201",
            "city": "Dubai",
            "zip": "00000",
            "website": "https://example.com",
            "vat": "AE123456",
            "customer_rank": 1,
            "supplier_rank": 0,
            "country_id": 229,       // M2O id
            "state_id":  123,        // M2O id
            "category_ids": [10, 11] // M2M ids (will replace)
        }
        """
        values = request.httprequest.json or {}
        try:
            # --- Auth basics ---
            user_id = values.get('user_id')
            auth_token = values.get('auth_token')
            if not user_id or not auth_token:
                return {'success': False, 'error_msg': 'Missing required parameters: user_id, auth_token.'}

            token = request.env['mobile.auth.token'].sudo().search([
                ('user_id', '=', user_id),
                ('mobile_app_auth_token', '=', auth_token)
            ], limit=1)
            if not token:
                return {'success': False, 'error_msg': 'Invalid or expired auth token.'}

            # --- Target partner ---
            partner_id = values.get('partner_id') or values.get('customer_id') or values.get('id')
            if not partner_id:
                return {'success': False, 'error_msg': 'Missing partner_id.'}

            partner = request.env['res.partner'].sudo().browse(int(partner_id))
            if not partner.exists():
                return {'success': False, 'error_msg': 'Partner not found.'}

            # --- Helpers ---
            def _to_float(v):
                try:
                    fv = float(v)
                    if fv != fv:  # NaN check
                        return None
                    return fv
                except Exception:
                    return None

            def _field_exists(name):
                return name in partner._fields

            # --- Parse lat/lon from any common key ---
            lat_raw = (
                values.get('partner_latitude', None) if 'partner_latitude' in values else
                values.get('latitude', None) if 'latitude' in values else
                values.get('lat', None)
            )
            lon_raw = (
                values.get('partner_longitude', None) if 'partner_longitude' in values else
                values.get('longitude', None) if 'longitude' in values else
                values.get('lng', None) if 'lng' in values else
                values.get('lon', None)
            )

            updates = {}

            # --- Validate & assign latitude ---
            if lat_raw is not None:
                lat = _to_float(lat_raw)
                if lat is None or lat < -90.0 or lat > 90.0:
                    return {'success': False, 'error_msg': 'Latitude must be a number between -90 and 90.'}
                if _field_exists('partner_latitude'):
                    updates['partner_latitude'] = lat
                if _field_exists('latitude'):
                    updates['latitude'] = lat  # for dbs that also have a 'latitude' field

            # --- Validate & assign longitude ---
            if lon_raw is not None:
                lon = _to_float(lon_raw)
                if lon is None or lon < -180.0 or lon > 180.0:
                    return {'success': False, 'error_msg': 'Longitude must be a number between -180 and 180.'}
                if _field_exists('partner_longitude'):
                    updates['partner_longitude'] = lon
                if _field_exists('longitude'):
                    updates['longitude'] = lon  # for dbs that also have a 'longitude' field

            # --- Whitelist for "other data" (simple fields) ---
            # SIMPLE_FIELDS = [
            #     'name', 'phone', 'mobile', 'email', 'street', 'street2',
            #     'city', 'zip', 'website', 'vat', 'customer_rank', 'supplier_rank'
            # ]
            # for f in SIMPLE_FIELDS:
            #     if f in values and _field_exists(f):
            #         updates[f] = values[f]

            # --- M2O fields (ids) ---
            # if 'country_id' in values and _field_exists('country_id'):
            #     updates['country_id'] = int(values['country_id']) if values['country_id'] else False
            # if 'state_id' in values and _field_exists('state_id'):
            #     updates['state_id'] = int(values['state_id']) if values['state_id'] else False

            # --- M2M Category (replaces all) ---
            # if 'category_ids' in values and isinstance(values['category_ids'], list) and _field_exists('category_id'):
            #     cat_ids = [int(i) for i in values['category_ids']]
            #     updates['category_id'] = [(6, 0, cat_ids)]

            if not updates:
                return {'success': False, 'error_msg': 'No valid fields to update were provided.'}

            partner.write(updates)

            # Build response safely (only if fields exist)
            def _safe_val(field):
                return getattr(partner, field) if _field_exists(field) else None

            return {
                'success': True,
                'partner': {
                    'id': partner.id,
                    'name': partner.name,
                    'partner_latitude': _safe_val('partner_latitude'),
                    'partner_longitude': _safe_val('partner_longitude'),
                    'latitude': _safe_val('latitude'),
                    'longitude': _safe_val('longitude'),
                    'write_date': str(partner.write_date),
                }
            }

        except Exception as e:
            request.env.cr.rollback()
            return {'success': False, 'error_msg': str(e)}
