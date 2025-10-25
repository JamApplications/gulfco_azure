from odoo import api, fields, models, tools

# ==========================================================
# TODO — map these to your actual customization names/fields
# ==========================================================
RMA_TABLE = 'rma'          # e.g., 'mw_rma' or your actual model's _table
RMA_LINE_TABLE = 'rma_product_line' # e.g., 'mw_rma_line'
# JSON fields that may live on SOL/AML/RMA lines holding location/department/channel
JSON_KEY_ON_SOL = 'analytic_distribution'          # jsonb on sale_order_line (if any). Use real field name or keep NULL
JSON_KEY_ON_AML = 'analytic_distribution'          # jsonb on account_move_line (if any). Use real field name or keep NULL
JSON_KEY_ON_RMAL = 'analytic_distribution'         # jsonb on rma line (if any). Use real field name or keep NULL
# Custom fields
SALE_SALESPERSON_FIELD = 'assign_to'  # res.partner m2o on sale.order
SALE_STAFF_CODE_FIELD = 'worker_code'      # field on res.partner for staff number
PARTNER_CODE_FIELD = 'customer_code'       # your customer code on res.partner
ORDER_SOURCE_FIELD = 'order_creation_source'  # on sale.order if you have it
SHIPPING_SITE_FIELD = 'site_number'        # on partner shipping address (if exists)
# Packaging fields on invoice/rma lines
AML_PACKAGING_ID_FIELD = 'product_packaging_id'    # if exists on AML
AML_PACKAGING_QTY_FIELD = 'product_packaging_qty'  # if exists on AML
RMAL_PACKAGING_ID_FIELD = 'product_packaging_id'   # on RMA line
RMAL_PACKAGING_QTY_FIELD = 'product_packaging_qty' # on RMA line
import logging

