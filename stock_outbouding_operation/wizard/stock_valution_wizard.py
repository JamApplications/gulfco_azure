from datetime import timedelta
from odoo import models, fields, api,tools
from odoo.exceptions import ValidationError
import base64
import io
import xlsxwriter
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from datetime import timedelta
import base64
import io
import xlsxwriter
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from pytz import timezone, UTC


class StockValuationWizard(models.TransientModel):
    _name = 'stock.valuation.wizard'
    _description = 'Stock Valuation Report Wizard'

    location_ids = fields.Many2many(
        'stock.location',
        string="Location",
        help="Leave empty to include all locations"
    )
    brand_ids = fields.Many2many(
        'product.brand',
        string="Brand",
        help="Leave empty to include all brands"
    )
    category_ids = fields.Many2many(
        'product.category',
        string="Product Category",
        help="Leave empty to include all categories"
    )
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
    date_from = fields.Datetime(string="Date From", required=True)
    date_to = fields.Datetime(string="Date To", required=True)
    all_locations = fields.Boolean(string="All Locations", default=True)
    all_brands = fields.Boolean(string="All Brands", default=True)
    all_categories = fields.Boolean(string="All Categories", default=True)
    all_warehouse = fields.Boolean(string="All Warehouse", default=True)

    def _get_domain_filters(self):
        domain = " WHERE 1=1 "

        if not self.all_locations and self.location_ids:
            ids = tuple(self.location_ids.ids)
            if len(ids) == 1:
                domain += f" AND quant.location_id = {ids[0]}"
            else:
                domain += f" AND quant.location_id IN {ids}"

        if not self.all_categories and self.category_ids:
            ids = tuple(self.category_ids.ids)
            if len(ids) == 1:
                domain += f" AND prod.categ_id = {ids[0]}"
            else:
                domain += f" AND prod.categ_id IN {ids}"

        if not self.all_brands and self.brand_ids:
            ids = tuple(self.brand_ids.ids)
            if len(ids) == 1:
                domain += f" AND prod.brand_id = {ids[0]}"
            else:
                domain += f" AND prod.brand_id IN {ids}"

        if not self.all_warehouse and self.warehouse_ids:
            ids = tuple(self.warehouse_ids.ids)
            if len(ids) == 1:
                domain += f" AND sl.warehouse_id = {ids[0]}"
            else:
                domain += f" AND sl.warehouse_id IN {ids}"

        return domain

    def _get_domain_location_warehouse_filters(self):
        domain = ""
        if not self.all_locations and self.location_ids:
            ids = tuple(self.location_ids.ids)
            if len(ids) == 1:
                domain += f" AND sl.id = {ids[0]}"
            else:
                domain += f" AND sl.id IN {ids}"
        if not self.all_warehouse and self.warehouse_ids:
            ids = tuple(self.warehouse_ids.ids)
            if len(ids) == 1:
                domain += f" AND sl.warehouse_id = {ids[0]}"
            else:
                domain += f" AND sl.warehouse_id IN {ids}"
        return domain

    def _get_domain_arrival_filters(self):
        domain = ""
        if not self.all_locations and self.location_ids:
            ids = tuple(self.location_ids.ids)
            if len(ids) == 1:
                domain += f" AND dest.id = {ids[0]}"
            else:
                domain += f" AND dest.id IN {ids}"
        if not self.all_warehouse and self.warehouse_ids:
            ids = tuple(self.warehouse_ids.ids)
            if len(ids) == 1:
                domain += f" AND dest.warehouse_id = {ids[0]}"
            else:
                domain += f" AND dest.warehouse_id IN {ids}"
        return domain

    def _get_utc_datetime(self, dt):
        """Convert user timezone datetime to UTC string (for SQL)."""
        if not dt:
            return None
        # user_tz = self.env.user.tz or 'UTC'
        user_tz = 'UTC'
        local = timezone(user_tz).localize(dt.replace(tzinfo=None))
        return local.astimezone(UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def action_print_report(self):
        if not self.all_warehouse and not self.warehouse_ids:
            raise ValidationError("Please select a Warehouse or enable 'All Warehouse'.")
        if not self.all_locations and not self.location_ids:
            raise ValidationError("Please select a Location or enable 'All Locations'.")
        if not self.all_brands and not self.brand_ids:
            raise ValidationError("Please select a Brand or enable 'All Brands'.")
        if not self.all_categories and not self.category_ids:
            raise ValidationError("Please select a Category or enable 'All Categories'.")

        cr = self.env.cr
        domain_sql = self._get_domain_filters()
        location_warehouse_domain_sql = self._get_domain_location_warehouse_filters()
        arrival_gross_domain_sql = self._get_domain_arrival_filters()

        date_from = self._get_utc_datetime(self.date_from)
        date_to = self._get_utc_datetime(self.date_to)

        # 🔹 Opening stock (till date_from)
        cr.execute(f"""
            SELECT sml.product_id,
                   SUM(CASE WHEN sml.location_dest_id IN (
                       SELECT id FROM stock_location WHERE usage='internal'
                   ) THEN sml.quantity ELSE 0 END) -
                   SUM(CASE WHEN sml.location_id IN (
                       SELECT id FROM stock_location WHERE usage='internal'
                   ) THEN sml.quantity ELSE 0 END) AS opening_stock
            FROM stock_move_line sml
            JOIN product_product pp ON pp.id = sml.product_id
            JOIN product_template prod ON prod.id = pp.product_tmpl_id
            JOIN stock_location sl ON sl.id = sml.location_id
            JOIN stock_location sld ON sld.id = sml.location_dest_id  and (sld.is_saleable_location ='true' or sld.is_saleable_location ='true')
            WHERE sml.state = 'done' AND sml.date <= %s AND sml.expiration_date >= %s
            {location_warehouse_domain_sql}
            GROUP BY sml.product_id
        """, [date_from, date_from])
        opening_dict = dict(cr.fetchall())

        # 🔹 Arrivals (supplier → internal)
        cr.execute(f"""
            SELECT sml.product_id, SUM(sml.quantity)
            FROM stock_move_line sml
            JOIN stock_move sm ON sm.id = sml.move_id 
            JOIN stock_location src ON src.id = sml.location_id
            JOIN stock_location dest ON dest.id = sml.location_dest_id
            WHERE sml.state='done'
              AND src.usage='supplier'
              AND sm.purchase_line_id IS NOT NULL
              AND sml.date BETWEEN %s AND %s 
            {arrival_gross_domain_sql}
            GROUP BY sml.product_id
        """, [date_from, date_to])
        arrivals_dict = dict(cr.fetchall())

        # 🔹 Gross Sales (internal → customer)
        cr.execute(f"""
            SELECT sml.product_id, SUM(sml.quantity)
            FROM stock_move_line sml
            JOIN stock_location dest ON dest.id = sml.location_dest_id
            JOIN stock_location src ON src.id = sml.location_id
            WHERE sml.state='done'
              AND src.usage='internal'
              AND dest.usage='customer'
              AND sml.date BETWEEN %s AND %s
            {arrival_gross_domain_sql}
            GROUP BY sml.product_id
        """, [date_from, date_to])
        gross_sales_dict = dict(cr.fetchall())

        # 🔹 Net Sales (Gross - Returns) → if you need net separately
        # cr.execute(f"""
        #     SELECT sml.product_id,
        #            SUM(CASE WHEN src.usage='internal' AND dest.usage='customer' THEN sml.quantity ELSE 0 END) -
        #            SUM(CASE WHEN src.usage='customer' AND dest.usage='internal' THEN sml.quantity ELSE 0 END) AS net_sales
        #     FROM stock_move_line sml
        #     JOIN stock_location src ON src.id = sml.location_id
        #     JOIN stock_location dest ON dest.id = sml.location_dest_id
        #     WHERE sml.state='done'
        #       AND sml.date BETWEEN %s AND %s
        #     {arrival_gross_domain_sql}
        #     GROUP BY sml.product_id
        # """, [date_from, date_to])
        # net_sales_dict = dict(cr.fetchall())


        # cr.execute("""
        #     SELECT lines.product_id,
        #            SUM(CASE WHEN pt.name = 'GOOD' THEN lines.product_uom_qty ELSE 0 END) AS rma_sellable,
        #            SUM(CASE WHEN pt.name IS NULL OR pt.name != 'GOOD' THEN lines.product_uom_qty ELSE 0 END) AS rma_non_sellable
        #     FROM (
        #             -- rma.line
        #             SELECT rl.product_id, rl.product_uom_qty, rl.quant_package_id, rma.state
        #             FROM rma_line rl
        #             JOIN rma ON rma.id = rl.rma_id
        #             WHERE rma.state IN ('refunded','received')
        #             AND rma.date BETWEEN %s AND %s
        #
        #             UNION ALL
        #
        #             SELECT rpl.product_id, rpl.product_uom_qty, rpl.quant_package_id, rma.state
        #             FROM rma_product_line rpl
        #             JOIN rma ON rma.id = rpl.rma_id
        #             WHERE rma.state IN ('refunded','received')
        #             AND rma.date BETWEEN %s AND %s
        #     ) AS lines
        #     LEFT JOIN stock_quant_package sqp ON sqp.id = lines.quant_package_id
        #     LEFT JOIN stock_package_type pt ON pt.id = sqp.package_type_id
        #     GROUP BY lines.product_id
        # """, [self.date_from, self.date_to, self.date_from, self.date_to])

        # without return reason

        # cr.execute("""
        #     SELECT
        #         lines.product_id,
        #         SUM(CASE WHEN lines.is_saleable = TRUE THEN lines.quantity ELSE 0 END) AS rma_sellable,
        #         SUM(CASE WHEN lines.is_not_saleable = TRUE THEN lines.quantity ELSE 0 END) AS rma_non_sellable
        #     FROM (
        #         SELECT
        #             spml.product_id,
        #             spml.quantity,
        #             spml.result_package_id,
        #             slt.is_saleable,
        #             slt.is_not_saleable
        #         FROM rma rm
        #         LEFT JOIN stock_move sm ON sm.id = rm.reception_move_id
        #         LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
        #         LEFT JOIN stock_move spm ON spm.picking_id = sp.id
        #         LEFT JOIN stock_move_line spml ON spml.move_id = spm.id
        #         LEFT JOIN stock_quant_package sqp ON sqp.id = spml.result_package_id
        #         LEFT JOIN stock_location_tag slt ON slt.id = sqp.tag_id
        #         WHERE rm.state IN ('refunded','received')
        #           AND rm.date BETWEEN %s AND %s
        #     ) AS lines
        #     GROUP BY lines.product_id
        # """, [self.date_from, self.date_to])

        # with return reason

        # cr.execute("""
        #         SELECT
        #         lines.product_id,
        #         SUM(
        #             CASE
        #                 WHEN lines.is_saleable = TRUE
        #                      OR lines.reason_is_saleable = TRUE
        #                 THEN lines.quantity
        #                 ELSE 0
        #             END
        #         ) AS rma_sellable,
        #         SUM(
        #             CASE
        #                 WHEN (lines.is_not_saleable = TRUE OR lines.reason_is_saleable = FALSE)
        #                     THEN  lines.quantity
        #                 ELSE 0
        #             END
        #         ) AS rma_non_sellable,
        #         SUM(
        #             CASE
        #                 WHEN lines.is_saleable IS NULL
        #                      AND lines.reason_is_saleable IS NULL
        #                      AND lines.is_not_saleable IS NULL
        #                 THEN lines.quantity
        #                 ELSE 0
        #             END
        #         ) AS rma_undefine
        #     FROM (
        #         SELECT
        #             spml.product_id,
        #             spml.quantity,
        #             spml.result_package_id,
        #             slt.is_saleable,
        #             slt.is_not_saleable,
        #             rrr.is_salable AS reason_is_saleable
        #         FROM rma rm
        #         LEFT JOIN stock_move sm
        #                ON sm.id = rm.reception_move_id
        #         LEFT JOIN stock_picking sp
        #                ON sp.id = sm.picking_id
        #         LEFT JOIN stock_move spm
        #                ON spm.picking_id = sp.id
        #         LEFT JOIN stock_move_line spml
        #                ON spml.move_id = spm.id
        #         LEFT JOIN stock_quant_package sqp
        #                ON sqp.id = spml.result_package_id
        #         LEFT JOIN stock_location_tag slt
        #                ON slt.id = sqp.tag_id
        #         LEFT JOIN crm_team ct
        #                ON slt.id = rm.crm_team_id
        #         LEFT JOIN rma_return_reason r rr
        #                ON rrr.id = sm.return_reason_id
        #         LEFT JOIN stock_location sl
        #                ON sl.id = spml.location_id
        #         WHERE rm.state IN ('refunded','received')
        #           AND spml.date BETWEEN %s AND %s AND sl.usage in ('customer','supplier')
        #     ) AS lines
        #     GROUP BY lines.product_id;
        # """, [date_from, date_to])
        #
        # rma_dict = {r[0]: (r[1], r[2],r[3]) for r in cr.fetchall()}

        cr.execute("""
            SELECT
                lines.product_id,
                SUM(
                    CASE 
                        -- VAN group → use reason_is_saleable from stock_move
                        WHEN lines.location_group = 'van' AND lines.reason_is_saleable = TRUE
                        THEN lines.quantity

                        -- WH group → use package tag from stock_move_line
                        WHEN lines.location_group = 'wh' AND lines.is_saleable = TRUE
                        THEN lines.quantity
                        ELSE 0
                    END
                ) AS rma_sellable,

                SUM(
                    CASE 
                        -- VAN group → reason is not saleable
                        WHEN lines.location_group = 'van' AND lines.reason_is_saleable = FALSE
                        THEN lines.quantity

                        -- WH group → package says not saleable
                        WHEN lines.location_group = 'wh' AND lines.is_not_saleable = TRUE
                        THEN lines.quantity
                        ELSE 0
                    END
                ) AS rma_non_sellable,

                SUM(
                    CASE 
                        -- VAN: no return_reason_id → Undefine
                        WHEN lines.location_group = 'van' 
                             AND lines.reason_is_saleable IS NULL
                        THEN lines.quantity
        
                        -- WH: no package → Undefine
                        WHEN lines.location_group = 'wh' 
                             AND lines.result_package_id IS NULL
                        THEN lines.quantity
        
                        -- WH: package exists but no flags set → Undefine
                        WHEN lines.location_group = 'wh' 
                             AND lines.result_package_id IS NOT NULL
                             AND (lines.is_saleable IS NULL OR lines.is_saleable = FALSE)
                             AND (lines.is_not_saleable IS NULL OR lines.is_not_saleable = FALSE)
                        THEN lines.quantity
        
                        ELSE 0
                    END
                ) AS rma_undefine

            FROM (
                SELECT
                    spml.product_id,
                    spml.quantity,
                    spml.result_package_id,
                    slt.is_saleable,
                    slt.is_not_saleable,
                    rrr.is_salable AS reason_is_saleable,
                    sldest.location_group
                FROM stock_move_line spml
                LEFT JOIN stock_move sm 
                       ON sm.id = spml.move_id
                LEFT JOIN stock_picking sp 
                       ON sp.id = sm.picking_id
                LEFT JOIN stock_quant_package sqp 
                       ON sqp.id = spml.result_package_id
                LEFT JOIN stock_location_tag slt 
                       ON slt.id = sqp.tag_id
                LEFT JOIN rma_return_reason rrr 
                       ON rrr.id = sm.return_reason_id 
                LEFT JOIN stock_location sldest
                       ON sldest.id = sp.location_dest_id   -- 🔑 use picking destination location
                LEFT JOIN stock_location slde
                       ON slde.id = sp.location_id
                WHERE spml.state = 'done' 
                  AND sp.trx_type = 'return_collection' 
                  AND spml.date BETWEEN %s AND %s 
                  AND slde.usage = 'customer' 
            ) AS lines
            GROUP BY lines.product_id;
        """, [date_from, date_to])

        rma_dict = {r[0]: (r[1], r[2],r[3]) for r in cr.fetchall()}


        # # 🔹 RMA Sellable / Non-Sellable
        # cr.execute("""
        #     SELECT sm.product_id,
        #            SUM(CASE WHEN sl.is_saleable_location = true THEN sm.product_uom_qty ELSE 0 END) AS rma_sellable,
        #            SUM(CASE WHEN sl.is_saleable_location = false THEN sm.product_uom_qty ELSE 0 END) AS rma_non_sellable
        #     FROM rma r
        #     JOIN stock_picking sp ON r.reception_move_id = sp.id
        #     JOIN stock_move sm ON sm.picking_id = sp.id
        #     JOIN stock_location sl ON sm.location_dest_id = sl.id
        #     WHERE r.state NOT IN ('refunded','submit','cancelled')
        #       AND sm.date BETWEEN %s AND %s
        #     GROUP BY sm.product_id
        # """, [self.date_from, self.date_to])
        # rma_dict = {r[0]: (r[1], r[2]) for r in cr.fetchall()}

        # 🔹 Expired stock
        cr.execute(f"""
            SELECT sml.product_id, SUM(sml.quantity)
            FROM stock_move_line sml
            JOIN stock_location sl ON sl.id = sml.location_dest_id
            WHERE sl.usage = 'inventory' AND sml.date BETWEEN %s AND %s AND sml.state='done'
            {location_warehouse_domain_sql}
            GROUP BY sml.product_id
        """, [date_from,date_to])
        expired_dict = dict(cr.fetchall())

        # 🔹 Near Expiry (next 90 days)
        expire_date_after_90 = self.date_to + timedelta(days=90)
        expire_date_after_90 = self._get_utc_datetime(expire_date_after_90)
        cr.execute(f"""
            SELECT quant.product_id, SUM(quant.quantity)
            FROM stock_quant quant
            JOIN stock_location sl ON sl.id = quant.location_id
            WHERE quant.expiration_date <= %s
            {location_warehouse_domain_sql}
            GROUP BY quant.product_id
        """, [expire_date_after_90])
        near_expiry_dict = dict(cr.fetchall())

        # 🔹 Products considered
        cr.execute(f"""
            SELECT DISTINCT quant.product_id
            FROM stock_quant quant
            JOIN product_product pp ON pp.id = quant.product_id
            JOIN product_template prod ON prod.id = pp.product_tmpl_id
            JOIN stock_location sl ON sl.id = quant.location_id
            {domain_sql}
        """)
        product_ids = [r[0] for r in cr.fetchall()]
        products = self.env['product.product'].browse(product_ids)

        # 🔹 Closing stock (till date_to and expiration date till date to)
        cr.execute(f"""
             SELECT sml.product_id,
                    SUM(CASE WHEN sml.location_dest_id IN (
                        SELECT id FROM stock_location WHERE usage='internal'
                    ) THEN sml.quantity ELSE 0 END) -
                    SUM(CASE WHEN sml.location_id IN (
                        SELECT id FROM stock_location WHERE usage='internal'
                    ) THEN sml.quantity ELSE 0 END) AS closing_stock
             FROM stock_move_line sml
             JOIN product_product pp ON pp.id = sml.product_id
             JOIN product_template prod ON prod.id = pp.product_tmpl_id
             JOIN stock_location sl ON sl.id = sml.location_id
             WHERE sml.state = 'done' AND sml.date <= %s AND sml.expiration_date >= %s
             {location_warehouse_domain_sql}
             GROUP BY sml.product_id
         """, [date_to, date_to])
        closing_dict = dict(cr.fetchall())

        # 🔹 Generate XLSX
        headers = [
            "Product code",
            "Description",
            "Opening Stock\nWithout Damages and Expiries",
            "Arrivals (Shipment Receipt)",
            "RMA Sellable",
            "RMA Non Sellable",
            "RMA Not Define",
            "Gross Sales",
            "Net Sales",
            "Closing Stock\nWithout Damages and Expires)",
            "Near Expiry Stock 90 days",
            "Stocks Expired in Warehouse\n"
        ]
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("SSR Report")

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        normal_format = workbook.add_format({'border': 1})

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 25)

        row = 1
        for product in products:
            opening = opening_dict.get(product.id, 0.0)
            arrivals = arrivals_dict.get(product.id, 0.0)
            gross_sales = gross_sales_dict.get(product.id, 0.0)
            # net_sales = net_sales_dict.get(product.id, gross_sales)  # fallback gross if no returns
            rma_sellable, rma_non_sellable,rma_undefine = rma_dict.get(product.id, (0.0, 0.0,0.0))
            net_sales = gross_sales - rma_sellable - rma_non_sellable - rma_undefine
            near_expiry = near_expiry_dict.get(product.id, 0.0)
            expired = expired_dict.get(product.id, 0.0)

            # closing = opening + arrivals - gross_sales + rma_sellable  # classic closing formula
            closing = closing_dict.get(product.id, 0.0)

            sheet.write(row, 0, product.default_code or "", normal_format)
            sheet.write(row, 1, product.name, normal_format)
            sheet.write(row, 2, opening, normal_format)
            sheet.write(row, 3, arrivals, normal_format)
            sheet.write(row, 4, rma_sellable, normal_format)
            sheet.write(row, 5, rma_non_sellable, normal_format)
            sheet.write(row, 6, rma_undefine, normal_format)
            sheet.write(row, 7, gross_sales, normal_format)
            sheet.write(row, 8, net_sales, normal_format)
            sheet.write(row, 9, closing, normal_format)
            sheet.write(row, 10, near_expiry, normal_format)
            sheet.write(row, 11, expired, normal_format)
            row += 1

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        attachment = self.env['ir.attachment'].create({
            'name': 'SSR_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
