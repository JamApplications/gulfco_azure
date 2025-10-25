
# from odoo import models, fields, api
# import base64, os, tempfile
# import xlsxwriter
# from odoo.exceptions import ValidationError
# from datetime import datetime, time, date
# from decimal import Decimal
# import time as pytime


# class SalesOrderRmaReportDelivery(models.TransientModel):
#     _name = 'sales.order.rma.report.delivery'
#     _description = 'Sales Order Rma Report Wizard Delivery'

#     date_from = fields.Date(string="Sales Order Start Date")
#     date_to = fields.Date(string="Sales Order End Date")
#     file_data = fields.Binary(string="Report File", readonly=True)
#     file_name = fields.Char(string="File Name")

#     show_invoice_dates = fields.Boolean(string="Filter by Sales Order Date")

#     invoice_date_from = fields.Datetime(string="Invoice Start Date")
#     invoice_date_to = fields.Datetime(string="Invoice End Date")
#     refund_id = fields.Many2one('account.move', string="Refund Invoice")

#     @api.constrains('date_from', 'date_to')
#     def _check_dates(self):
#         for record in self:
#             if record.date_from and record.date_to and record.date_to < record.date_from:
#                 raise ValidationError("End Date cannot be before Start Date.")

#     @api.constrains('invoice_date_from', 'invoice_date_to')
#     def _check_invoice_dates(self):
#         for record in self:
#             if record.invoice_date_from and record.invoice_date_to and record.invoice_date_to < record.invoice_date_from:
#                 raise ValidationError("Invoice End Date cannot be before Invoice Start Date.")

#     def generate_report(self):
#         # ===== إعدادات الأداء =====
#         FETCH_BATCH = 5000
#         READ_CHUNK = 5000
#         self.env.cr.itersize = 10000

#         # تهيئة جلسة Postgres للاستعلامات الثقيلة
#         try:
#             self.env.cr.execute("SET LOCAL work_mem = %s", ('256MB',))
#             self.env.cr.execute("SET LOCAL jit = off")
#         except Exception:
#             pass

#         def dictfetchmany(cr, size):
#             cols = [d[0] for d in cr.description]
#             while True:
#                 rows = cr.fetchmany(size)
#                 if not rows:
#                     break
#                 for r in rows:
#                     yield dict(zip(cols, r))

#         def _xlsx_cell(v):
#             if v is None:
#                 return ''
#             if isinstance(v, Decimal):
#                 return float(v)
#             if isinstance(v, (int, float)):
#                 return v
#             if isinstance(v, (datetime, date)):
#                 return v.strftime('%Y-%m-%d')
#             if isinstance(v, (list, tuple)):
#                 if len(v) >= 2 and isinstance(v[1], (str, int, float)):
#                     return v[1]
#                 return ' | '.join(str(_xlsx_cell(x)) for x in v)
#             if isinstance(v, dict):  # JSONB/ترجمات
#                 if v.get('en_US'):
#                     return v['en_US']
#                 for k in ('name', 'display_name', 'label'):
#                     if v.get(k):
#                         return v[k]
#                 if v:
#                     return str(next(iter(v.values())))
#                 return ''
#             if isinstance(v, (bytes, bytearray)):
#                 try:
#                     return v.decode('utf-8', 'ignore')
#                 except Exception:
#                     return str(v)
#             return str(v)

#         def _sanitize_cell(v):
#             if v is None:
#                 return ''
#             if isinstance(v, (str, int, float)):
#                 return v
#             if isinstance(v, (datetime, date)):
#                 return v.strftime('%Y-%m-%d')
#             if isinstance(v, Decimal):
#                 return float(v)
#             if isinstance(v, (dict, list, tuple, bytes, bytearray)):
#                 return _xlsx_cell(v)
#             return str(v)

#         def _sanitize_row(row_vals):
#             return [_sanitize_cell(x) for x in row_vals]

#         safe_json = _xlsx_cell

#         # ===== ربط سطر الفاتورة بسطر SO عبر الجدول الوسيط =====
#         m2m = self.env['account.move.line']._fields['sale_line_ids']
#         rel_table = m2m.relation
#         col_aml   = m2m.column1
#         col_sol   = m2m.column2

#         # ===== IDs لقراءة Ship to Site عبر ORM =====
#         so_filters = ["so.state IN ('sale','done')"]
#         so_params = []
#         invoice_date_subfilter = ""
#         if self.show_invoice_dates:
#             if self.date_from:
#                 so_filters.append("so.date_order >= %s")
#                 so_params.append(datetime.combine(self.date_from, time.min))
#             if self.date_to:
#                 so_filters.append("so.date_order <= %s")
#                 so_params.append(datetime.combine(self.date_to, time.max))
#         else:
#             if self.invoice_date_from or self.invoice_date_to:
#                 invoice_date_subfilter = f"""
#                     AND EXISTS (
#                         SELECT 1
#                         FROM sale_order_line sol2
#                         JOIN {rel_table} rel2 ON rel2.{col_sol} = sol2.id
#                         JOIN account_move_line aml2 ON aml2.id = rel2.{col_aml}
#                         JOIN account_move am2 ON am2.id = aml2.move_id
#                         WHERE sol2.order_id = so.id
#                           AND am2.move_type = 'out_invoice'
#                           AND am2.state = 'posted'
#                           {"AND am2.invoice_date >= %s" if self.invoice_date_from else ""}
#                           {"AND am2.invoice_date <= %s" if self.invoice_date_to else ""}
#                     )
#                 """
#                 if self.invoice_date_from:
#                     so_params.append(datetime.combine(self.invoice_date_from, time.min))
#                 if self.invoice_date_to:
#                     so_params.append(datetime.combine(self.invoice_date_to, time.max))

#         ids_sql = f"""
#             SELECT so.id
#             FROM sale_order so
#             WHERE {" AND ".join(so_filters)}
#             {invoice_date_subfilter}
#             ORDER BY so.date_order, so.id
#         """
#         self.env.cr.execute(ids_sql, tuple(so_params))
#         all_so_ids = [r[0] for r in self.env.cr.fetchall()]

#         site_map = {}
#         if all_so_ids:
#             for i in range(0, len(all_so_ids), READ_CHUNK):
#                 chunk_ids = all_so_ids[i:i+READ_CHUNK]
#                 for rec in self.env['sale.order'].browse(chunk_ids).exists().read(['x_studio_site_']):
#                     site_map[rec['id']] = rec.get('x_studio_site_')

#         # ===== تجهيز JOINs لأسماء العلاقات =====
#         resolve_fields = [
#             ('partner_channel_id',      'channel_name'),
#             ('outlet_id',               'outlet_class_name'),
#             ('sub_outlet_id',           'sub_class_name'),
#             ('customer_subdivision_id', 'sub_channel_name'),
#         ]
#         FIELD_LABEL_COL_OVERRIDES = {
#             'partner_channel_id': 'channel_name',
#             'customer_subdivision_id': 'name',
#             'outlet_id': 'outlet_name',
#             'sub_outlet_id': 'name',
#         }

#         partner_name_cols = []
#         partner_name_joins = []
#         for field, label in resolve_fields:
#             fld = self.env['res.partner']._fields.get(field)
#             if fld and getattr(fld, 'comodel_name', None):
#                 model = self.env[fld.comodel_name]
#                 table = model._table
#                 alias = f"rp_{field}"

#                 chosen = FIELD_LABEL_COL_OVERRIDES.get(field)
#                 if chosen:
#                     fdef = model._fields.get(chosen)
#                     if not (fdef and getattr(fdef, 'store', False)):
#                         chosen = None

#                 if not chosen:
#                     candidates = []
#                     rec_name = (getattr(model, '_rec_name', None) or 'name')
#                     candidates.append(rec_name)
#                     candidates += ['name', 'complete_name', 'code', 'ref', 'title', 'short_name', 'x_name']
#                     for c in candidates:
#                         fdef = model._fields.get(c)
#                         if fdef and getattr(fdef, 'store', False):
#                             chosen = c
#                             break

#                 if chosen:
#                     partner_name_joins.append(f"LEFT JOIN {table} {alias} ON {alias}.id = p.{field}")
#                     partner_name_cols.append(f"{alias}.{chosen} AS {label}")
#                 else:
#                     partner_name_cols.append(f"CAST(p.{field} AS varchar) AS {label}")
#             else:
#                 partner_name_cols.append(f"CAST(p.{field} AS varchar) AS {label}")

#         partner_name_cols_sql = ",\n                " + ",\n                ".join(partner_name_cols) if partner_name_cols else ""
#         partner_name_joins_sql = ("\n            " + "\n            ".join(partner_name_joins) + "\n") if partner_name_joins else "\n"

#         # ===== ملف الإكسل =====
#         fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
#         os.close(fd)
#         workbook = xlsxwriter.Workbook(tmp_path, {'constant_memory': True})
#         sheet = workbook.add_worksheet("Sales Orders & Credit Notes")

#         header_format = workbook.add_format({'bold': True,'bg_color': '#D3D3D3','border': 1,'align': 'center','valign': 'vcenter'})
#         period_format = workbook.add_format({'bold': True,'font_size': 14,'align': 'center','valign': 'vcenter','bg_color': '#5B9BD5','font_color': 'white'})