_logger = logging.getLogger(__name__)
class MwSalesRmaReport(models.Model):
    _name = 'mw.sales.rma.report'
    _description = 'Unified Sales & RMA Report (SQL View)'
    _auto = False
    _rec_name = 'order_no'

    # --- identifiers & typing ---
    rec_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('rma', 'RMA Return'),
    ], string='Record Type', index=True)

    company_id = fields.Many2one('res.company', string='Company', index=True)
    currency_id = fields.Many2one('res.currency', string='Currency')

    # --- commercial heads ---
    sales_man_id = fields.Many2one('res.partner', string='Sales Man', index=True)
    sales_man = fields.Char(string='Sales Man (Name)')
    staff_number = fields.Char(string='Staff Number')

    invoice_date = fields.Date(string='Invoice Date', index=True)
    invoice_no = fields.Char(string='Invoice No', index=True)
    invoice_line_number = fields.Char(string='Invoice Line Number')

    order_id = fields.Many2one('sale.order', string='Order')
    order_no = fields.Char(string='Order No', index=True)

    branch = fields.Char(string='Branch')
    channel = fields.Char(string='Channel')
    sub_channel = fields.Char(string='Sub Channel')

    customer_id = fields.Many2one('res.partner', string='Customer', index=True)
    customer_code = fields.Char(string='Customer Code')
    customer_name = fields.Char(string='Customer Name')

    shipping_site_number = fields.Char(string='Ship To Site Number')
    ship_address1 = fields.Char(string='Address1')
    ship_address2 = fields.Char(string='Address2')
    ship_city = fields.Char(string='City')
    ship_state = fields.Char(string='State')

    payment_term = fields.Char(string='Payment Term')
    tax_registration = fields.Char(string='Tax Registration Number')
    customer_po = fields.Char(string='Customer PO Reference')
    order_source = fields.Char(string='Order Source')

    # --- product ---
    product_id = fields.Many2one('product.product', string='Product', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    item_code = fields.Char(string='Item Code')
    description = fields.Char(string='Description')
    product_category = fields.Char(string='Product Category')
    product_category_id = fields.Many2one("product.category",string='Product Category')

    # --- uom/qty/packaging ---
    trx_uom = fields.Char(string='Trx UoM (PACKAGE)')
    trx_uom_id = fields.Many2one("product.packaging", string='Trx UoM (PACKAGE)')
    package_qty_invoiced = fields.Float(string='Package Qty Invoiced')
    package_qty_return = fields.Float(string='Package Qty Return')
    package_conv_to_each = fields.Float(string='Item Conversion in EAC for the PACKAGE USED')

    primary_qty = fields.Float(string='Primary Qty')
    primary_return_qty = fields.Float(string='Primary Return Qty')
    primary_uom = fields.Char(string='Primary UoM')
    primary_uom_id = fields.Many2one("uom.uom", string='Primary UoM')

    unit_selling_price = fields.Monetary(string='Unit Selling Price')
    unit_cost = fields.Monetary(string='Unit Cost')
    total_cost = fields.Monetary(string='Total Cost')
    line_total_selling = fields.Monetary(string='Line Total Selling Price')

    # --- accounting/analytics ---
    analytic_location = fields.Char(string='Analytical Location')
    analytic_department = fields.Char(string='Analytical Department')
    analytic_channel = fields.Char(string='Analytical Channel')
    chart_of_account = fields.Char(string='Chart of Account')
    analytic_department_id = fields.Many2one("account.analytic.account")
    analytic_channel_id = fields.Many2one("account.analytic.account")
    # --- returns metadata ---
    return_reason = fields.Char(string='Return Reason')
    return_type = fields.Char(string='Return Type')
    return_caused_by = fields.Char(string='Return Caused By')

    # --- logistics ---
    picking_id = fields.Many2one('stock.picking', string='Delivery / IN Document', index=True)
    delivery_name = fields.Char(string='DELIVERY / IN Document')
    location_text = fields.Char(string='LOCATION')

    remarks = fields.Char(string='Remarks')

    @api.model
    def _select(self):
        # latest DONE picking per SO for invoice rows
        last_done_picking_sql = (
            "LEFT JOIN LATERAL ("
            "  SELECT sp2.id, sp2.name, sp2.location_dest_id"
            "  FROM stock_picking sp2"
            "  WHERE sp2.sale_id = so.id AND sp2.state = 'done'"
            "  ORDER BY sp2.date_done DESC NULLS LAST"
            "  LIMIT 1"
            ") sp ON TRUE"
        )

        query = f"""
        WITH inv AS (
            SELECT
                aml.id::bigint                                                    AS id,
                'invoice'::text                                                   AS rec_type,
                am.company_id::integer                                            AS company_id,
                am.currency_id::integer                                           AS currency_id,

                am.invoice_date                                                   AS invoice_date,
                am.name::text                                                     AS invoice_no,
                COALESCE(NULLIF(aml.sequence::text, ''), NULLIF(aml.name::text, ''), pt.name::text)
                                                                                  AS invoice_line_number,

                so.id::integer                                                    AS order_id,
                so.name::text                                                     AS order_no,

                so.assign_to::integer                                             AS sales_man_id,
                spn.name::text                                                    AS sales_man,
                spn.worker_code::text                                             AS staff_number,

                rp.id::integer                                                    AS customer_id,
                rp.customer_code::text                                            AS customer_code,
                rp.name::text                                                     AS customer_name,

                ship.site_number::text                                            AS shipping_site_number,
                ship.street::text                                                 AS ship_address1,
                NULLIF(ship.street2::text, '')                                    AS ship_address2,
                ship.city::text                                                   AS ship_city,
                ship.state_id::text                                               AS ship_state,

                pt.id::integer                                                    AS product_tmpl_id,
                pp.id::integer                                                    AS product_id,
                pp.default_code::text                                             AS item_code,
                COALESCE(NULLIF(aml.name::text, ''), pt.name::text)               AS description,
                pc.name::text                                                     AS product_category,
                pc.id::integer                                                    AS product_category_id,

                pkg.name::text                                                    AS trx_uom,
                pkg.id::integer                                                   AS trx_uom_id,
                aml.product_packaging_qty::numeric                                AS package_qty_invoiced,
                NULL::numeric                                                     AS package_qty_return,
                pkg.qty::numeric                                                  AS package_conv_to_each,

                aml.quantity::numeric                                             AS primary_qty,
                NULL::numeric                                                     AS primary_return_qty,
                uom.name::text                                                    AS primary_uom,
                COALESCE(aml.product_uom_id, pt.uom_id)::integer                  AS primary_uom_id,

                aml.price_unit::numeric                                           AS unit_selling_price,
                pt.list_price::numeric                                            AS unit_cost,
                (pt.list_price::numeric * aml.quantity::numeric)                  AS total_cost,
                aml.price_subtotal::numeric                                       AS line_total_selling,

                NULL::text                                                        AS analytic_location,
                aagg.analytic_department::text                                    AS analytic_department,
                aagg.analytic_channel::text                                       AS analytic_channel,
                aagg.analytic_department_id::integer                               AS analytic_department_id,
                aagg.analytic_channel_id::integer                                  AS analytic_channel_id,
                acc.name::text                                                    AS chart_of_account,

                NULL::text                                                        AS return_reason,
                NULL::text                                                        AS return_type,
                NULL::text                                                        AS return_caused_by,

                sp.id::integer                                                    AS picking_id,
                sp.name::text                                                     AS delivery_name,
                NULL::text                                                        AS location_text,

                aml.name::text                                                    AS remarks,

                wh.name::text                                                     AS branch,
                NULL::text                                                        AS channel,
                NULL::text                                                        AS sub_channel,

                so.order_creation_source::text                                    AS order_source,
                so.client_order_ref::text                                         AS customer_po,
                ptm.name::text                                                    AS payment_term,
                rp.vat::text                                                      AS tax_registration

            FROM account_move_line aml
            JOIN account_move am                    ON am.id = aml.move_id
                                                    AND am.state = 'posted'
                                                    AND am.move_type IN ('out_invoice', 'out_refund')
            LEFT JOIN account_account acc           ON acc.id = aml.account_id
            LEFT JOIN product_product pp            ON pp.id = aml.product_id
            LEFT JOIN product_template pt           ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pc           ON pc.id = pt.categ_id
            LEFT JOIN uom_uom uom                   ON uom.id = COALESCE(aml.product_uom_id, pt.uom_id)
            LEFT JOIN product_packaging pkg         ON pkg.id = aml.product_packaging_id

            -- AML -> SOL link
            LEFT JOIN sale_order_line_invoice_rel rel ON rel.invoice_line_id = aml.id
            LEFT JOIN sale_order_line sol              ON sol.id = rel.order_line_id
            LEFT JOIN sale_order so                    ON so.id = sol.order_id
            LEFT JOIN res_partner rp                   ON rp.id = so.partner_id
            LEFT JOIN res_partner ship                 ON ship.id = so.partner_shipping_id
            LEFT JOIN res_partner spn                  ON spn.id = so.assign_to
            LEFT JOIN stock_warehouse wh               ON wh.id = so.warehouse_id
            LEFT JOIN account_payment_term ptm         ON ptm.id = so.payment_term_id

            -- analytics from account_analytic_line (single aggregated row per aml)
            LEFT JOIN LATERAL (
                SELECT
                    string_agg(DISTINCT dep.name::text, ' / ') AS analytic_department,
                    string_agg(DISTINCT ch.name::text,  ' / ') AS analytic_channel,
                    MIN(dep.id)::integer                        AS analytic_department_id,
                    MIN(ch.id)::integer                         AS analytic_channel_id
                FROM account_analytic_line aal
                LEFT JOIN account_analytic_account dep ON dep.id = aal.x_plan2_id
                LEFT JOIN account_analytic_account ch  ON ch.id  = aal.x_plan3_id
                WHERE aal.move_line_id = aml.id
            ) aagg ON TRUE

            {last_done_picking_sql}
        ),
        rma AS (
            SELECT
                (rmal.id + 1000000000)::bigint                                    AS id,
                'rma'::text                                                       AS rec_type,
                rma.company_id::integer                                           AS company_id,
                rma.currency_id::integer                                          AS currency_id,

                rma.date::date                                                    AS invoice_date,
                NULL::text                                                        AS invoice_no,
                NULL::text                                                        AS invoice_line_number,

                so.id::integer                                                    AS order_id,
                so.name::text                                                     AS order_no,

                so.assign_to::integer                                             AS sales_man_id,
                spn.name::text                                                    AS sales_man,
                spn.worker_code::text                                             AS staff_number,

                rp.id::integer                                                    AS customer_id,
                rp.customer_code::text                                            AS customer_code,
                rp.name::text                                                     AS customer_name,

                ship.site_number::text                                            AS shipping_site_number,
                ship.street::text                                                 AS ship_address1,
                NULLIF(ship.street2::text, '')                                    AS ship_address2,
                ship.city::text                                                   AS ship_city,
                ship.state_id::text                                               AS ship_state,

                pt.id::integer                                                    AS product_tmpl_id,
                pp.id::integer                                                    AS product_id,
                pp.default_code::text                                             AS item_code,
                pt.name::text                                                     AS description,
                pc.name::text                                                     AS product_category,
                pc.id::integer                                                    AS product_category_id,

                pkg.name::text                                                    AS trx_uom,
                pkg.id::integer                                                   AS trx_uom_id,         -- ✨ ADDED to match INV
                NULL::numeric                                                     AS package_qty_invoiced,
                rmal.product_packaging_qty::numeric                               AS package_qty_return,
                pkg.qty::numeric                                                  AS package_conv_to_each,

                NULL::numeric                                                     AS primary_qty,
                rmal.product_uom_qty::numeric                                     AS primary_return_qty,
                uom.name::text                                                    AS primary_uom,
                COALESCE(rmal.product_uom_id, pt.uom_id)::integer                 AS primary_uom_id,     -- consistent

                rmal.price_unit::numeric                                          AS unit_selling_price,
                pt.list_price::numeric                                            AS unit_cost,
                (pt.list_price::numeric * rmal.product_uom_qty::numeric)          AS total_cost,
                (rmal.price_unit::numeric * rmal.product_uom_qty::numeric)        AS line_total_selling,

                NULL::text                                                        AS analytic_location,
                NULL::text                                                        AS analytic_department,
                NULL::text                                                        AS analytic_channel,
                NULL::integer                                                     AS analytic_department_id,
                NULL::integer                                                     AS analytic_channel_id,
                NULL::text                                                        AS chart_of_account,

                rr.name::text                                                     AS return_reason,
                rrt.name::text                                                    AS return_type,
                rcb.name::text                                                    AS return_caused_by,

                rma.picking_id::integer                                           AS picking_id,
                sp.name::text                                                     AS delivery_name,
                NULL::text                                                        AS location_text,

                NULL::text                                                        AS remarks,

                wh.name::text                                                     AS branch,
                NULL::text                                                        AS channel,
                NULL::text                                                        AS sub_channel,

                so.order_creation_source::text                                    AS order_source,
                so.client_order_ref::text                                         AS customer_po,
                ptm.name::text                                                    AS payment_term,
                rp.vat::text                                                      AS tax_registration

            FROM rma_product_line rmal
            JOIN rma rma                      ON rma.id = rmal.rma_id AND rma.rma_type = 'base_on_delivery'
            LEFT JOIN stock_picking sp        ON sp.id = rma.picking_id
            LEFT JOIN sale_order so           ON so.name = sp.origin
            LEFT JOIN res_partner rp          ON rp.id = rma.partner_id
            LEFT JOIN res_partner ship        ON ship.id = so.partner_shipping_id
            LEFT JOIN res_partner spn         ON spn.id = so.assign_to
            LEFT JOIN stock_warehouse wh      ON wh.id = so.warehouse_id
            LEFT JOIN account_payment_term ptm ON ptm.id = so.payment_term_id

            LEFT JOIN product_product pp      ON pp.id = rmal.product_id
            LEFT JOIN product_template pt     ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pc     ON pc.id = pt.categ_id
            LEFT JOIN uom_uom uom             ON uom.id = rmal.product_uom_id
            LEFT JOIN product_packaging pkg   ON pkg.id = rmal.product_packaging_id

            LEFT JOIN rma_return_reason rr         ON rr.id = rmal.return_reason_id
            LEFT JOIN rma_return_reason_type rrt   ON rrt.id = rmal.return_reason_type_id
            LEFT JOIN rma_return_caused_config rcb ON rcb.id = rmal.return_caused_by_id
        )
        SELECT * FROM inv
        UNION ALL
        SELECT * FROM rma
        """

        _logger.info("this is my query")
        _logger.info(query)
        _logger.info("end of my query")

        return query

    def init(self):
        """Create the SQL view for mw_sales_rma_report (Odoo 18 style)."""
        # self._table == 'mw_sales_rma_report' derived from _name
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                {self._select()}
            )
        """)

    # Example hook if you opt for a materialized view instead of a plain VIEW
    def _refresh_materialized(self):
        self.env.cr.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mw_sales_rma_report")

