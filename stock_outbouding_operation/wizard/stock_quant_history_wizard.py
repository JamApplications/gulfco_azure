
from odoo import api, fields, models, tools, _
from datetime import datetime, time
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError



class StockQuantHistory(models.TransientModel):
    _name = 'stock.quant.history'
    _description = 'Inventory at Date for Locations'

    inventory_datetime = fields.Datetime(
        string='Inventory at Date',
        required=True,
        default=lambda self: fields.Datetime.now()
    )

    def open_at_date_view(self):
        self.ensure_one()
        action = self.env.ref('stock_outbouding_operation.action_stock_quant_at_date').read()[0]
        action['display_name'] = _("Inventory at Date: %s") % (self.inventory_datetime.strftime('%B %d, %Y'))
        action['domain'] = [('location_id.usage','=','internal'), ('on_hand_qty', '!=', 0)]
        action['context'] = dict(self.env.context, to_date=self.inventory_datetime, )
        action['context'].update({'search_default_internal_loc': 1,
                                  "search_default_groupby_location": 1,
                                  "search_default_groupby_product": 1,
                                  'search_default_groupby_lot': 1,
                                  })

        return action



class StockQuantAtDate(models.Model):
    _name = "stock.quant.at.date"
    _description = "Stock Quant Snapshot At Date (fixed & aggregated on read)"
    _auto = False

    date = fields.Datetime(
        string='Date',
        required=True,
        default=lambda self: fields.Datetime.now()
    )
    company_id = fields.Many2one('res.company', required=True, index=True)
    location_id = fields.Many2one('stock.location', string="Location", index=True)
    product_id = fields.Many2one('product.product', string="Product", index=True)
    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number", aggregator="sum", index=True,)

    package_id = fields.Many2one('stock.quant.package', string="Package")
    owner_id = fields.Many2one('res.partner', string="Owner")

    on_hand = fields.Boolean('On Hand', store=False, search='_search_on_hand')

    def _search_on_hand(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))

        # Get valid locations (same as quants)
        domain_loc = self.env['product.product']._get_domain_locations()[0]

        # Build SQL to find product/location with qty > 0
        self.env.cr.execute("""
            SELECT
                sml.product_id AS product_id,
                sml.location_id AS location_id
            FROM stock_move_line sml
            JOIN stock_location src ON src.id = sml.location_id
            JOIN stock_location dest ON dest.id = sml.location_dest_id
            WHERE src.usage = 'internal' AND src.location_id IS NOT NULL
            GROUP BY  sml.product_id, sml.location_id
            HAVING SUM(sml.quantity) > 0
        """)
        rows = self.env.cr.fetchall()

        if not rows:
            # If nothing in stock, return a domain that never matches
            return [('id', '=', 0)] if value else []

        product_ids = list(set(r[0] for r in rows))
        location_ids = list(set(r[1] for r in rows))

        # Build the domain
        domain = ['&', ('product_id', 'in', product_ids), ('location_id', 'in', location_ids)]

        # Negate if operator/value require it
        if (operator == '!=' and value) or (operator == '=' and not value):
            domain = ['!', *domain]

        return domain



    on_hand_qty = fields.Float("On Hand Qty", digits='Product Unit of Measure')
    reserved_qty = fields.Float("Reserved Qty", default=0.0)
    available_qty = fields.Float("Available Qty", default=0.0 )

    move_date = fields.Datetime("Move Date", readonly=True)

    value = fields.Monetary(
        string="Value",
        currency_field="currency_id",
        readonly=True,
        aggregator="sum",
        compute="_compute_value",
        store=False,
    )

    currency_id = fields.Many2one("res.currency",
                                  default=lambda self: self.env.company.currency_id,
                                  readonly=True)

    avg_cost = fields.Float(
        string="Average Cost",
        currency_field="currency_id",
        compute="_compute_avg_cost",
        aggregator="sum",
        store=False,
    )

    expiration_date = fields.Datetime(
        string="Expiration Date",
        related="lot_id.expiration_date"
    )

    @api.depends('product_id')
    def _compute_avg_cost(self):
        for rec in self:
            rec.avg_cost = rec.product_id.standard_price or 0.0


    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute(f"""
    #         CREATE OR REPLACE VIEW {self._table} AS (
    #             WITH move_contrib AS (
    #                 /* Inbound contribution: +qty to destination location */
    #                 SELECT
    #                     sml.company_id,
    #                     sml.date,
    #                     sml.product_id,
    #                     sml.lot_id,
    #                     sml.package_id,
    #                     sml.owner_id,
    #                     sml.location_dest_id AS location_id,
    #                     CASE
    #                         WHEN sm.state = 'done' THEN sml.quantity
    #                         ELSE 0.0
    #                     END AS qty_delta,
    #                     0.0::numeric AS reserved_delta
    #                 FROM stock_move_line sml
    #                 JOIN stock_move sm ON sm.id = sml.move_id
    #
    #                 UNION ALL
    #
    #                 /* Outbound contribution: -qty from source location */
    #                 SELECT
    #                     sml.company_id,
    #                     sml.date,
    #                     sml.product_id,
    #                     sml.lot_id,
    #                     sml.package_id,
    #                     sml.owner_id,
    #                     sml.location_id AS location_id,
    #                     CASE
    #                         WHEN sm.state = 'done' THEN -sml.quantity
    #                         ELSE 0.0
    #                     END AS qty_delta,
    #                     CASE
    #                         WHEN sm.state IN ('assigned','partially_available') THEN sml.quantity
    #                         ELSE 0.0
    #                     END AS reserved_delta
    #                 FROM stock_move_line sml
    #                 JOIN stock_move sm ON sm.id = sml.move_id
    #             )
    #
    #             SELECT
    #                 ROW_NUMBER() OVER() AS id,
    #                 mc.company_id,
    #                 mc.product_id,
    #                 mc.lot_id,
    #                 mc.package_id,
    #                 mc.owner_id,
    #                 mc.location_id,
    #                 rc.currency_id,
    #                 mc.date AS date,
    #
    #                 /* balances */
    #                 SUM(mc.qty_delta) AS on_hand_qty,
    #                 SUM(mc.reserved_delta) AS reserved_qty,
    #                 SUM(mc.qty_delta) - SUM(mc.reserved_delta) AS available_qty,
    #
    #                 /* valuation */
    #                 COALESCE(MAX(avc.avg_cost), 0.0) * SUM(mc.qty_delta) AS value
    #
    #             FROM move_contrib mc
    #             LEFT JOIN res_company rc ON rc.id = mc.company_id
    #
    #             /* avg cost as of to_date */
    #             LEFT JOIN LATERAL (
    #                 SELECT
    #                     COALESCE(
    #                         SUM(svl.value)::numeric / NULLIF(SUM(svl.quantity), 0),
    #                         0.0
    #                     ) AS avg_cost
    #                 FROM stock_valuation_layer svl
    #                 WHERE svl.product_id = mc.product_id
    #                   AND svl.company_id = mc.company_id
    #                   AND svl.create_date <= (
    #                       CASE
    #                           WHEN current_setting('stock_quant_at_date.to_date', true) IS NOT NULL
    #                           THEN current_setting('stock_quant_at_date.to_date', true)::timestamp
    #                           ELSE now()
    #                       END
    #                   )
    #             ) avc ON TRUE
    #
    #             GROUP BY
    #                 mc.company_id,
    #                 mc.product_id,
    #                 mc.lot_id,
    #                 mc.package_id,
    #                 mc.owner_id,
    #                 mc.location_id,
    #                 rc.currency_id,
    #                 mc.date
    #         )
    #     """)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH move_contrib AS (
                    /* Inbound contribution: +qty to destination location */
                    SELECT
                        sml.company_id,
                        sml.date,
                        sml.product_id,
                        sml.lot_id,
                        sml.package_id,
                        sml.owner_id,
                        sml.location_dest_id AS location_id,
                        CASE
                            WHEN sm.state = 'done' THEN sml.quantity
                            ELSE 0.0
                        END AS qty_delta,
                        0.0::numeric AS reserved_delta
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id

                    UNION ALL

                    /* Outbound contribution: -qty from source location */
                    SELECT
                        sml.company_id,
                        sml.date,
                        sml.product_id,
                        sml.lot_id,
                        sml.package_id,
                        sml.owner_id,
                        sml.location_id AS location_id,
                        CASE
                            WHEN sm.state = 'done' THEN -sml.quantity
                            ELSE 0.0
                        END AS qty_delta,
                        CASE
                            WHEN sm.state IN ('assigned','partially_available') THEN sml.quantity
                            ELSE 0.0
                        END AS reserved_delta
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                )

                SELECT
                    ROW_NUMBER() OVER() AS id,
                    mc.company_id,
                    mc.product_id,
                    mc.lot_id,
                    mc.package_id,
                    mc.owner_id,
                    mc.location_id,
                    rc.currency_id,
                    mc.date AS date,

                    /* balances only */
                    SUM(mc.qty_delta) AS on_hand_qty,
                    SUM(mc.reserved_delta) AS reserved_qty,
                    SUM(mc.qty_delta) - SUM(mc.reserved_delta) AS available_qty

                FROM move_contrib mc
                LEFT JOIN res_company rc ON rc.id = mc.company_id

                GROUP BY
                    mc.company_id,
                    mc.product_id,
                    mc.lot_id,
                    mc.package_id,
                    mc.owner_id,
                    mc.location_id,
                    rc.currency_id,
                    mc.date
            )
        """)

    @api.model
    def _where_calc(self, domain, active_test=True):
        """
        Apply cutoff on per-row move_date and company filter.
        Also sets a session variable so the SQL lateral subquery can read the same to_date.
        """
        query = super()._where_calc(domain, active_test=active_test)

        to_date = self.env.context.get('to_date')
        table = self._table  # "stock_quant_at_date"
        if to_date:
            to_date = self._end_of_day(to_date)

            # Set session variable so the view's lateral subquery can use the same cutoff.
            # SET LOCAL applies for the current transaction / query context.
            # We pass a string timestamp parameter (postgres will accept it).
            self.env.cr.execute(
                "SET LOCAL stock_quant_at_date.to_date = %s",
                (to_date.strftime('%Y-%m-%d %H:%M:%S'),)
            )

            query.add_where(
                self.env.cr.mogrify(f"{table}.date <= %s", (to_date,)).decode()
            )

        company_id = self.env.context.get('force_company') or self.env.company.id
        query.add_where(
            self.env.cr.mogrify(f"{table}.company_id = %s", (company_id,)).decode()
        )
        return query


    def _end_of_day(self, dt):
        """Normalize cutoff to end of day (avoid TZ partial-day issues)."""
        if not dt:
            return fields.Datetime.now()
        if isinstance(dt, str):
            dt = fields.Datetime.from_string(dt)
        return datetime.combine(dt.date(), time(23, 59, 59))

    def _avg_cost_by_product_company(self, to_date, prod_ids=None, company_id=None):
        """Return avg unit cost (company-level) from stock_valuation_layer up to cutoff."""
        cr = self.env.cr
        to_date = self._end_of_day(to_date)
        if prod_ids is None:
            prod_ids = list({r.product_id.id for r in self if r.product_id})
        if not prod_ids:
            return {}
        if company_id is None:
            company_id = self.env.context.get('force_company') or self.env.company.id

        cr.execute("""
            SELECT product_id,
                   COALESCE(SUM(value), 0.0)    AS total_value,
                   COALESCE(SUM(quantity), 0.0) AS total_qty
            FROM stock_valuation_layer
            WHERE product_id = ANY(%s)
              AND company_id = %s
              AND create_date <= %s
            GROUP BY product_id
        """, (prod_ids, company_id, to_date))
        mapping = {}
        for product_id, total_value, total_qty in cr.fetchall():
            mapping[product_id] = (total_value / total_qty) if total_qty else 0.0
        return mapping

    @api.depends('on_hand_qty')
    def _compute_value(self):
        """Compute per-row value using company-level avg cost as-of to_date."""
        # to_date = self.env.context.get('to_date') or fields.Datetime.now()
        # to_date = self._end_of_day(to_date)
        # company_id = self.env.context.get('force_company') or self.env.company.id
        # prod_ids = list({r.product_id.id for r in self if r.product_id})
        # if not prod_ids:
        #     for rec in self:
        #         rec.value = 0.0
        #     return
        #
        # cost_map = self._avg_cost_by_product_company(to_date, prod_ids=prod_ids, company_id=company_id)
        for rec in self:
            # unit_cost = cost_map.get(rec.product_id.id, rec.product_id.standard_price or 0.0) #used for valuation layer
            unit_cost = rec.product_id.standard_price or 0.0 #use this for directly calculate the value based on cost * qty
            rec.value = (rec.on_hand_qty or 0.0) * unit_cost

    # ---- Server-side grouping: return aggregated rows to client by default ----
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Return aggregated results grouped by:
        (location_id, product_id, lot_id, package_id, owner_id)
        Unless client explicitly requests raw rows (context flag or group_by present).
        """
        # If caller wants raw rows or explicitly groups, fallback to default
        if self.env.context.get('stock_quant_at_date_raw') or self.env.context.get('group_by') or self.env.context.get('stock_quant_at_date_no_group'):
            return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

        domain = domain or []
        groupby = ['location_id', 'product_id', 'lot_id', 'package_id', 'owner_id']
        agg_fields = ['on_hand_qty']
        if fields and 'value' in fields:
            agg_fields.append('value')

        # Use read_group to get aggregated rows (this will call our read_group override for value)
        groups = self.read_group(domain, agg_fields, groupby, offset=offset, limit=limit, orderby=order, lazy=False)

        results = []
        # Build stable synthetic id per group so client can operate (negative to avoid collisions)
        for g in groups:
            key = (
                g.get('location_id') and (g['location_id'][0] if isinstance(g['location_id'], tuple) else g['location_id']),
                g.get('product_id') and (g['product_id'][0] if isinstance(g['product_id'], tuple) else g['product_id']),
                g.get('lot_id') and (g['lot_id'][0] if isinstance(g['lot_id'], tuple) else g['lot_id']),
                g.get('package_id') and (g['package_id'][0] if isinstance(g['package_id'], tuple) else g['package_id']),
                g.get('owner_id') and (g['owner_id'][0] if isinstance(g['owner_id'], tuple) else g['owner_id']),
            )
            rec = {}
            rec['id'] = -abs(hash(key))
            # Fill standard fields expected by the tree view
            rec['location_id'] = g.get('location_id') or False
            rec['product_id'] = g.get('product_id') or False
            rec['lot_id'] = g.get('lot_id') or False
            rec['package_id'] = g.get('package_id') or False
            rec['owner_id'] = g.get('owner_id') or False
            rec['on_hand_qty'] = g.get('on_hand_qty') or 0.0
            rec['reserved_qty'] = g.get('reserved_qty') or 0.0
            rec['available_qty'] = (g.get('on_hand_qty') or 0.0) - (g.get('reserved_qty') or 0.0)
            rec['value'] = g.get('value') or 0.0
            rec['currency_id'] = g.get('currency_id') or (self.env.company.currency_id.id if self.env.company else False)
            results.append(rec)

        # apply offset/limit on aggregated list (if requested)
        if offset or limit:
            results = results[offset: (offset + limit) if limit else None]

        return results

    # # ---- compute aggregated 'value' for read_group results ----
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     # Remove 'value' from DB aggregation (we compute it from aggregated qty)
    #     fields_wo_value = [f for f in fields if not f.startswith('value')]
    #     res = super().read_group(domain, fields_wo_value, groupby, offset=offset, limit=limit,
    #                              orderby=orderby, lazy=lazy)
    #
    #     to_date = self.env.context.get('to_date') or fields.Datetime.now()
    #     to_date = self._end_of_day(to_date)
    #     company_id = self.env.context.get('force_company') or self.env.company.id
    #
    #     prod_ids = []
    #     for row in res:
    #         if 'product_id' in row and isinstance(row['product_id'], tuple):
    #             prod_ids.append(row['product_id'][0])
    #     cost_map = self._avg_cost_by_product_company(to_date, prod_ids=list(set(prod_ids)), company_id=company_id) if prod_ids else {}
    #
    #     filtered_res = []
    #     for row in res:
    #         qty = row.get('on_hand_qty', 0.0) or 0.0
    #         pid = None
    #         if 'product_id' in row and isinstance(row['product_id'], tuple):
    #             pid = row['product_id'][0]
    #         unit_cost = cost_map.get(pid, 0.0) if pid else 0.0
    #         row['value'] = qty * unit_cost
    #         row['value_count'] = 1
    #
    #         # ✅ only keep groups where qty != 0
    #         if abs(qty) > 1e-6:   # tolerance for float errors
    #             filtered_res.append(row)
    #
    #     return filtered_res



    # ---- compute aggregated 'value' for read_group results ----
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # Remove 'value' from DB aggregation (we compute it from aggregated qty)
        fields_wo_value = [f for f in fields if not f.startswith('value')]
        res = super().read_group(domain, fields_wo_value, groupby, offset=offset, limit=limit,
                                 orderby=orderby, lazy=lazy)

        to_date = self.env.context.get('to_date') or fields.Datetime.now()
        to_date = self._end_of_day(to_date)
        company_id = self.env.context.get('force_company') or self.env.company.id

        prod_ids = []
        for row in res:
            if 'product_id' in row and isinstance(row['product_id'], tuple):
                prod_ids.append(row['product_id'][0])
        # if prod_ids:
        #     cost_map = self._avg_cost_by_product_company(to_date, prod_ids=list(set(prod_ids)), company_id=company_id)
        # else:
        #     cost_map = {}

        for row in res:
            qty = row.get('on_hand_qty', 0.0) or 0.0
            pid = None
            unit_cost = 0
            if 'product_id' in row and isinstance(row['product_id'], tuple):
                pid = row['product_id'][0]
                product = self.env['product.product'].browse(pid)
                unit_cost = product.standard_price or 0.0
            # unit_cost = cost_map.get(pid, 0.0) if pid else 0.0
            row['value'] = qty * unit_cost
            row['value_count'] = 1
        return res

    # ---- History: open aggregated view filtered by same keys and cutoff ----
    def action_view_stock_moves_custom(self):
        """Drill-down: stock move lines upto the same cutoff."""
        self.ensure_one()
        to_date = self.env.context.get('to_date')
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_line_action")
        # Safe default context
        ctx = {}
        try:
            if action.get('context'):
                ctx = literal_eval(action['context'])
        except Exception:
            ctx = {}
        ctx.update({
            'search_default_done': 1,
        })
        action['context'] = ctx

        dom = [
            ('state', '=', 'done'),
            ('product_id', '=', self.product_id.id),
        ]
        if to_date:
            dom.append(('date', '<=', to_date))
        # (A OR B)
        dom += ['|', ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id)]
        if self.lot_id:
            dom.append(('lot_id', '=', self.lot_id.id))
        if self.owner_id:
            dom.append(('owner_id', '=', self.owner_id.id))
        if self.package_id:
            dom += ['|', ('package_id', '=', self.package_id.id),
                    ('result_package_id', '=', self.package_id.id)]
        action['domain'] = dom
        return action