#         headers = ['Day','Order Number','Customer','Customer Code','Channel','Outlet Classification',
#                    'Sub Classification','Customer Type','Customer Group','Customer Outlet Code','Delivery Address','Sub Channel',
#                    'External Reference','Ship to Site','Customer Po Reference','Salesman','Order Date','Product','Internal Reference','Category',
#                    'Brand','Product Division','SO_Product Packaging','SO_Packaging Quantity',
#                    'SO_Product Packaging Price','INV_Product Packaging','INV_Packaging Quantity',
#                    'INV_Product Packaging Price','SO_Unit Qty','INV_Unit Qty','SO_Unit Price','INV_Unit Price',
#                    'SO_Delivered Qty','Invoiced Qty','Cost','Excise Tax','INV_Discount(%)','INV_Discount Amount',
#                    'INV_Gross Amount','SO_Total Before Vat(TAX)','SO_VAT(TAX) Amount','SO_Total after VAT(TAX)',
#                    'INV_Total Before Vat(TAX)','INV_VAT(TAX) Amount','INV_Total after VAT(TAX)',
#                    'Sales Order Status','Delivery Status','Delivery Number','Delivery Date','Invoice Status','Invoice Number','Invoice Dates',
#                    'Journal Name','Invoice State','Payment Status','Return Reason','RMA Status']
#         for i, h in enumerate(headers):
#             sheet.write(0, i, h, header_format)

#         row = 1
#         inv_status_selection = dict(self.env['sale.order']._fields['invoice_status'].selection)
#         payment_state_selection = dict(self.env['account.move']._fields['payment_state'].selection)

#         # ===== قسم أوامر البيع =====
#         so_wheres = ["so.state IN ('sale','done')"]
#         so_where_params = []
#         if self.show_invoice_dates:
#             if self.date_from:
#                 so_wheres.append("so.date_order >= %s")
#                 so_where_params.append(datetime.combine(self.date_from, time.min))
#             if self.date_to:
#                 so_wheres.append("so.date_order <= %s")
#                 so_where_params.append(datetime.combine(self.date_to, time.max))

#         invoice_date_subfilter = ""
#         exists_params = []
#         if (not self.show_invoice_dates) and (self.invoice_date_from or self.invoice_date_to):
#             invoice_date_subfilter = f"""
#                 AND EXISTS (
#                     SELECT 1
#                     FROM sale_order_line sol2
#                     JOIN {rel_table} rel2 ON rel2.{col_sol} = sol2.id
#                     JOIN account_move_line aml2 ON aml2.id = rel2.{col_aml}
#                     JOIN account_move am2 ON am2.id = aml2.move_id
#                     WHERE sol2.order_id = so.id
#                       AND am2.move_type = 'out_invoice'
#                       AND am2.state = 'posted'
#                       {"AND am2.invoice_date >= %s" if self.invoice_date_from else ""}
#                       {"AND am2.invoice_date <= %s" if self.invoice_date_to else ""}
#                 )
#             """
#             if self.invoice_date_from:
#                 exists_params.append(datetime.combine(self.invoice_date_from, time.min))
#             if self.invoice_date_to:
#                 exists_params.append(datetime.combine(self.invoice_date_to, time.max))

#         inv_join_date_filter = ""
#         inv_join_params = []
#         if self.invoice_date_from:
#             inv_join_date_filter += " AND am.invoice_date >= %s"
#             inv_join_params.append(datetime.combine(self.invoice_date_from, time.min))
#         if self.invoice_date_to:
#             inv_join_date_filter += " AND am.invoice_date <= %s"
#             inv_join_params.append(datetime.combine(self.invoice_date_to, time.max))

#         so_sql_stream = f"""
#             WITH so_filtered AS (
#                 SELECT
#                     so.id, so.name, so.state, so.invoice_status, so.date_order,
#                     so.partner_id, so.partner_shipping_id, so.po_number,
#                     so.assign_to AS so_assign_to
#                 FROM sale_order so
#                 WHERE {' AND '.join(so_wheres)}
#                 {invoice_date_subfilter}
#             ),
#             pick_agg AS (
#                 SELECT
#                     sof.id AS so_id,
#                     COUNT(sp.id) AS total_picks,
#                     SUM(CASE WHEN sp.state='done' THEN 1 ELSE 0 END) AS done_picks
#                 FROM so_filtered sof
#                 LEFT JOIN stock_picking sp ON sp.sale_id = sof.id
#                 LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
#                 WHERE spt.code = 'outgoing'     -- فقط Outbound
#                 GROUP BY sof.id
#             )
#             SELECT
#                 -- SO
#                 sof.id               AS so_id,
#                 sof.name             AS so_name,
#                 sof.state            AS so_state,
#                 sof.invoice_status   AS so_invoice_status,
#                 sof.date_order       AS so_date_order,
#                 sof.partner_id       AS partner_id,
#                 sof.partner_shipping_id AS ship_partner_id,
#                 sof.po_number        AS so_po,
#                 sof.so_assign_to     AS so_assign_to,

#                 -- SO Line
#                 sol.id              AS sol_id,
#                 sol.product_id      AS product_id,
#                 sol.product_uom_qty AS so_unit_qty,
#                 sol.price_unit      AS so_unit_price,
#                 sol.discount        AS so_discount,
#                 sol.qty_delivered   AS so_qty_delivered,
#                 sol.qty_invoiced    AS so_qty_invoiced,
#                 sol.purchase_price  AS so_purchase_price,
#                 sol.exercise_price  AS so_exercise_price,
#                 sol.product_packaging_id   AS so_packaging_id,
#                 sol.product_packaging_qty  AS so_packaging_qty,
#                 sol.product_packaging_price AS so_packaging_price,
#                 sol.price_subtotal  AS so_price_subtotal,
#                 sol.price_total     AS so_price_total,

#                 -- منتج الفاتورة (أولوية) ثم منتج SO
#                 COALESCE(pt_inv.name, pt.name)                               AS product_name,
#                 COALESCE(pp_inv.default_code, pp.default_code)               AS default_code,
#                 pc.complete_name                                             AS category_name,
#                 pb.name                                                      AS brand_name,
#                 pt.division                                                  AS division,

#                 -- حالة التوصيل
#                 CASE
#                   WHEN pick_agg.total_picks IS NULL THEN 'Pending'
#                   WHEN pick_agg.total_picks = pick_agg.done_picks AND pick_agg.total_picks > 0 THEN 'Delivered'
#                   ELSE 'Pending'
#                 END AS delivery_status,

#                 -- رقم وتاريخ الحركة الفعلية (Outgoing) لسطر الـ SO
#                 sp_so.name AS so_delivery_number,
#                 (SELECT MAX(sml.date)
#                    FROM stock_move_line sml
#                    JOIN stock_move sm2 ON sm2.id = sml.move_id
#                   WHERE sml.picking_id = sp_so.id
#                     AND sm2.sale_line_id = sol.id) AS so_delivery_date,

#                 -- بيانات الفاتورة/سطر الفاتورة
#                 aml.id              AS aml_id,
#                 am.id               AS move_id,
#                 am.state            AS am_state,
#                 am.payment_state    AS am_payment_state,
#                 aj.name             AS journal_name,
#                 am.name             AS inv_name_single,
#                 TO_CHAR(am.invoice_date, 'YYYY-MM-DD') AS inv_date_single,

#                 aml.quantity        AS inv_unit_qty,
#                 aml.price_unit      AS inv_unit_price,
#                 aml.discount        AS inv_discount,
#                 aml.product_packaging_id    AS inv_packaging_id,
#                 aml.product_packaging_qty   AS inv_packaging_qty,
#                 aml.product_packaging_price AS inv_packaging_price,
#                 aml.exercise_price  AS inv_excise_tax,

#                 CASE WHEN am.id IS NULL THEN 0 ELSE COALESCE(aml.price_subtotal, 0) END AS inv_price_subtotal,
#                 CASE WHEN am.id IS NULL THEN 0 ELSE COALESCE(aml.price_total, aml.price_subtotal, 0) END AS inv_price_total,

#                 -- الشريك وعناوينه + أعمدة الأسماء
#                 p.name AS partner_name, p.customer_code, p.partner_channel_id, p.outlet_id,
#                 p.sub_outlet_id, p.customer_type, p.customer_group_id, p.outlet_code,
#                 p.customer_subdivision_id, p.external_ref,
#                 (ps.complete_name || ', ' || ps.contact_address_complete) AS ship_display_name,
#                 pa.name AS assign_partner_name{partner_name_cols_sql},

#                 -- التغليف
#                 pks.name AS so_packaging_name,
#                 pki.name AS inv_packaging_name

#             FROM so_filtered sof
#             JOIN sale_order_line sol ON sol.order_id = sof.id

#             -- اربط سطور الفاتورة المرتبطة بسطر الـ SO
#             LEFT JOIN {rel_table} rel        ON rel.{col_sol} = sol.id
#             LEFT JOIN account_move_line aml  ON aml.id = rel.{col_aml}
#             LEFT JOIN account_move am        ON am.id = aml.move_id
#                                              AND am.move_type='out_invoice'
#                                              AND am.state='posted'
#                                              {inv_join_date_filter}

#             -- منتج SO
#             LEFT JOIN product_product  pp ON pp.id = sol.product_id
#             LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
#             LEFT JOIN product_category pc ON pc.id = pt.categ_id
#             LEFT JOIN product_brand    pb ON pb.id = pt.brand_id

#             -- منتج الفاتورة
#             LEFT JOIN product_product  pp_inv ON pp_inv.id = aml.product_id
#             LEFT JOIN product_template pt_inv ON pt_inv.id = pp_inv.product_tmpl_id

#             LEFT JOIN pick_agg ON pick_agg.so_id = sof.id
#             LEFT JOIN account_journal aj ON aj.id = am.journal_id

#             -- الشريك وعناوينه
#             LEFT JOIN res_partner p  ON p.id  = sof.partner_id
#             LEFT JOIN res_partner ps ON ps.id = sof.partner_shipping_id
#             LEFT JOIN res_partner pa ON pa.id = sof.so_assign_to
#             {partner_name_joins_sql}
#             LEFT JOIN product_packaging pks ON pks.id = sol.product_packaging_id
#             LEFT JOIN product_packaging pki ON pki.id = aml.product_packaging_id

