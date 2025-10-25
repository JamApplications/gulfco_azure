# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import io
import base64
from datetime import datetime, date, time, timedelta
from odoo.exceptions import ValidationError

try:
    import xlsxwriter
except Exception:
    from odoo.tools.misc import xlsxwriter

try:
    import pytz
except Exception:
    pytz = None
    from zoneinfo import ZoneInfo as _ZoneInfo  # Python 3.9+


def _json_to_text(val):
    if isinstance(val, dict):
        return (
            val.get('en_US') or val.get('en') or val.get('ar_001') or val.get('ar')
            or next((x for x in val.values() if isinstance(x, str) and x), '')
            or ''
        )
    return val


def _to_float(val, default=0.0):
    if isinstance(val, dict):
        val = _json_to_text(val)
    try:
        return float(val)
    except Exception:
        return float(default)


class RmaAnalysisExcelWizard(models.TransientModel):
    _name = 'rma.analysis.excel.wizard'
    _description = 'RMA Analysis Excel Wizard'

    date_from = fields.Date(string="RMA Start Date")
    date_to   = fields.Date(string="RMA End Date")

    receipt_date_from = fields.Date(string="Receipt Start Date")
    receipt_date_to   = fields.Date(string="Receipt End Date")

    file_data = fields.Binary(string="Excel File", readonly=True)
    file_name = fields.Char(string="Filename", readonly=True)

    @api.constrains('date_from', 'date_to', 'receipt_date_from', 'receipt_date_to')
    def _check_date_ranges(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_("RMA End Date cannot be earlier than RMA Start Date."))
            if rec.receipt_date_from and rec.receipt_date_to and rec.receipt_date_to < rec.receipt_date_from:
                raise ValidationError(_("Receipt End Date cannot be earlier than Receipt Start Date."))

    def _user_tz(self):
        tzname = (self.env.user.tz or 'UTC') if self.env.user else 'UTC'
        if pytz:
            return pytz.timezone(tzname), pytz.UTC
        else:
            return _ZoneInfo(tzname), _ZoneInfo('UTC')

    def _to_utc_from_user_midnight(self, d, add_days=0):
        if not d:
            return None
        loctz, utctz = self._user_tz()
        base_local = datetime.combine(d + timedelta(days=add_days), time.min)
        if pytz:
            aware_local = loctz.localize(base_local)
        else:
            aware_local = base_local.replace(tzinfo=loctz)
        aware_utc = aware_local.astimezone(utctz)
        return aware_utc.replace(tzinfo=None)  # Odoo/PG: naive as UTC

    def _excel_date_user_tz(self, v):
        if not v:
            return None
        loctz, utctz = self._user_tz()
        if isinstance(v, datetime):
            if pytz:
                aware_utc = utctz.localize(v)
            else:
                aware_utc = v.replace(tzinfo=utctz)
            local_dt = aware_utc.astimezone(loctz)
            return datetime(local_dt.year, local_dt.month, local_dt.day)
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day)
        return None

    def _dt_range(self, d_from, d_to):
        dt_from = self._to_utc_from_user_midnight(d_from, add_days=0) if d_from else None
        dt_to   = self._to_utc_from_user_midnight(d_to,   add_days=1) if d_to   else None
        return dt_from, dt_to

    def _get_effective_receipt_range(self):
        if self.receipt_date_from or self.receipt_date_to:
            return self._dt_range(self.receipt_date_from, self.receipt_date_to), 'receipt'
        return self._dt_range(self.date_from, self.date_to), 'legacy'

    def _fetch_rows(self, rec_dt_from, rec_dt_to):
        excluded_states = ('draft', 'cancel', 'cancelled')
        params = [excluded_states]
        where  = ["(r.state IS NULL OR r.state NOT IN %s)"]

        if rec_dt_from:
            where.append("spk.date_done >= %s")
            params.append(rec_dt_from)
        if rec_dt_to:
            where.append("spk.date_done < %s")
            params.append(rec_dt_to)

        where_sql = " AND ".join(where)

        query_full = f"""
            SELECT
                r.id                                           AS rma_id,
                l.line_id                                      AS line_id,
                spk.date_done::timestamp                       AS transaction_date, -- Receipt UTC (naive)
                r.date::timestamp                              AS rma_date,         -- RMA Date
                r.name                                         AS rma_number,

                l.product_id                                   AS product_id,
                pt.name                                        AS item_description,

                r.operation_id                                 AS operation_id,
                rop.name                                       AS operation_name,

                whpick.wh_id                                   AS warehouse_id,
                sw.name                                        AS warehouse_name,

                locpick.loc_id                                 AS locator_id,
                loc.complete_name                              AS locator_name,

                l.product_uom_id                               AS uom_id,
                uom.name                                       AS uom_name,
                l.product_uom_qty                              AS primary_quantity,
                l.quantity                                     AS quantity,

                r.currency_id                                  AS currency_id,
                l.price                                        AS price,
                l.total_rma_amount                             AS total_rma_amount,

                r.partner_id                                   AS customer_id,
                rp.name                                        AS customer_name,

                COALESCE(rp.customer_code, r.customer_account, '') AS customer_no,

                r.sales_person_id                              AS salesman_id,
                sp.name                                        AS salesman_name,

                r.rma_type                                     AS rma_type,
                rr.name                                        AS return_reason,
                rrt.name                                       AS return_reason_type_name,

                rm.picking_id                                  AS picking_id,
                r.state                                        AS rma_state
            FROM rma r
            LEFT JOIN (
                -- rma_line
                SELECT
                    rl.rma_id,
                    rl.id AS line_id,
                    rl.product_id,
                    rl.product_uom_id,
                    rl.product_uom_qty,
                    rl.product_uom_qty AS quantity,
                    COALESCE(rl.price_unit, 0.0) AS price,
                    ABS(COALESCE(rl.total, rl.price_unit * rl.product_uom_qty, 0.0)) AS total_rma_amount,
                    rl.return_reason_id
                FROM rma_line rl

                UNION ALL

                -- rma_product_line
                SELECT
                    rpl.rma_id,
                    rpl.id AS line_id,
                    rpl.product_id,
                    rpl.product_uom_id,
                    rpl.product_uom_qty,
                    rpl.product_uom_qty AS quantity,
                    COALESCE(rpl.price_unit, 0.0) AS price,
                    ABS(COALESCE(rpl.total, rpl.price_unit * rpl.product_uom_qty, 0.0)) AS total_rma_amount,
                    rpl.return_reason_id
                FROM rma_product_line rpl
            ) l ON l.rma_id = r.id

            LEFT JOIN rma_operation rop   ON rop.id = r.operation_id
            LEFT JOIN product_product pp  ON pp.id = l.product_id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN uom_uom uom         ON uom.id = l.product_uom_id
            LEFT JOIN res_partner rp      ON rp.id = r.partner_id
            LEFT JOIN res_partner sp      ON sp.id = r.sales_person_id
            LEFT JOIN rma_return_reason rr   ON rr.id = l.return_reason_id
            LEFT JOIN rma_return_reason_type rrt ON rrt.id = rr.type

            JOIN stock_move rm       ON rm.id = r.reception_move_id
            JOIN stock_picking spk   ON spk.id = rm.picking_id

            LEFT JOIN LATERAL (
                SELECT COALESCE(
                    rm.location_dest_id,
                    (
                        SELECT sml.location_dest_id
                        FROM stock_move_line sml
                        WHERE sml.move_id = rm.id
                          AND sml.location_dest_id IS NOT NULL
                        LIMIT 1
                    )
                ) AS loc_id
            ) AS locpick ON TRUE
            LEFT JOIN stock_location loc  ON loc.id = locpick.loc_id

            LEFT JOIN stock_picking_type spt ON spt.id = spk.picking_type_id

            LEFT JOIN LATERAL (
                SELECT COALESCE(spt.warehouse_id, swa.id) AS wh_id
                FROM (
                    WITH RECURSIVE loc_ancestors(id) AS (
                        SELECT locpick.loc_id
                        UNION ALL
                        SELECT sl.location_id
                        FROM stock_location sl
                        JOIN loc_ancestors la ON sl.id = la.id
                        WHERE sl.location_id IS NOT NULL
                    )
                    SELECT sw.id
                    FROM stock_warehouse sw
                    JOIN loc_ancestors la ON la.id = sw.view_location_id
                    LIMIT 1
                ) AS swa
            ) AS whpick ON TRUE
            LEFT JOIN stock_warehouse sw  ON sw.id = whpick.wh_id

            WHERE {where_sql}
            ORDER BY spk.date_done ASC, COALESCE(l.line_id, r.id) ASC
        """

        try:
            self.env.cr.execute(query_full, params)
        except Exception:
            query_fallback = f"""
                SELECT
                    r.id AS rma_id,
                    l.line_id AS line_id,
                    spk.date_done::timestamp AS transaction_date,
                    r.date::timestamp AS rma_date,
                    r.name AS rma_number,

                    l.product_id AS product_id,
                    pt.name AS item_description,

                    r.operation_id AS operation_id,
                    rop.name AS operation_name,

                    whpick.wh_id AS warehouse_id,
                    sw.name AS warehouse_name,

                    locpick.loc_id AS locator_id,
                    loc.complete_name AS locator_name,

                    l.product_uom_id AS uom_id,
                    uom.name AS uom_name,
                    l.product_uom_qty AS primary_quantity,
                    l.product_uom_qty AS quantity,

                    r.currency_id AS currency_id,
                    NULL::numeric AS price,
                    NULL::numeric AS total_rma_amount,

                    r.partner_id AS customer_id,
                    rp.name AS customer_name,
                    COALESCE(rp.customer_code, r.customer_account, '') AS customer_no,

                    r.sales_person_id AS salesman_id,
                    sp.name AS salesman_name,

                    r.rma_type AS rma_type,
                    NULL::text AS return_reason,
                    NULL::text AS return_reason_type_name,

                    rm.picking_id AS picking_id,
                    r.state AS rma_state
                FROM rma r
                LEFT JOIN (
                    SELECT rl.rma_id, rl.id AS line_id, rl.product_id, rl.product_uom_id, rl.product_uom_qty
                    FROM rma_line rl
                    UNION ALL
                    SELECT rpl.rma_id, rpl.id AS line_id, rpl.product_id, rpl.product_uom_id, rpl.product_uom_qty
                    FROM rma_product_line rpl
                ) l ON l.rma_id = r.id

                LEFT JOIN rma_operation rop   ON rop.id = r.operation_id
                LEFT JOIN product_product pp  ON pp.id = l.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN uom_uom uom         ON uom.id = l.product_uom_id
                LEFT JOIN res_partner rp      ON rp.id = r.partner_id
                LEFT JOIN res_partner sp      ON sp.id = r.sales_person_id

                JOIN stock_move rm       ON rm.id = r.reception_move_id
                JOIN stock_picking spk   ON spk.id = rm.picking_id

                LEFT JOIN LATERAL (
                    SELECT COALESCE(
                        rm.location_dest_id,
                        (
                            SELECT sml.location_dest_id
                            FROM stock_move_line sml
                            WHERE sml.move_id = rm.id
                              AND sml.location_dest_id IS NOT NULL
                            LIMIT 1
                        )
                    ) AS loc_id
                ) AS locpick ON TRUE
                LEFT JOIN stock_location loc  ON loc.id = locpick.loc_id

                LEFT JOIN stock_picking_type spt ON spt.id = spk.picking_type_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(spt.warehouse_id, swa.id) AS wh_id
                    FROM (
                        WITH RECURSIVE loc_ancestors(id) AS (
                            SELECT locpick.loc_id
                            UNION ALL
                            SELECT sl.location_id
                            FROM stock_location sl
                            JOIN loc_ancestors la ON sl.id = la.id
                            WHERE sl.location_id IS NOT NULL
                        )
                        SELECT sw.id
                        FROM stock_warehouse sw
                        JOIN loc_ancestors la ON la.id = sw.view_location_id
                        LIMIT 1
                    ) AS swa
                ) AS whpick ON TRUE
                LEFT JOIN stock_warehouse sw  ON sw.id = whpick.wh_id

                WHERE {where_sql}
                ORDER BY spk.date_done ASC, COALESCE(l.line_id, r.id) ASC
            """
            self.env.cr.execute(query_fallback, params)

        return self.env.cr.dictfetchall()

    def _fetch_lot_pool(self, rma_ids, product_ids):
        if not rma_ids or not product_ids:
            return {}

        query = """
            WITH rx AS (
                SELECT r.id AS rma_id, spk.id AS picking_id
                FROM rma r
                JOIN stock_move rm     ON rm.id = r.reception_move_id
                JOIN stock_picking spk ON spk.id = rm.picking_id
                WHERE r.id = ANY(%s)
            ),
            lot_agg AS (
                SELECT
                    rx.rma_id,
                    sm.product_id,
                    lot.name            AS lot_serial,
                    sml.production_date AS prod_dt,
                    sml.expiration_date AS exp_dt,
                    SUM(sml.quantity)   AS lot_qty
                FROM rx
                JOIN stock_move sm       ON sm.picking_id = rx.picking_id
                JOIN stock_move_line sml ON sml.move_id = sm.id
                LEFT JOIN stock_lot lot  ON lot.id = sml.lot_id
                WHERE sm.product_id = ANY(%s) AND sml.lot_id IS NOT NULL
                GROUP BY rx.rma_id, sm.product_id, lot.name, sml.production_date, sml.expiration_date
            )
            SELECT * FROM lot_agg
        """
        self.env.cr.execute(query, (list(set(rma_ids)), list(set(product_ids))))
        data = self.env.cr.dictfetchall()

        pool = {}
        for r in data:
            key = (r['rma_id'], r['product_id'])
            bucket = pool.setdefault(key, [])
            bucket.append({
                'lot': (r.get('lot_serial') or '').strip(),
                'prod': r.get('prod_dt'),
                'exp': r.get('exp_dt'),
                'qty': float(r.get('lot_qty') or 0.0),
            })

        for key in list(pool.keys()):
            pool[key].sort(key=lambda x: (-(x['qty']), x['lot']))
        return pool

    def _assign_lot_for_line(self, pool_list, line_qty):
        if not pool_list or not line_qty or line_qty <= 0:
            return '', None, None

        for i, lot in enumerate(pool_list):
            if abs(lot['qty'] - line_qty) < 1e-6:
                chosen = pool_list.pop(i)
                return chosen['lot'], chosen['prod'], chosen['exp']

        best_idx = -1
        best_diff = None
        for i, lot in enumerate(pool_list):
            diff = abs(lot['qty'] - line_qty)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_idx = i

        if best_idx == -1:
            return '', None, None

        chosen = pool_list[best_idx]
        chosen['qty'] -= line_qty
        if chosen['qty'] <= 1e-6:
            pool_list.pop(best_idx)
        return chosen['lot'], chosen['prod'], chosen['exp']

    def action_export_excel(self):
        self.ensure_one()

        (rec_dt_from, rec_dt_to), range_source = self._get_effective_receipt_range()
        rows = self._fetch_rows(rec_dt_from, rec_dt_to)

        rma_ids     = [r['rma_id'] for r in rows if r.get('rma_id')]
        product_ids = [r['product_id'] for r in rows if r.get('product_id')]
        picking_ids = [r['picking_id'] for r in rows if r.get('picking_id')]

        lot_pool = self._fetch_lot_pool(rma_ids, product_ids) if rows else {}
        cost_map = self._fetch_cost_agg(picking_ids, product_ids) if rows else {}
        qty_map  = self._fetch_qty_agg(picking_ids, product_ids) if rows else {}

        state_map, rma_type_map = {}, {}
        try:
            fld = self.env['rma']._fields.get('state')
            if fld and fld.selection:
                sel = fld.selection(self.env['rma']) if callable(fld.selection) else fld.selection
                state_map = {k: _json_to_text(v) if isinstance(v, dict) else v for k, v in sel}
        except Exception:
            pass
        try:
            fld = self.env['rma']._fields.get('rma_type')
            if fld and fld.selection:
                sel = fld.selection(self.env['rma']) if callable(fld.selection) else fld.selection
                rma_type_map = {k: _json_to_text(v) if isinstance(v, dict) else v for k, v in sel}
        except Exception:
            pass

        pt_division_field = self.env['product.template']._fields.get('division')
        division_field_type = getattr(pt_division_field, 'type', None) if pt_division_field else None
        division_label_map = {}
        if pt_division_field and getattr(pt_division_field, 'selection', None):
            sel = pt_division_field.selection(self.env['product.template']) if callable(pt_division_field.selection) else pt_division_field.selection
            division_label_map = {k: _json_to_text(v) if isinstance(v, dict) else v for k, v in sel}

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'constant_memory': True})
        ws = workbook.add_worksheet('RMA Analysis')

        fmt_hdr  = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        fmt_txt  = workbook.add_format({'border': 1})
        fmt_num  = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        fmt_date = workbook.add_format({'border': 1, 'num_format': 'd/m/yyyy'})

        headers = [
            'RMA Date', 'Receipt Date', 'Item','Transaction Type Name',
            'Warehouse','Locator','RMA Number',
            'Primary Uom Code','Primary Quantity','Division',
            'RMA Type','Return Reason','Type',
            'Price','Lot Serial Number','Production Date','Expiry Date',
            'Customer No','Customer Name','Channel',
            'Salesman','Brand','Product Category','Total RMA Amount',
            'Total Cost','RMA Status'
        ]
        for c, h in enumerate(headers):
            ws.write(0, c, h, fmt_hdr)

        r_idx = 1
        Product = self.env['product.product']
        Rma     = self.env['rma']
        Partner = self.env['res.partner']

        working_pool = {k: [dict(x) for x in v] for k, v in lot_pool.items()}

        for r in rows:
            dt = r.get('transaction_date')   # Receipt Date (UTC-naive)
            rma_dt = r.get('rma_date')       # RMA Date

            key = (r.get('rma_id'), r.get('product_id'))
            line_qty = _to_float(r.get('primary_quantity'))
            lot_name, prod_dt, exp_dt = self._assign_lot_for_line(working_pool.get(key, []), line_qty)

            brand_name = ''
            category_name = ''
            division_disp = ''
            uom_name = _json_to_text(r.get('uom_name') or '')
            item_name = ''
            if r.get('product_id'):
                prod = Product.browse(r['product_id'])
                item_name = prod.display_name or ''
                tmpl = prod.product_tmpl_id
                category_name = (tmpl.categ_id.display_name or '') if tmpl.categ_id else ''
                if pt_division_field:
                    if division_field_type == 'many2one':
                        division_disp = tmpl.division.display_name if getattr(tmpl, 'division', False) else ''
                    elif division_field_type == 'selection':
                        raw_div = getattr(tmpl, 'division', '') or ''
                        division_disp = division_label_map.get(raw_div, raw_div)
                    else:
                        division_disp = getattr(tmpl, 'division', '') or ''
                brand = getattr(tmpl, 'brand_id', False)
                brand_name = brand.name if brand else ''

            op_name   = _json_to_text(r.get('operation_name') or '')
            wh_name   = _json_to_text(r.get('warehouse_name') or '')
            loc_name  = _json_to_text(r.get('locator_name') or '')
            if r.get('customer_id'):
                cust_rec = Partner.browse(r['customer_id'])
                cust_name = cust_rec.display_name or _json_to_text(r.get('customer_name') or '')
            else:
                cust_name = _json_to_text(r.get('customer_name') or '')

            sales_name  = _json_to_text(r.get('salesman_name') or '')
            rma_state   = state_map.get(r.get('rma_state'), r.get('rma_state') or '')
            reason_type = _json_to_text(r.get('return_reason_type_name') or '')
            rma_type_label = rma_type_map.get(r.get('rma_type'), _json_to_text(r.get('rma_type') or ''))

            rma_rec = Rma.browse(r.get('rma_id')) if r.get('rma_id') else False
            channel_name = rma_rec.partner_channel_id.display_name if (rma_rec and rma_rec.partner_channel_id) else ''

            overall_cost = float(cost_map.get((r.get('picking_id'), r.get('product_id')), 0.0) or 0.0)
            overall_qty  = float(qty_map.get((r.get('picking_id'), r.get('product_id')), 0.0) or 0.0)
            unit_cost = (overall_cost / overall_qty) if overall_qty else 0.0
            line_primary_qty = _to_float(r.get('primary_quantity'))
            line_cost = unit_cost * line_primary_qty

            values = [
                rma_dt,              # 0: RMA Date (Date)
                dt,                  # 1: Receipt Date (UTC-naive)
                item_name,           # 2
                op_name,             # 3
                wh_name,             # 4  <-- من الاستلام فقط
                loc_name,            # 5  <-- من الاستلام فقط
                (r.get('rma_number') or ''),  # 6
                uom_name,            # 7
                line_primary_qty,    # 8
                division_disp,       # 9
                rma_type_label,      # 10
                _json_to_text(r.get('return_reason') or ''),  # 11
                reason_type,         # 12
                _to_float(r.get('price')),   # 13
                lot_name,            # 14
                prod_dt,             # 15
                exp_dt,              # 16
                _json_to_text(r.get('customer_no') or ''),     # 17
                cust_name,           # 18
                channel_name,        # 19
                sales_name,          # 20
                brand_name,          # 21
                category_name,       # 22
                _to_float(r.get('total_rma_amount')),  # 23
                _to_float(line_cost),                  # 24
                rma_state,           # 25
            ]

            for c, v in enumerate(values):
                if c in (0, 1, 15, 16):  # dates
                    dv = self._excel_date_user_tz(v)
                    if dv:
                        ws.write_datetime(r_idx, c, dv, fmt_date)
                    else:
                        ws.write(r_idx, c, _json_to_text(v) if isinstance(v, dict) else v, fmt_txt)
                elif c in (8, 13, 23, 24) and v != '':
                    ws.write_number(r_idx, c, _to_float(v), fmt_num)
                else:
                    ws.write(r_idx, c, _json_to_text(v) if isinstance(v, dict) else v, fmt_txt)

            r_idx += 1

        for col in range(len(headers)):
            ws.set_column(col, col, 18)

        workbook.close()
        buffer.seek(0)
        data = buffer.read()
        buffer.close()

        fname = "RMA_Analysis"
        use_from = self.receipt_date_from or self.date_from
        use_to   = self.receipt_date_to   or self.date_to
        if use_from or use_to:
            parts = []
            if use_from:
                parts.append(use_from.strftime('%Y%m%d'))
            if use_to:
                parts.append(use_to.strftime('%Y%m%d'))
            suffix = "_".join(parts)
            if suffix:
                fname = f"RMA_Analysis_{suffix}"

        self.write({'file_data': base64.b64encode(data), 'file_name': f"{fname}.xlsx"})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rma.analysis.excel.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _fetch_cost_agg(self, picking_ids, product_ids):
        if not picking_ids or not product_ids:
            return {}
        query = """
            SELECT
                sm.picking_id,
                sm.product_id,
                ABS(COALESCE(SUM(svl.value), 0.0)) AS total_cost
            FROM stock_valuation_layer svl
            JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE sm.picking_id = ANY(%s) AND sm.product_id = ANY(%s)
            GROUP BY sm.picking_id, sm.product_id
        """
        self.env.cr.execute(query, (picking_ids, product_ids))
        data = self.env.cr.dictfetchall()
        return {(r['picking_id'], r['product_id']): float(r['total_cost'] or 0.0) for r in data}

    def _fetch_qty_agg(self, picking_ids, product_ids):
        if not picking_ids or not product_ids:
            return {}
        query = """
            SELECT
                sm.picking_id,
                sm.product_id,
                COALESCE(SUM(sml.quantity), 0.0) AS total_qty
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id
            WHERE sm.picking_id = ANY(%s) AND sm.product_id = ANY(%s)
            GROUP BY sm.picking_id, sm.product_id
        """
        self.env.cr.execute(query, (picking_ids, product_ids))
        data = self.env.cr.dictfetchall()
        return {(r['picking_id'], r['product_id']): float(r['total_qty'] or 0.0) for r in data}