#             -- أحدث ترانسفير Outgoing مرتبط بنفس سطر الـ SO
#             LEFT JOIN LATERAL (
#                 SELECT sp.*
#                 FROM stock_picking sp
#                 JOIN stock_move sm ON sm.picking_id = sp.id
#                 JOIN stock_picking_type spt2 ON spt2.id = sp.picking_type_id
#                 WHERE sp.sale_id = sof.id
#                   AND sm.sale_line_id = sol.id
#                   AND sp.state = 'done'
#                   AND spt2.code = 'outgoing'
#                 ORDER BY sp.date_done DESC NULLS LAST, sp.id DESC
#                 LIMIT 1
#             ) sp_so ON TRUE

#             ORDER BY sof.date_order, sof.id, sol.id, am.invoice_date NULLS LAST, aml.id
#         """
#         so_params_stream = tuple(so_where_params + exists_params + inv_join_params)
#         if so_sql_stream.count('%s') != len(so_params_stream):
#             raise ValidationError(
#                 f"Param mismatch in SO SQL: placeholders={so_sql_stream.count('%s')} params={len(so_params_stream)}")

#         self.env.cr.execute(so_sql_stream, so_params_stream)

#         for r in dictfetchmany(self.env.cr, FETCH_BATCH):
#             so_day = r['so_date_order'].strftime('%Y-%m-%d') if r.get('so_date_order') else ''
#             ship_to_site = safe_json(site_map.get(r['so_id'], ''))

#             so_price_subtotal = r.get('so_price_subtotal') or 0.0
#             so_price_total    = r.get('so_price_total') or so_price_subtotal
#             vat_amount        = so_price_total - so_price_subtotal

#             has_invoice = bool(r.get('move_id'))

#             inv_unit_qty   = (r.get('inv_unit_qty') or 0.0) if has_invoice else 0.0
#             inv_unit_price = (r.get('inv_unit_price') or 0.0) if has_invoice else 0.0
#             inv_discount   = (r.get('inv_discount') or 0.0) if has_invoice else 0.0

#             inv_discount_amount = inv_unit_price * inv_unit_qty * (inv_discount / 100.0)
#             inv_gross_amount    = inv_unit_price * inv_unit_qty

#             inv_price_subtotal  = (r.get('inv_price_subtotal') or 0.0) if has_invoice else 0.0
#             inv_price_total     = (r.get('inv_price_total') or 0.0)    if has_invoice else 0.0
#             inv_vat_amount      = inv_price_total - inv_price_subtotal

#             invoice_status_label = inv_status_selection.get(r.get('so_invoice_status'), 'N/A')
#             payment_state_label  = payment_state_selection.get(r.get('am_payment_state'), r.get('am_payment_state') or '')

#             _row_vals = [
#                 so_day,
#                 r.get('so_name') or '',
#                 r.get('partner_name') or '',
#                 r.get('customer_code') or '',
#                 r.get('channel_name') or '',
#                 r.get('outlet_class_name') or '',
#                 r.get('sub_class_name') or '',
#                 r.get('customer_type') or '',
#                 r.get('customer_group_id') or '',
#                 r.get('outlet_code') or '',
#                 r.get('ship_display_name') or '',
#                 r.get('sub_channel_name') or '',
#                 r.get('external_ref') or '',
#                 ship_to_site,
#                 r.get('so_po') or '',
#                 r.get('assign_partner_name') or '',
#                 so_day,
#                 r.get('product_name') or '',
#                 r.get('default_code') or '',
#                 r.get('category_name') or '',
#                 r.get('brand_name') or '',
#                 r.get('division') or '',
#                 r.get('so_packaging_name') or '',
#                 r.get('so_packaging_qty') or 0.0,
#                 r.get('so_packaging_price') or 0.0,
#                 r.get('inv_packaging_name') or '',
#                 (r.get('inv_packaging_qty') or 0.0) if has_invoice else 0.0,
#                 (r.get('inv_packaging_price') or 0.0) if has_invoice else 0.0,
#                 r.get('so_unit_qty') or 0.0,
#                 inv_unit_qty,
#                 r.get('so_unit_price') or 0.0,
#                 inv_unit_price,
#                 r.get('so_qty_delivered') or 0.0,
#                 r.get('so_qty_invoiced') or 0.0,
#                 r.get('so_purchase_price') or 0.0,
#                 (r.get('inv_excise_tax') or 0.0) if has_invoice else 0.0,
#                 inv_discount,
#                 inv_discount_amount,
#                 inv_gross_amount,
#                 so_price_subtotal,
#                 vat_amount,
#                 so_price_total,
#                 inv_price_subtotal,
#                 inv_vat_amount,
#                 inv_price_total,
#                 r.get('so_state') or '',
#                 r.get('delivery_status') or 'Pending',
#                 r.get('so_delivery_number') or '',
#                 r.get('so_delivery_date') or '',
#                 invoice_status_label,
#                 r.get('inv_name_single') or 'No Invoice',
#                 r.get('inv_date_single') or '',
#                 r.get('journal_name') or '',
#                 r.get('am_state') or '',
#                 payment_state_label,
#                 '',
#                 ''
#             ]
#             sheet.write_row(row, 0, _sanitize_row(_row_vals))
#             row += 1

#         # ===== قسم RMA / Credit Notes =====
#         rma_params = []
#         rma_date_filter = ""
#         if self.invoice_date_from:
#             rma_date_filter += " AND cn.invoice_date >= %s"
#             rma_params.append(datetime.combine(self.invoice_date_from, time.min))
#         if self.invoice_date_to:
#             rma_date_filter += " AND cn.invoice_date <= %s"
#             rma_params.append(datetime.combine(self.invoice_date_to, time.max))

#         rma_sql = f"""
#             WITH rma_base AS (
#                 SELECT
#                     r.id      AS rma_id,
#                     r.name    AS rma_name,
#                     r.date    AS rma_date,
#                     r.state   AS rma_state,
#                     r.sales_person_id AS salesman_partner_id,

#                     cn.id     AS inv_id,
#                     cn.name   AS inv_name,
#                     cn.invoice_date AS inv_date,
#                     cn.state  AS inv_state,
#                     cn.payment_state AS payment_state,
#                     aj.name   AS journal_name,

#                     r.partner_id            AS partner_id,
#                     r.partner_shipping_id   AS ship_partner_id
#                 FROM rma r
#                 LEFT JOIN account_move   cn ON cn.id = r.refund_id
#                 LEFT JOIN account_journal aj ON aj.id = cn.journal_id
#                 WHERE r.state NOT IN ('draft', 'cancelled')
#                   {rma_date_filter}
#             ),
#             rma_lines AS (
#                 SELECT
#                     rb.*,
#                     rl.id     AS rma_line_id,
#                     rl.product_id,
#                     rl.exercise_price  AS rma_excise_price,
#                     rl.product_packaging_id    AS so_packaging_id,
#                     rl.product_packaging_qty   AS so_packaging_qty,
#                     rl.product_packaging_price AS so_packaging_price,
#                     rl.price_unit              AS so_unit_price,
#                     rl.product_uom_qty         AS rma_so_unit_qty,
#                     rl.total                   AS line_total,
#                     rl.return_reason_id,
#                     rl.amount_tax              AS rma_amount_tax
#                 FROM rma_base rb
#                 JOIN rma_line rl ON rl.rma_id = rb.rma_id

#                 UNION ALL

#                 SELECT
#                     rb.*,
#                     rpl.id     AS rma_line_id,
#                     rpl.product_id,
#                     NULL::numeric  AS rma_excise_price,
#                     rpl.product_packaging_id   AS so_packaging_id,
#                     rpl.product_packaging_qty  AS so_packaging_qty,
#                     NULL::numeric              AS so_packaging_price,
#                     rpl.price_unit             AS so_unit_price,
#                     rpl.product_uom_qty        AS rma_so_unit_qty,
#                     rpl.total                  AS line_total,
#                     rpl.return_reason_id,
#                     NULL::numeric              AS rma_amount_tax
#                 FROM rma_base rb
#                 JOIN rma_product_line rpl ON rpl.rma_id = rb.rma_id
#             )
#             SELECT
#                 rl.rma_id, rl.rma_name, rl.rma_date, rl.rma_state,
#                 rl.salesman_partner_id,
#                 rl.inv_id, rl.inv_name, rl.inv_date,
#                 rl.partner_id, rl.ship_partner_id,
#                 rl.inv_state, rl.payment_state, rl.journal_name,

#                 rl.rma_line_id, rl.product_id,
#                 rl.so_packaging_id, rl.so_packaging_qty, rl.so_packaging_price,
#                 rl.so_unit_price, rl.rma_so_unit_qty, rl.line_total,
#                 rl.return_reason_id, rl.rma_amount_tax, rl.rma_excise_price,

#                 il.product_id              AS il_product_id,
#                 il.quantity                AS inv_unit_qty,
#                 il.price_unit              AS inv_unit_price,
#                 il.discount                AS inv_discount,
#                 il.product_packaging_id    AS inv_packaging_id,
#                 il.product_packaging_qty   AS inv_packaging_qty,
#                 il.product_packaging_price AS inv_packaging_price,
#                 COALESCE(il.price_subtotal, il.debit - il.credit, 0) AS inv_price_subtotal,
#                 COALESCE(il.price_total,   il.balance,
#                          COALESCE(il.debit - il.credit, 0))          AS inv_price_total,
#                 il.exercise_price          AS inv_excise_tax,

#                 pp.default_code,
#                 pt.name   AS product_name,
#                 pc.complete_name    AS category_name,
#                 pb.name   AS brand_name,
#                 pt.division AS division,
#                 pt.categ_id AS pt_categ_id,

#                 p.name AS partner_name, p.customer_code, p.partner_channel_id, p.outlet_id,
#                 p.sub_outlet_id, p.customer_type, p.customer_group_id, p.outlet_code,
#                 p.customer_subdivision_id, p.external_ref,
#                 (ps.complete_name || ', ' || ps.contact_address_complete) AS ship_display_name,
#                 sp.name AS salesman_name{partner_name_cols_sql},

#                 rr.name AS return_reason_name_jsonb,

#                 pk_so.name  AS so_packaging_name,
#                 pk_inv.name AS inv_packaging_name,

#                 sp_rma.name AS rma_delivery_number,
#                 (SELECT MAX(sml.date)
#                    FROM stock_move_line sml
#                    JOIN stock_move sm2 ON sm2.id = sml.move_id
#                   WHERE sml.picking_id = sp_rma.id
#                     AND (rl.product_id IS NULL OR sml.product_id = rl.product_id)) AS rma_delivery_date

#             FROM rma_lines rl

#             LEFT JOIN LATERAL (
#                 SELECT il.*
#                 FROM account_move_line il
#                 WHERE il.move_id = rl.inv_id
#                   AND (il.display_type IS NULL OR il.display_type = 'product')
#                   AND (il.tax_line_id IS NULL OR il.tax_line_id = 0)
#                   AND COALESCE(il.display_type, '') NOT IN ('tax','payment_term','line_section','line_note','rounding')
#                   AND (rl.product_id IS NULL OR il.product_id = rl.product_id)
#                 ORDER BY
#                   CASE WHEN il.product_id = rl.product_id THEN 0 ELSE 1 END,
#                   CASE WHEN COALESCE(il.product_packaging_id,0) = COALESCE(rl.so_packaging_id,0) THEN 0 ELSE 1 END,
#                   ABS(ABS(il.quantity) - ABS(COALESCE(rl.rma_so_unit_qty,0))) ASC,
#                   ABS(COALESCE(il.price_subtotal, il.debit - il.credit, il.balance, 0)) DESC,
#                   il.id DESC
#                 LIMIT 1
#             ) il ON TRUE

#             LEFT JOIN product_product  pp ON pp.id = rl.product_id
#             LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
#             LEFT JOIN product_category pc ON pc.id = pt.categ_id
#             LEFT JOIN product_brand    pb ON pb.id = pt.brand_id

#             LEFT JOIN res_partner p  ON p.id  = rl.partner_id
#             LEFT JOIN res_partner ps ON ps.id = rl.ship_partner_id

#             LEFT JOIN res_partner sp ON sp.id = rl.salesman_partner_id
#             {partner_name_joins_sql}
#             LEFT JOIN rma_return_reason rr ON rr.id = rl.return_reason_id

#             LEFT JOIN product_packaging pk_inv ON pk_inv.id = il.product_packaging_id
#             LEFT JOIN product_packaging pk_so  ON pk_so.id  = rl.so_packaging_id

#             -- أحدث Picking خاص بالاستلام (Incoming) لهذا الـ RMA
#             LEFT JOIN LATERAL (
#                 SELECT sp.*
#                 FROM stock_picking sp
#                 JOIN stock_move sm ON sm.picking_id = sp.id
#                 JOIN stock_picking_type spt2 ON spt2.id = sp.picking_type_id
#                 WHERE sp.origin = rl.rma_name
#                   AND (rl.product_id IS NULL OR sm.product_id = rl.product_id)
#                   AND sp.state = 'done'
#                   AND spt2.code = 'incoming'
#                 ORDER BY sp.date_done DESC NULLS LAST, sp.id DESC
#                 LIMIT 1
#             ) sp_rma ON TRUE

#             ORDER BY rl.rma_date, rl.rma_id, rl.rma_line_id
#         """

#         self.env.cr.execute(rma_sql, tuple(rma_params))

#         rma_title_fmt = workbook.add_format(
#             {'bold': True, 'font_size': 14, 'bg_color': '#5B9BD5', 'font_color': 'white', 'align': 'center'})
#         rma_header_format = workbook.add_format(
#             {'bold': True, 'bg_color': '#FFE699', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
#         rma_header_written = False

#         for r in dictfetchmany(self.env.cr, FETCH_BATCH):
#             if not rma_header_written:
#                 sheet.write(row, 0, "RMA / Credit Notes", rma_title_fmt)
#                 row += 1
#                 rma_headers = [h.replace('SO_', 'RMA_') for h in headers]
#                 for i, h in enumerate(rma_headers):
#                     sheet.write(row, i, h, rma_header_format)
#                 row += 1
#                 rma_header_written = True

#             inv_unit_qty = r.get('inv_unit_qty') if r.get('inv_unit_qty') is not None else 0.0
#             inv_unit_price = r.get('inv_unit_price') if r.get('inv_unit_price') is not None else 0.0
#             inv_discount = r.get('inv_discount') if r.get('inv_discount') is not None else 0.0
#             inv_pack_qty = r.get('inv_packaging_qty') if r.get('inv_packaging_qty') is not None else 0.0
#             inv_pack_price = r.get('inv_packaging_price') if r.get('inv_packaging_price') is not None else 0.0
#             inv_packaging_name = r.get('inv_packaging_name') or ''

#             inv_gross_amount = inv_unit_price * inv_unit_qty
#             inv_discount_amount = inv_unit_price * inv_unit_qty * (inv_discount / 100.0)

#             inv_sub_use = (r.get('inv_price_subtotal') or 0.0)
#             inv_tot_use = (r.get('inv_price_total') or 0.0)
#             inv_vat_use = max(inv_tot_use - inv_sub_use, 0.0)

#             excise_tax_val = r.get('inv_excise_tax') or 0.0

#             rma_unit_qty = r.get('rma_so_unit_qty') or 0.0
#             rma_unit_price = r.get('so_unit_price') or 0.0
#             rma_total_after = r.get('line_total') or 0.0
#             rma_vat_amount = r.get('rma_amount_tax') if r.get('rma_amount_tax') is not None else 0.0

#             rma_packaging_name = r.get('so_packaging_name') or ''
#             rma_pack_qty = r.get('so_packaging_qty') if r.get('so_packaging_qty') is not None else 0.0
#             rma_pack_price = r.get('so_packaging_price') if r.get('so_packaging_price') is not None else 0.0

#             return_reason_label = safe_json(r.get('return_reason_name_jsonb'))
#             rma_day = r['rma_date'].strftime('%Y-%m-%d') if r.get('rma_date') else ''
#             inv_day = r['inv_date'].strftime('%Y-%m-%d') if r.get('inv_date') else ''

#             EPS = 1e-6
#             has_aml = bool(r.get('il_product_id'))
#             inv_amount_for_sign = inv_sub_use if abs(inv_sub_use) > EPS else inv_tot_use
#             is_discount = has_aml and (inv_amount_for_sign < -EPS)

#             def _absf(v):
#                 try:
#                     return abs(float(v or 0.0))
#                 except Exception:
#                     return 0.0

#             rma_unit_qty = _absf(rma_unit_qty)
#             rma_unit_price = _absf(rma_unit_price)
#             rma_total_after = _absf(rma_total_after)
#             rma_vat_amount = _absf(rma_vat_amount)
#             rma_pack_qty = _absf(rma_pack_qty)
#             rma_pack_price = _absf(rma_pack_price)
#             rma_subtotal = max(rma_total_after - rma_vat_amount, 0.0)

#             sign_rma = 1 if is_discount else -1
#             rma_unit_qty *= sign_rma
#             rma_unit_price *= sign_rma
#             rma_total_after *= sign_rma
#             rma_vat_amount *= sign_rma
#             rma_subtotal *= sign_rma
#             rma_pack_qty *= sign_rma
#             rma_pack_price *= sign_rma

#             sign_inv = -1
#             inv_unit_qty *= sign_inv
#             inv_pack_qty *= sign_inv
#             inv_unit_price *= sign_inv
#             inv_gross_amount *= sign_inv
#             inv_discount_amount *= sign_inv
#             inv_sub_use *= sign_inv
#             inv_tot_use *= sign_inv
#             inv_vat_use *= sign_inv
#             excise_tax_val *= sign_inv
#             inv_discount *= sign_inv

#             _row_vals = [
#                 rma_day,
#                 r.get('rma_name') or '',
#                 r.get('partner_name') or '',
#                 r.get('customer_code') or '',
#                 r.get('channel_name') or '',
#                 r.get('outlet_class_name') or '',
#                 r.get('sub_class_name') or '',
#                 r.get('customer_type') or '',
#                 r.get('customer_group_id') or '',
#                 r.get('outlet_code') or '',
#                 r.get('ship_display_name') or '',
#                 r.get('sub_channel_name') or '',
#                 r.get('external_ref') or '',
#                 '',  # Ship to Site
#                 '',  # Customer Po Reference
#                 r.get('salesman_name') or '',
#                 rma_day,
#                 r.get('product_name') or '',
#                 r.get('default_code') or '',
#                 r.get('category_name') or '',
#                 r.get('brand_name') or '',
#                 r.get('division') or '',

#                 rma_packaging_name,
#                 rma_pack_qty,
#                 rma_pack_price,

#                 inv_packaging_name,
#                 inv_pack_qty,
#                 inv_pack_price,

#                 rma_unit_qty,
#                 inv_unit_qty,
#                 rma_unit_price,
#                 inv_unit_price,

#                 '',  # Delivered Qty
#                 '',  # Invoiced Qty
#                 '',  # Cost
#                 excise_tax_val,

#                 inv_discount,
#                 inv_discount_amount,
#                 inv_gross_amount,

#                 rma_subtotal,
#                 rma_vat_amount,
#                 rma_total_after,

#                 inv_sub_use,
#                 inv_vat_use,
#                 inv_tot_use,

#                 r.get('rma_state') or '',                           # Sales Order Status
#                 ('Delivered' if r.get('rma_delivery_number') else 'Pending'),  # Delivery Status
#                 r.get('rma_delivery_number') or '',                 # Delivery Number
#                 r.get('rma_delivery_date') or '',                   # Delivery Date (sml.date)
#                 (r.get('inv_state') or ''),                         # Invoice Status (SO)
#                 (r.get('inv_name') or 'No Invoice'),
#                 inv_day,
#                 r.get('journal_name') or '',
#                 (r.get('inv_state') or ''),                         # Invoice State
#                 (payment_state_selection.get(r.get('payment_state'), r.get('payment_state') or '')),
#                 safe_json(r.get('return_reason_name_jsonb')),
#                 r.get('rma_state') or ''
#             ]
#             sheet.write_row(row, 0, _sanitize_row(_row_vals))
#             row += 1

#         # ===== سطر الفترات =====
#         invoice_date_from_local = fields.Datetime.context_timestamp(self, self.invoice_date_from) if self.invoice_date_from else None
#         invoice_date_to_local   = fields.Datetime.context_timestamp(self, self.invoice_date_to) if self.invoice_date_to else None
#         period_row = (
#             f"Sales Order Period: {self.date_from.strftime('%Y-%m-%d') if self.date_from else 'N/A'} to "
#             f"{self.date_to.strftime('%Y-%m-%d') if self.date_to else 'N/A'}    |    "
#             f"Invoice Period: {invoice_date_from_local.strftime('%Y-%m-%d') if invoice_date_from_local else 'N/A'} to "
#             f"{invoice_date_to_local.strftime('%Y-%m-%d') if invoice_date_to_local else 'N/A'}"
#         )
#         sheet.write(row, 0, period_row, period_format)

#         # ===== إنهاء الملف المؤقّت ورفعه للحقل =====
#         workbook.close()
#         with open(tmp_path, 'rb') as f:
#             self.file_data = base64.b64encode(f.read())
#         self.file_name = "sales_order_and_credit_notes_report.xlsx"
#         for _ in range(10):
#             try:
#                 os.remove(tmp_path)
#                 break
#             except PermissionError:
#                 pytime.sleep(0.2)

#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'sales.order.rma.report.delivery',
#             'view_mode': 'form',
#             'res_id': self.id,
#             'target': 'new',
#         }


from odoo import models, fields, api
import base64, os, tempfile
import xlsxwriter
from odoo.exceptions import ValidationError
from datetime import datetime, time, date
from decimal import Decimal
import time as pytime


class SalesOrderRmaReportDelivery(models.TransientModel):
    _name = 'sales.order.rma.report.delivery'
    _description = 'Sales Order Rma Report Wizard Delivery'

    date_from = fields.Date(string="Sales Order Start Date")
    date_to = fields.Date(string="Sales Order End Date")
    file_data = fields.Binary(string="Report File", readonly=True)
    file_name = fields.Char(string="File Name")

    show_invoice_dates = fields.Boolean(string="Filter by Sales Order Date")

    invoice_date_from = fields.Datetime(string="Invoice Start Date")
    invoice_date_to = fields.Datetime(string="Invoice End Date")
    refund_id = fields.Many2one('account.move', string="Refund Invoice")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_to < record.date_from:
                raise ValidationError("End Date cannot be before Start Date.")

    @api.constrains('invoice_date_from', 'invoice_date_to')
    def _check_invoice_dates(self):
        for record in self:
            if record.invoice_date_from and record.invoice_date_to and record.invoice_date_to < record.invoice_date_from:
                raise ValidationError("Invoice End Date cannot be before Invoice Start Date.")

    def generate_report(self):
        # ===== إعدادات الأداء =====
        FETCH_BATCH = 5000
        READ_CHUNK = 5000
        self.env.cr.itersize = 10000

        # تهيئة جلسة Postgres للاستعلامات الثقيلة
        try:
            self.env.cr.execute("SET LOCAL work_mem = %s", ('256MB',))
            self.env.cr.execute("SET LOCAL jit = off")
        except Exception:
            pass

        def dictfetchmany(cr, size):
            cols = [d[0] for d in cr.description]
            while True:
                rows = cr.fetchmany(size)
                if not rows:
                    break
                for r in rows:
                    yield dict(zip(cols, r))

        def _xlsx_cell(v):
            if v is None:
                return ''
            if isinstance(v, Decimal):
                return float(v)
            if isinstance(v, (int, float)):
                return v
            if isinstance(v, (datetime, date)):
                return v.strftime('%Y-%m-%d')
            if isinstance(v, (list, tuple)):
                if len(v) >= 2 and isinstance(v[1], (str, int, float)):
                    return v[1]
                return ' | '.join(str(_xlsx_cell(x)) for x in v)
            if isinstance(v, dict):  # JSONB/ترجمات
                if v.get('en_US'):
                    return v['en_US']
                for k in ('name', 'display_name', 'label'):
                    if v.get(k):
                        return v[k]
                if v:
                    return str(next(iter(v.values())))
                return ''
            if isinstance(v, (bytes, bytearray)):
                try:
                    return v.decode('utf-8', 'ignore')
                except Exception:
                    return str(v)
            return str(v)

        def _sanitize_cell(v):
            if v is None:
                return ''
            if isinstance(v, (str, int, float)):
                return v
            if isinstance(v, (datetime, date)):
                return v.strftime('%Y-%m-%d')
            if isinstance(v, Decimal):
                return float(v)
            if isinstance(v, (dict, list, tuple, bytes, bytearray)):
                return _xlsx_cell(v)
            return str(v)

        def _sanitize_row(row_vals):
            return [_sanitize_cell(x) for x in row_vals]

        safe_json = _xlsx_cell

        # ===== ربط سطر الفاتورة بسطر SO عبر الجدول الوسيط =====
        m2m = self.env['account.move.line']._fields['sale_line_ids']
        rel_table = m2m.relation
        col_aml   = m2m.column1
        col_sol   = m2m.column2

        # ===== تجهيز JOINs لأسماء العلاقات =====
        resolve_fields = [
            ('partner_channel_id',      'channel_name'),
            ('outlet_id',               'outlet_class_name'),
            ('sub_outlet_id',           'sub_class_name'),
            ('customer_subdivision_id', 'sub_channel_name'),
        ]
        FIELD_LABEL_COL_OVERRIDES = {
            'partner_channel_id': 'channel_name',
            'customer_subdivision_id': 'name',
            'outlet_id': 'outlet_name',
            'sub_outlet_id': 'name',
        }

        partner_name_cols = []
        partner_name_joins = []
        for field, label in resolve_fields:
            fld = self.env['res.partner']._fields.get(field)
            if fld and getattr(fld, 'comodel_name', None):
                model = self.env[fld.comodel_name]
                table = model._table
                alias = f"rp_{field}"

                chosen = FIELD_LABEL_COL_OVERRIDES.get(field)
                if chosen:
                    fdef = model._fields.get(chosen)
                    if not (fdef and getattr(fdef, 'store', False)):
                        chosen = None

                if not chosen:
                    candidates = []
                    rec_name = (getattr(model, '_rec_name', None) or 'name')
                    candidates.append(rec_name)
                    candidates += ['name', 'complete_name', 'code', 'ref', 'title', 'short_name', 'x_name']
                    for c in candidates:
                        fdef = model._fields.get(c)
                        if fdef and getattr(fdef, 'store', False):
                            chosen = c
                            break

                if chosen:
                    partner_name_joins.append(f"LEFT JOIN {table} {alias} ON {alias}.id = p.{field}")
                    partner_name_cols.append(f"{alias}.{chosen} AS {label}")
                else:
                    partner_name_cols.append(f"CAST(p.{field} AS varchar) AS {label}")
            else:
                partner_name_cols.append(f"CAST(p.{field} AS varchar) AS {label}")

        partner_name_cols_sql = ",\n                " + ",\n                ".join(partner_name_cols) if partner_name_cols else ""
        partner_name_joins_sql = ("\n            " + "\n            ".join(partner_name_joins) + "\n") if partner_name_joins else "\n"

        # ===== ملف الإكسل =====
        fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        workbook = xlsxwriter.Workbook(tmp_path, {'constant_memory': True})
        sheet = workbook.add_worksheet("Sales Orders & Credit Notes")

        header_format = workbook.add_format({'bold': True,'bg_color': '#D3D3D3','border': 1,'align': 'center','valign': 'vcenter'})
        period_format = workbook.add_format({'bold': True,'font_size': 14,'align': 'center','valign': 'vcenter','bg_color': '#5B9BD5','font_color': 'white'})

        headers = ['Day','Order Number','Customer','Customer Code','Channel','Outlet Classification',
                   'Sub Classification','Customer Type','Customer Group','Customer Outlet Code','Delivery Address','Sub Channel',
                   'External Reference','Ship to Site','Customer Po Reference','Salesman','Order Date','Product','Internal Reference','Category',
                   'Brand','Product Division','SO_Product Packaging','SO_Packaging Quantity',
                   'SO_Product Packaging Price','INV_Product Packaging','INV_Packaging Quantity',
                   'INV_Product Packaging Price','SO_Unit Qty','INV_Unit Qty','SO_Unit Price','INV_Unit Price',
                   'SO_Delivered Qty','Invoiced Qty','Cost','Excise Tax','INV_Discount(%)','INV_Discount Amount',
                   'INV_Gross Amount','SO_Total Before Vat(TAX)','SO_VAT(TAX) Amount','SO_Total after VAT(TAX)',
                   'INV_Total Before Vat(TAX)','INV_VAT(TAX) Amount','INV_Total after VAT(TAX)',
                   'Sales Order Status','Delivery Status','Delivery Number','Delivery Date','Invoice Status','Invoice Number','Invoice Dates',
                   'Journal Name','Invoice State','Payment Status','Return Reason','RMA Status']
        for i, h in enumerate(headers):
            sheet.write(0, i, h, header_format)

        row = 1
        inv_status_selection = dict(self.env['sale.order']._fields['invoice_status'].selection)
        payment_state_selection = dict(self.env['account.move']._fields['payment_state'].selection)

        # ===== قسم أوامر البيع =====
        so_wheres = ["so.state IN ('sale','done')"]
        so_where_params = []
        if self.show_invoice_dates:
            if self.date_from:
                so_wheres.append("so.date_order >= %s")
                so_where_params.append(datetime.combine(self.date_from, time.min))
            if self.date_to:
                so_wheres.append("so.date_order <= %s")
                so_where_params.append(datetime.combine(self.date_to, time.max))

        invoice_date_subfilter = ""
        exists_params = []
        if (not self.show_invoice_dates) and (self.invoice_date_from or self.invoice_date_to):
            invoice_date_subfilter = f"""
                AND EXISTS (
                    SELECT 1
                    FROM sale_order_line sol2
                    JOIN {rel_table} rel2 ON rel2.{col_sol} = sol2.id
                    JOIN account_move_line aml2 ON aml2.id = rel2.{col_aml}
                    JOIN account_move am2 ON am2.id = aml2.move_id
                    WHERE sol2.order_id = so.id
                      AND am2.move_type = 'out_invoice'
                      AND am2.state = 'posted'
                      {"AND am2.invoice_date >= %s" if self.invoice_date_from else ""}
                      {"AND am2.invoice_date <= %s" if self.invoice_date_to else ""}
                )
            """
            if self.invoice_date_from:
                exists_params.append(datetime.combine(self.invoice_date_from, time.min))
            if self.invoice_date_to:
                exists_params.append(datetime.combine(self.invoice_date_to, time.max))

        inv_join_date_filter = ""
        inv_join_params = []
        if self.invoice_date_from:
            inv_join_date_filter += " AND am.invoice_date >= %s"
            inv_join_params.append(datetime.combine(self.invoice_date_from, time.min))
        if self.invoice_date_to:
            inv_join_date_filter += " AND am.invoice_date <= %s"
            inv_join_params.append(datetime.combine(self.invoice_date_to, time.max))

        so_sql_stream = f"""
            WITH so_filtered AS (
                SELECT
                    so.id, so.name, so.state, so.invoice_status, so.date_order,
                    so.partner_id, so.partner_shipping_id, so.po_number,
                    so.assign_to AS so_assign_to
                FROM sale_order so
                WHERE {' AND '.join(so_wheres)}
                {invoice_date_subfilter}
            ),
            pick_agg AS (
                SELECT
                    sof.id AS so_id,
                    COUNT(sp.id) AS total_picks,
                    SUM(CASE WHEN sp.state='done' THEN 1 ELSE 0 END) AS done_picks
                FROM so_filtered sof
                LEFT JOIN stock_picking sp ON sp.sale_id = sof.id
                LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE spt.code = 'outgoing'     -- فقط Outbound
                GROUP BY sof.id
            )
            SELECT
                -- SO
                sof.id               AS so_id,
                sof.name             AS so_name,
                sof.state            AS so_state,
                sof.invoice_status   AS so_invoice_status,
                sof.date_order       AS so_date_order,
                sof.partner_id       AS partner_id,
                sof.partner_shipping_id AS ship_partner_id,
                sof.po_number        AS so_po,
                sof.so_assign_to     AS so_assign_to,

                -- SO Line
                sol.id              AS sol_id,
                sol.product_id      AS product_id,
                sol.product_uom_qty AS so_unit_qty,
                sol.price_unit      AS so_unit_price,
                sol.discount        AS so_discount,
                sol.qty_delivered   AS so_qty_delivered,
                sol.qty_invoiced    AS so_qty_invoiced,
                sol.purchase_price  AS so_purchase_price,
                sol.exercise_price  AS so_exercise_price,
                sol.product_packaging_id   AS so_packaging_id,
                sol.product_packaging_qty  AS so_packaging_qty,
                sol.product_packaging_price AS so_packaging_price,
                sol.price_subtotal  AS so_price_subtotal,
                sol.price_total     AS so_price_total,

                -- منتج الفاتورة (أولوية) ثم منتج SO
                COALESCE(pt_inv.name, pt.name)                               AS product_name,
                COALESCE(pp_inv.default_code, pp.default_code)               AS default_code,
                pc.complete_name                                             AS category_name,
                pb.name                                                      AS brand_name,
                pt.division                                                  AS division,

                -- حالة التوصيل
                CASE
                  WHEN pick_agg.total_picks IS NULL THEN 'Pending'
                  WHEN pick_agg.total_picks = pick_agg.done_picks AND pick_agg.total_picks > 0 THEN 'Delivered'
                  ELSE 'Pending'
                END AS delivery_status,

                -- رقم وتاريخ الحركة الفعلية (Outgoing) لسطر الـ SO
                sp_so.name AS so_delivery_number,
                (SELECT MAX(sml.date)
                   FROM stock_move_line sml
                   JOIN stock_move sm2 ON sm2.id = sml.move_id
                  WHERE sml.picking_id = sp_so.id
                    AND sm2.sale_line_id = sol.id) AS so_delivery_date,

                -- بيانات الفاتورة/سطر الفاتورة
                aml.id              AS aml_id,
                am.id               AS move_id,
                am.state            AS am_state,
                am.payment_state    AS am_payment_state,
                aj.name             AS journal_name,
                am.name             AS inv_name_single,
                TO_CHAR(am.invoice_date, 'YYYY-MM-DD') AS inv_date_single,

                aml.quantity        AS inv_unit_qty,
                aml.price_unit      AS inv_unit_price,
                aml.discount        AS inv_discount,
                aml.product_packaging_id    AS inv_packaging_id,
                aml.product_packaging_qty   AS inv_packaging_qty,
                aml.product_packaging_price AS inv_packaging_price,
                aml.exercise_price  AS inv_excise_tax,

                CASE WHEN am.id IS NULL THEN 0 ELSE COALESCE(aml.price_subtotal, 0) END AS inv_price_subtotal,
                CASE WHEN am.id IS NULL THEN 0 ELSE COALESCE(aml.price_total, aml.price_subtotal, 0) END AS inv_price_total,

                -- الشريك وعناوينه + Ship to Site (partner_shipping فقط)
                p.name AS partner_name, p.customer_code, p.partner_channel_id, p.outlet_id,
                p.sub_outlet_id, p.customer_type, p.customer_group_id, p.outlet_code,
                p.customer_subdivision_id, p.external_ref,
                (ps.complete_name || ', ' || ps.contact_address_complete) AS ship_display_name,
                pa.name AS assign_partner_name{partner_name_cols_sql},
                NULLIF(ps.site_number::text, '') AS ship_site_number,

                -- التغليف
                pks.name AS so_packaging_name,
                pki.name AS inv_packaging_name

            FROM so_filtered sof
            JOIN sale_order_line sol ON sol.order_id = sof.id

            -- اربط سطور الفاتورة المرتبطة بسطر الـ SO
            LEFT JOIN {rel_table} rel        ON rel.{col_sol} = sol.id
            LEFT JOIN account_move_line aml  ON aml.id = rel.{col_aml}
            LEFT JOIN account_move am        ON am.id = aml.move_id
                                             AND am.move_type='out_invoice'
                                             AND am.state='posted'
                                             {inv_join_date_filter}

            -- منتج SO
            LEFT JOIN product_product  pp ON pp.id = sol.product_id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pc ON pc.id = pt.categ_id
            LEFT JOIN product_brand    pb ON pb.id = pt.brand_id

            -- منتج الفاتورة
            LEFT JOIN product_product  pp_inv ON pp_inv.id = aml.product_id
            LEFT JOIN product_template pt_inv ON pt_inv.id = pp_inv.product_tmpl_id

            LEFT JOIN pick_agg ON pick_agg.so_id = sof.id
            LEFT JOIN account_journal aj ON aj.id = am.journal_id

            -- الشريك وعنوان الشحن فقط
            LEFT JOIN res_partner p  ON p.id  = sof.partner_id
            LEFT JOIN res_partner ps ON ps.id = sof.partner_shipping_id
            LEFT JOIN res_partner pa ON pa.id = sof.so_assign_to
            {partner_name_joins_sql}
            LEFT JOIN product_packaging pks ON pks.id = sol.product_packaging_id
            LEFT JOIN product_packaging pki ON pki.id = aml.product_packaging_id

            -- أحدث ترانسفير Outgoing مرتبط بنفس سطر الـ SO
            LEFT JOIN LATERAL (
                SELECT sp.*
                FROM stock_picking sp
                JOIN stock_move sm ON sm.picking_id = sp.id
                JOIN stock_picking_type spt2 ON spt2.id = sp.picking_type_id
                WHERE sp.sale_id = sof.id
                  AND sm.sale_line_id = sol.id
                  AND sp.state = 'done'
                  AND spt2.code = 'outgoing'
                ORDER BY sp.date_done DESC NULLS LAST, sp.id DESC
                LIMIT 1
            ) sp_so ON TRUE

            ORDER BY sof.date_order, sof.id, sol.id, am.invoice_date NULLS LAST, aml.id
        """
        so_params_stream = tuple(so_where_params + exists_params + inv_join_params)
        if so_sql_stream.count('%s') != len(so_params_stream):
            raise ValidationError(
                f"Param mismatch in SO SQL: placeholders={so_sql_stream.count('%s')} params={len(so_params_stream)}")

        self.env.cr.execute(so_sql_stream, so_params_stream)

        for r in dictfetchmany(self.env.cr, FETCH_BATCH):
            so_day = r['so_date_order'].strftime('%Y-%m-%d') if r.get('so_date_order') else ''
            ship_to_site = safe_json(r.get('ship_site_number') or '')

            so_price_subtotal = r.get('so_price_subtotal') or 0.0
            so_price_total    = r.get('so_price_total') or so_price_subtotal
            vat_amount        = so_price_total - so_price_subtotal

            has_invoice = bool(r.get('move_id'))

            inv_unit_qty   = (r.get('inv_unit_qty') or 0.0) if has_invoice else 0.0
            inv_unit_price = (r.get('inv_unit_price') or 0.0) if has_invoice else 0.0
            inv_discount   = (r.get('inv_discount') or 0.0) if has_invoice else 0.0

            inv_discount_amount = inv_unit_price * inv_unit_qty * (inv_discount / 100.0)
            inv_gross_amount    = inv_unit_price * inv_unit_qty

            inv_price_subtotal  = (r.get('inv_price_subtotal') or 0.0) if has_invoice else 0.0
            inv_price_total     = (r.get('inv_price_total') or 0.0)    if has_invoice else 0.0
            inv_vat_amount      = inv_price_total - inv_price_subtotal

            invoice_status_label = inv_status_selection.get(r.get('so_invoice_status'), 'N/A')
            payment_state_label  = payment_state_selection.get(r.get('am_payment_state'), r.get('am_payment_state') or '')

            _row_vals = [
                so_day,
                r.get('so_name') or '',
                r.get('partner_name') or '',
                r.get('customer_code') or '',
                r.get('channel_name') or '',
                r.get('outlet_class_name') or '',
                r.get('sub_class_name') or '',
                r.get('customer_type') or '',
                r.get('customer_group_id') or '',
                r.get('outlet_code') or '',
                r.get('ship_display_name') or '',
                r.get('sub_channel_name') or '',
                r.get('external_ref') or '',
                ship_to_site,
                r.get('so_po') or '',
                r.get('assign_partner_name') or '',
                so_day,
                r.get('product_name') or '',
                r.get('default_code') or '',
                r.get('category_name') or '',
                r.get('brand_name') or '',
                r.get('division') or '',
                r.get('so_packaging_name') or '',
                r.get('so_packaging_qty') or 0.0,
                r.get('so_packaging_price') or 0.0,
                r.get('inv_packaging_name') or '',
                (r.get('inv_packaging_qty') or 0.0) if has_invoice else 0.0,
                (r.get('inv_packaging_price') or 0.0) if has_invoice else 0.0,
                r.get('so_unit_qty') or 0.0,
                inv_unit_qty,
                r.get('so_unit_price') or 0.0,
                inv_unit_price,
                r.get('so_qty_delivered') or 0.0,
                r.get('so_qty_invoiced') or 0.0,
                r.get('so_purchase_price') or 0.0,
                (r.get('inv_excise_tax') or 0.0) if has_invoice else 0.0,
                inv_discount,
                inv_discount_amount,
                inv_gross_amount,
                so_price_subtotal,
                vat_amount,
                so_price_total,
                inv_price_subtotal,
                inv_vat_amount,
                inv_price_total,
                r.get('so_state') or '',
                r.get('delivery_status') or 'Pending',
                r.get('so_delivery_number') or '',
                r.get('so_delivery_date') or '',
                invoice_status_label,
                r.get('inv_name_single') or 'No Invoice',
                r.get('inv_date_single') or '',
                r.get('journal_name') or '',
                r.get('am_state') or '',
                payment_state_label,
                '',
                ''
            ]
            sheet.write_row(row, 0, _sanitize_row(_row_vals))
            row += 1

        # ===== قسم RMA / Credit Notes =====
        rma_params = []
        rma_date_filter = ""
        if self.invoice_date_from:
            rma_date_filter += " AND cn.invoice_date >= %s"
            rma_params.append(datetime.combine(self.invoice_date_from, time.min))
        if self.invoice_date_to:
            rma_date_filter += " AND cn.invoice_date <= %s"
            rma_params.append(datetime.combine(self.invoice_date_to, time.max))

        rma_sql = f"""
            WITH rma_base AS (
                SELECT
                    r.id      AS rma_id,
                    r.name    AS rma_name,
                    r.date    AS rma_date,
                    r.state   AS rma_state,
                    r.sales_person_id AS salesman_partner_id,

                    cn.id     AS inv_id,
                    cn.name   AS inv_name,
                    cn.invoice_date AS inv_date,
                    cn.state  AS inv_state,
                    cn.payment_state AS payment_state,
                    aj.name   AS journal_name,

                    r.partner_id            AS partner_id,
                    r.partner_shipping_id   AS ship_partner_id
                FROM rma r
                LEFT JOIN account_move   cn ON cn.id = r.refund_id
                LEFT JOIN account_journal aj ON aj.id = cn.journal_id
                WHERE r.state NOT IN ('draft', 'cancelled')
                  {rma_date_filter}
            ),
            rma_lines AS (
                SELECT
                    rb.*,
                    rl.id     AS rma_line_id,
                    rl.product_id,
                    rl.exercise_price  AS rma_excise_price,
                    rl.product_packaging_id    AS so_packaging_id,
                    rl.product_packaging_qty   AS so_packaging_qty,
                    rl.product_packaging_price AS so_packaging_price,
                    rl.price_unit              AS so_unit_price,
                    rl.product_uom_qty         AS rma_so_unit_qty,
                    rl.total                   AS line_total,
                    rl.return_reason_id,
                    rl.amount_tax              AS rma_amount_tax
                FROM rma_base rb
                JOIN rma_line rl ON rl.rma_id = rb.rma_id

                UNION ALL

                SELECT
                    rb.*,
                    rpl.id     AS rma_line_id,
                    rpl.product_id,
                    NULL::numeric  AS rma_excise_price,
                    rpl.product_packaging_id   AS so_packaging_id,
                    rpl.product_packaging_qty  AS so_packaging_qty,
                    NULL::numeric              AS so_packaging_price,
                    rpl.price_unit             AS so_unit_price,
                    rpl.product_uom_qty        AS rma_so_unit_qty,
                    rpl.total                  AS line_total,
                    rpl.return_reason_id,
                    NULL::numeric              AS rma_amount_tax
                FROM rma_base rb
                JOIN rma_product_line rpl ON rpl.rma_id = rb.rma_id
            )
            SELECT
                rl.rma_id, rl.rma_name, rl.rma_date, rl.rma_state,
                rl.salesman_partner_id,
                rl.inv_id, rl.inv_name, rl.inv_date,
                rl.partner_id, rl.ship_partner_id,
                rl.inv_state, rl.payment_state, rl.journal_name,

                rl.rma_line_id, rl.product_id,
                rl.so_packaging_id, rl.so_packaging_qty, rl.so_packaging_price,
                rl.so_unit_price, rl.rma_so_unit_qty, rl.line_total,
                rl.return_reason_id, rl.rma_amount_tax, rl.rma_excise_price,

                il.product_id              AS il_product_id,
                il.quantity                AS inv_unit_qty,
                il.price_unit              AS inv_unit_price,
                il.discount                AS inv_discount,
                il.product_packaging_id    AS inv_packaging_id,
                il.product_packaging_qty   AS inv_packaging_qty,
                il.product_packaging_price AS inv_packaging_price,
                COALESCE(il.price_subtotal, il.debit - il.credit, 0) AS inv_price_subtotal,
                COALESCE(il.price_total,   il.balance,
                         COALESCE(il.debit - il.credit, 0))          AS inv_price_total,
                il.exercise_price          AS inv_excise_tax,

                pp.default_code,
                pt.name   AS product_name,
                pc.complete_name    AS category_name,
                pb.name   AS brand_name,
                pt.division AS division,
                pt.categ_id AS pt_categ_id,

                -- العميل + Ship to Site (partner_shipping فقط)
                p.name AS partner_name, p.customer_code, p.partner_channel_id, p.outlet_id,
                p.sub_outlet_id, p.customer_type, p.customer_group_id, p.outlet_code,
                p.customer_subdivision_id, p.external_ref,
                (ps.complete_name || ', ' || ps.contact_address_complete) AS ship_display_name,
                NULLIF(ps.site_number::text, '') AS ship_site_number,
                sp.name AS salesman_name{partner_name_cols_sql},

                rr.name AS return_reason_name_jsonb,

                pk_so.name  AS so_packaging_name,
                pk_inv.name AS inv_packaging_name,

                sp_rma.name AS rma_delivery_number,
                (SELECT MAX(sml.date)
                   FROM stock_move_line sml
                   JOIN stock_move sm2 ON sm2.id = sml.move_id
                  WHERE sml.picking_id = sp_rma.id
                    AND (rl.product_id IS NULL OR sml.product_id = rl.product_id)) AS rma_delivery_date

            FROM rma_lines rl

            LEFT JOIN LATERAL (
                SELECT il.*
                FROM account_move_line il
                WHERE il.move_id = rl.inv_id
                  AND (il.display_type IS NULL OR il.display_type = 'product')
                  AND (il.tax_line_id IS NULL OR il.tax_line_id = 0)
                  AND COALESCE(il.display_type, '') NOT IN ('tax','payment_term','line_section','line_note','rounding')
                  AND (rl.product_id IS NULL OR il.product_id = rl.product_id)
                ORDER BY
                  CASE WHEN il.product_id = rl.product_id THEN 0 ELSE 1 END,
                  CASE WHEN COALESCE(il.product_packaging_id,0) = COALESCE(rl.so_packaging_id,0) THEN 0 ELSE 1 END,
                  ABS(ABS(il.quantity) - ABS(COALESCE(rl.rma_so_unit_qty,0))) ASC,
                  ABS(COALESCE(il.price_subtotal, il.debit - il.credit, il.balance, 0)) DESC,
                  il.id DESC
                LIMIT 1
            ) il ON TRUE

            LEFT JOIN product_product  pp ON pp.id = rl.product_id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pc ON pc.id = pt.categ_id
            LEFT JOIN product_brand    pb ON pb.id = pt.brand_id

            LEFT JOIN res_partner p  ON p.id  = rl.partner_id
            LEFT JOIN res_partner ps ON ps.id = rl.ship_partner_id

            LEFT JOIN res_partner sp ON sp.id = rl.salesman_partner_id
            {partner_name_joins_sql}
            LEFT JOIN rma_return_reason rr ON rr.id = rl.return_reason_id

            LEFT JOIN product_packaging pk_inv ON pk_inv.id = il.product_packaging_id
            LEFT JOIN product_packaging pk_so  ON pk_so.id  = rl.so_packaging_id

            -- أحدث Picking خاص بالاستلام (Incoming) لهذا الـ RMA
            LEFT JOIN LATERAL (
                SELECT sp.*
                FROM stock_picking sp
                JOIN stock_move sm ON sm.picking_id = sp.id
                JOIN stock_picking_type spt2 ON spt2.id = sp.picking_type_id
                WHERE sp.origin = rl.rma_name
                  AND (rl.product_id IS NULL OR sm.product_id = rl.product_id)
                  AND sp.state = 'done'
                  AND spt2.code = 'incoming'
                ORDER BY sp.date_done DESC NULLS LAST, sp.id DESC
                LIMIT 1
            ) sp_rma ON TRUE

            ORDER BY rl.rma_date, rl.rma_id, rl.rma_line_id
        """

        self.env.cr.execute(rma_sql, tuple(rma_params))

        rma_title_fmt = workbook.add_format(
            {'bold': True, 'font_size': 14, 'bg_color': '#5B9BD5', 'font_color': 'white', 'align': 'center'})
        rma_header_format = workbook.add_format(
            {'bold': True, 'bg_color': '#FFE699', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        rma_header_written = False

        for r in dictfetchmany(self.env.cr, FETCH_BATCH):
            if not rma_header_written:
                sheet.write(row, 0, "RMA / Credit Notes", rma_title_fmt)
                row += 1
                rma_headers = [h.replace('SO_', 'RMA_') for h in headers]
                for i, h in enumerate(rma_headers):
                    sheet.write(row, i, h, rma_header_format)
                row += 1
                rma_header_written = True

            inv_unit_qty = r.get('inv_unit_qty') if r.get('inv_unit_qty') is not None else 0.0
            inv_unit_price = r.get('inv_unit_price') if r.get('inv_unit_price') is not None else 0.0
            inv_discount = r.get('inv_discount') if r.get('inv_discount') is not None else 0.0
            inv_pack_qty = r.get('inv_packaging_qty') if r.get('inv_packaging_qty') is not None else 0.0
            inv_pack_price = r.get('inv_packaging_price') if r.get('inv_packaging_price') is not None else 0.0
            inv_packaging_name = r.get('inv_packaging_name') or ''

            inv_gross_amount = inv_unit_price * inv_unit_qty
            inv_discount_amount = inv_unit_price * inv_unit_qty * (inv_discount / 100.0)

            inv_sub_use = (r.get('inv_price_subtotal') or 0.0)
            inv_tot_use = (r.get('inv_price_total') or 0.0)
            inv_vat_use = max(inv_tot_use - inv_sub_use, 0.0)

            excise_tax_val = r.get('inv_excise_tax') or 0.0

            rma_unit_qty = r.get('rma_so_unit_qty') or 0.0
            rma_unit_price = r.get('so_unit_price') or 0.0
            rma_total_after = r.get('line_total') or 0.0
            rma_vat_amount = r.get('rma_amount_tax') if r.get('rma_amount_tax') is not None else 0.0

            rma_packaging_name = r.get('so_packaging_name') or ''
            rma_pack_qty = r.get('so_packaging_qty') if r.get('so_packaging_qty') is not None else 0.0
            rma_pack_price = r.get('so_packaging_price') if r.get('so_packaging_price') is not None else 0.0

            return_reason_label = safe_json(r.get('return_reason_name_jsonb'))
            rma_day = r['rma_date'].strftime('%Y-%m-%d') if r.get('rma_date') else ''
            inv_day = r['inv_date'].strftime('%Y-%m-%d') if r.get('inv_date') else ''

            EPS = 1e-6
            has_aml = bool(r.get('il_product_id'))
            inv_amount_for_sign = inv_sub_use if abs(inv_sub_use) > EPS else inv_tot_use
            is_discount = has_aml and (inv_amount_for_sign < -EPS)

            def _absf(v):
                try:
                    return abs(float(v or 0.0))
                except Exception:
                    return 0.0

            rma_unit_qty = _absf(rma_unit_qty)
            rma_unit_price = _absf(rma_unit_price)
            rma_total_after = _absf(rma_total_after)
            rma_vat_amount = _absf(rma_vat_amount)
            rma_pack_qty = _absf(rma_pack_qty)
            rma_pack_price = _absf(rma_pack_price)
            rma_subtotal = max(rma_total_after - rma_vat_amount, 0.0)

            sign_rma = 1 if is_discount else -1
            rma_unit_qty *= sign_rma
            rma_unit_price *= sign_rma
            rma_total_after *= sign_rma
            rma_vat_amount *= sign_rma
            rma_subtotal *= sign_rma
            rma_pack_qty *= sign_rma
            rma_pack_price *= sign_rma

            sign_inv = -1
            inv_unit_qty *= sign_inv
            inv_pack_qty *= sign_inv
            inv_unit_price *= sign_inv
            inv_gross_amount *= sign_inv
            inv_discount_amount *= sign_inv
            inv_sub_use *= sign_inv
            inv_tot_use *= sign_inv
            inv_vat_use *= sign_inv
            excise_tax_val *= sign_inv
            inv_discount *= sign_inv

            _row_vals = [
                rma_day,
                r.get('rma_name') or '',
                r.get('partner_name') or '',
                r.get('customer_code') or '',
                r.get('channel_name') or '',
                r.get('outlet_class_name') or '',
                r.get('sub_class_name') or '',
                r.get('customer_type') or '',
                r.get('customer_group_id') or '',
                r.get('outlet_code') or '',
                r.get('ship_display_name') or '',
                r.get('sub_channel_name') or '',
                r.get('external_ref') or '',
                safe_json(r.get('ship_site_number') or ''),  # Ship to Site من partner_shipping فقط
                '',  # Customer Po Reference
                r.get('salesman_name') or '',
                rma_day,
                r.get('product_name') or '',
                r.get('default_code') or '',
                r.get('category_name') or '',
                r.get('brand_name') or '',
                r.get('division') or '',

                rma_packaging_name,
                rma_pack_qty,
                rma_pack_price,

                inv_packaging_name,
                inv_pack_qty,
                inv_pack_price,

                rma_unit_qty,
                inv_unit_qty,
                rma_unit_price,
                inv_unit_price,

                '',  # Delivered Qty
                '',  # Invoiced Qty
                '',  # Cost
                excise_tax_val,

                inv_discount,
                inv_discount_amount,
                inv_gross_amount,

                rma_subtotal,
                rma_vat_amount,
                rma_total_after,

                inv_sub_use,
                inv_vat_use,
                inv_tot_use,

                r.get('rma_state') or '',                           # Sales Order Status
                ('Delivered' if r.get('rma_delivery_number') else 'Pending'),  # Delivery Status
                r.get('rma_delivery_number') or '',                 # Delivery Number
                r.get('rma_delivery_date') or '',                   # Delivery Date (sml.date)
                (r.get('inv_state') or ''),                         # Invoice Status (SO)
                (r.get('inv_name') or 'No Invoice'),
                inv_day,
                r.get('journal_name') or '',
                (r.get('inv_state') or ''),                         # Invoice State
                (payment_state_selection.get(r.get('payment_state'), r.get('payment_state') or '')),
                safe_json(r.get('return_reason_name_jsonb')),
                r.get('rma_state') or ''
            ]
            sheet.write_row(row, 0, _sanitize_row(_row_vals))
            row += 1

        # ===== سطر الفترات =====
        invoice_date_from_local = fields.Datetime.context_timestamp(self, self.invoice_date_from) if self.invoice_date_from else None
        invoice_date_to_local   = fields.Datetime.context_timestamp(self, self.invoice_date_to) if self.invoice_date_to else None
        period_row = (
            f"Sales Order Period: {self.date_from.strftime('%Y-%m-%d') if self.date_from else 'N/A'} to "
            f"{self.date_to.strftime('%Y-%m-%d') if self.date_to else 'N/A'}    |    "
            f"Invoice Period: {invoice_date_from_local.strftime('%Y-%m-%d') if invoice_date_from_local else 'N/A'} to "
            f"{invoice_date_to_local.strftime('%Y-%m-%d') if invoice_date_to_local else 'N/A'}"
        )
        sheet.write(row, 0, period_row, period_format)

        # ===== إنهاء الملف المؤقّت ورفعه للحقل =====
        workbook.close()
        with open(tmp_path, 'rb') as f:
            self.file_data = base64.b64encode(f.read())
        self.file_name = "sales_order_and_credit_notes_report.xlsx"
        for _ in range(10):
            try:
                os.remove(tmp_path)
                break
            except PermissionError:
                pytime.sleep(0.2)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sales.order.rma.report.delivery',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }