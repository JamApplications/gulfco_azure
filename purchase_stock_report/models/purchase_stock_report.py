from odoo import models, fields, api

class PurchaseStockReport(models.Model):
    _name = 'purchase.stock.report'
    _description = 'Purchase & Stock Report'
    _auto = False  # SQL View model

    # الحقول الأساسية
    date = fields.Datetime(string="Receipt Date")
    expiration_date = fields.Datetime(string="Expiration Date")
    location_id = fields.Many2one('stock.location', string="From")
    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
    product_packaging_id = fields.Many2one('product.packaging', string="Packaging")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float(string="Quantity")
    reference = fields.Char(string="Reference")
    source_document = fields.Char(string="Source Document")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string="Status")
    location_dest_id = fields.Many2one('stock.location', string="To")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    picking_id = fields.Many2one('stock.picking', string="Transfer/ASN Number")
    purchase_order = fields.Char(string="Purchase Order")

    # الحقول الجديدة للتكلفة
    ordered_qty = fields.Float(string="Ordered Quantity")
    ordered_cost = fields.Float(string="Ordered Cost")
    received_qty = fields.Float(string="Received Quantity")
    received_cost = fields.Float(string="Received Cost")
    additional_cost = fields.Float(string="Additional Cost")
    total_cost = fields.Float(string="Total Cost After Additional")
    po_ordered_date = fields.Datetime(string="PO Ordered Date")
    currency_id = fields.Many2one('res.currency', string="Currency")
    supplier_id = fields.Many2one('res.partner', string="Supplier")
    product_packaging_qty = fields.Float(string="Packaging Quantity")
    # landed_cost = fields.Float(string="Landed Cost")

    # def init(self):
    #     self.env.cr.execute("DROP VIEW IF EXISTS purchase_stock_report CASCADE;")
    #     self.env.cr.execute("""
    #         CREATE VIEW purchase_stock_report AS (
    #             SELECT
    #                 sml.id,
    #                 sp.date_done AS date,
    #                 sml.location_id,
    #                 sml.lot_id,
    #                 sqp.id AS product_packaging_id,
    #                 sml.product_id,
    #                 sml.quantity AS quantity,
    #                 po.name AS purchase_order,
    #                 po.date_approve AS po_ordered_date,
    #                 po.currency_id AS currency_id,
    #                 po.partner_id AS supplier_id,
    #                 sml.reference,
    #                 sp.origin AS source_document,
    #                 sp.state,
    #                 sml.location_dest_id,
    #                 sml.product_uom_id AS uom_id,
    #                 sml.picking_id,
    #                 sml.expiration_date,
    #                 sml.product_packaging_qty AS product_packaging_qty,
    #                 pol.product_qty AS ordered_qty,
    #                 (pol.product_qty * pol.price_unit) AS ordered_cost,
    #                 pol.qty_received AS received_qty,
    #                 (pol.qty_received * pol.price_unit) AS received_cost,
    #                 COALESCE(SUM(lc.amount_total), 0) AS landed_cost,
    #                 (pol.qty_received * pol.price_unit + COALESCE(SUM(lc.amount_total), 0)) AS cost_after_landed
    #             FROM stock_move_line sml
    #             JOIN stock_move sm ON sm.id = sml.move_id
    #             LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
    #             LEFT JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
    #             LEFT JOIN purchase_order po ON po.id = pol.order_id
    #             LEFT JOIN stock_quant_package sqp ON sqp.id = sm.product_packaging_id
    #             LEFT JOIN stock_landed_cost lc ON lc.picking_id = sp.id
    #             WHERE po.state = 'purchase'
    #             GROUP BY
    #                 sml.id, sp.date_done, sml.location_id, sml.lot_id, sqp.id, sml.product_id,
    #                 sml.quantity, po.name, po.date_approve, po.currency_id, po.partner_id,
    #                 sml.reference, sp.origin, sp.state, sml.location_dest_id, sml.product_uom_id,
    #                 sml.picking_id, sml.expiration_date, sml.product_packaging_qty,
    #                 pol.product_qty, pol.price_unit, pol.qty_received
    #         )
    #     """)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS purchase_stock_report CASCADE;")
        self.env.cr.execute("""
            CREATE VIEW purchase_stock_report AS (
                SELECT
                    sml.id,
                    sp.date_done AS date,
                    sml.location_id,
                    sml.lot_id,
                    sqp.id AS product_packaging_id,
                    sml.product_id,
                    sml.quantity AS quantity, 
                    po.name AS purchase_order,
                    po.date_approve AS po_ordered_date,
                    po.currency_id AS currency_id,
                    po.partner_id AS supplier_id,
                    sml.reference,
                    sp.origin AS source_document,
                    sp.state,
                    sml.location_dest_id,
                    sml.product_uom_id AS uom_id,
                    sml.picking_id,
                    sml.expiration_date,
                    sml.product_packaging_qty AS product_packaging_qty,
                    pol.product_qty AS ordered_qty,
                    (pol.product_qty * pol.price_unit) AS ordered_cost,
                    pol.qty_received AS received_qty,
                    (pol.qty_received * pol.price_unit) AS received_cost,
                    COALESCE(SUM(lc.amount_total), 0) AS landed_cost,
                    (pol.qty_received * pol.price_unit + COALESCE(SUM(lc.amount_total), 0)) AS total_cost
                FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
                LEFT JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
                LEFT JOIN purchase_order po ON po.id = pol.order_id
                LEFT JOIN stock_quant_package sqp ON sqp.id = sm.product_packaging_id
                LEFT JOIN stock_landed_cost lc ON lc.picking_id = sp.id
                WHERE po.state = 'purchase'
                GROUP BY
                    sml.id, sp.date_done, sml.location_id, sml.lot_id, sqp.id, sml.product_id,
                    sml.quantity, po.name, po.date_approve, po.currency_id, po.partner_id,
                    sml.reference, sp.origin, sp.state, sml.location_dest_id, sml.product_uom_id,
                    sml.picking_id, sml.expiration_date, sml.product_packaging_qty,
                    pol.product_qty, pol.price_unit, pol.qty_received
            )
        """)

# from odoo import models, fields
#
# class PurchaseStockReport(models.Model):
#     _name = 'purchase.stock.report'
#     _description = 'Purchase & Stock Report'
#     _auto = False  # SQL View model
#
#     date = fields.Datetime(string="Receipt Date")
#     expiration_date = fields.Datetime(string="Expiration Date")
#     location_id = fields.Many2one('stock.location', string="From")
#     lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
#     package_id = fields.Many2one('stock.quant.package', string="Packaging")
#     product_id = fields.Many2one('product.product', string="Product")
#     quantity = fields.Float(string="Quantity")
#     reference = fields.Char(string="Reference")
#     source_document = fields.Char(string="Source Document")
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('confirmed', 'Waiting'),
#         ('assigned', 'Ready'),
#         ('done', 'Done'),
#         ('cancel', 'Cancelled')
#     ], string="Status")
#     location_dest_id = fields.Many2one('stock.location', string="To")
#     uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
#     picking_id = fields.Many2one('stock.picking', string="Transfer/ASN Number")
#     purchase_order = fields.Char(string="Purchase Order")
#
#     # الحقول الجديدة
#     ordered_qty = fields.Float(string="Ordered Quantity")
#     ordered_cost = fields.Float(string="Ordered Cost")
#     received_qty = fields.Float(string="Received Quantity")
#     received_cost = fields.Float(string="Received Cost")
#     po_ordered_date = fields.Datetime(string="PO Ordered Date")
#     # po_line_index = fields.Integer(string="PO Line NO")
#     currency_id = fields.Many2one('res.currency', string="Currency")
#     supplier_id = fields.Many2one('res.partner', string="Supplier")
#     product_packaging_qty = fields.Float(string="Packaging Quantity")
#     landed_cost = fields.Float(string="Landed Cost")
#     cost_after_landed = fields.Float(string="Cost After Landed Cost")
#
#     # asn_request_id = fields.Many2one('stock.picking', string="ASN Number")
#
#     # def init(self):
#     #     self.env.cr.execute("DROP VIEW IF EXISTS purchase_stock_report CASCADE;")
#     #     self.env.cr.execute("""
#     #         CREATE VIEW purchase_stock_report AS (
#     #             SELECT
#     #                 sml.id,
#     #                 sp.date_done AS date,
#     #                 sml.location_id,
#     #                 sml.lot_id,
#     #                 sml.product_id,
#     #                 sml.quantity AS quantity,
#     #                 po.name AS purchase_order,
#     #                 po.date_approve AS po_ordered_date,
#     #                 po.currency_id AS currency_id,
#     #                 po.partner_id AS supplier_id,
#     #                 sml.reference,
#     #                 sp.origin AS source_document,
#     #                 sp.state,
#     #                 sml.location_dest_id,
#     #                 sml.product_uom_id AS uom_id,
#     #                 sml.picking_id,
#     #                 sml.expiration_date,
#     #                 sm.product_packaging_id AS package_id,
#     #                 sml.product_packaging_qty AS product_packaging_qty,
#     #                 pol.product_qty AS ordered_qty,
#     #                 (pol.product_qty * pol.price_unit) AS ordered_cost,
#     #                 pol.qty_received AS received_qty,
#     #                 (pol.qty_received * pol.price_unit) AS received_cost,
#     #                 COALESCE(lc.amount_total,0) AS landed_cost,
#     #                 COALESCE((pol.qty_received * pol.price_unit),0) + COALESCE(lc.amount_total,0) AS cost_after_landed
#     #             FROM stock_move_line sml
#     #             JOIN stock_move sm ON sm.id = sml.move_id
#     #             LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
#     #             LEFT JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
#     #             LEFT JOIN purchase_order po ON po.id = pol.order_id
#     #             LEFT JOIN stock_landed_cost lc ON lc.picking_id = sp.id
#     #             WHERE po.state = 'purchase'
#     #         )
#     #     """)
#
# #
# def init(self):
#     self.env.cr.execute("DROP VIEW IF EXISTS purchase_stock_report CASCADE;")
#     self.env.cr.execute("""
#          CREATE VIEW purchase_stock_report AS (
#              SELECT
#                  sml.id,
#                  sp.date_done AS date,
#                  sml.location_id,
#                  sml.lot_id,
#                  sml.product_id,
#                  sml.quantity AS quantity,
#                  po.name AS purchase_order,
#                  po.date_approve AS po_ordered_date,
#                  po.currency_id AS currency_id,
#                  po.partner_id AS supplier_id,
#                  sml.reference,
#                  sp.origin AS source_document,
#                  sp.state,
#                  sml.location_dest_id,
#                  sml.product_uom_id AS uom_id,
#                  sml.picking_id,
#                  sml.expiration_date,
#                  sm.product_packaging_id AS package_id,
#                  sml.product_packaging_qty AS product_packaging_qty,
#                  pol.product_qty AS ordered_qty,
#                  (pol.product_qty * pol.price_unit) AS ordered_cost,
#                  pol.qty_received AS received_qty,
#                  (pol.qty_received * pol.price_unit) AS received_cost,
#                  COALESCE(SUM(lc.amount), 0) AS additional_cost,
#                  (pol.qty_received * pol.price_unit + COALESCE(SUM(lc.amount),0)) AS total_cost
#              FROM stock_move_line sml
#              JOIN stock_move sm ON sm.id = sml.move_id
#              LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
#              LEFT JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
#              LEFT JOIN purchase_order po ON po.id = pol.order_id
#              LEFT JOIN stock_landed_cost_line lcl ON lcl.move_id = sm.id
#              LEFT JOIN stock_landed_cost lc ON lc.id = lcl.landed_cost_id
#              WHERE po.state = 'purchase'
#              GROUP BY sml.id, sp.date_done, sml.location_id, sml.lot_id, sml.product_id,
#                       sml.quantity, po.name, po.date_approve, po.currency_id, po.partner_id,
#                       sml.reference, sp.origin, sp.state, sml.location_dest_id, sml.product_uom_id,
#                       sml.picking_id, sml.expiration_date, sm.product_packaging_id,
#                       sml.product_packaging_qty, pol.product_qty, pol.price_unit, pol.qty_received
#          )
#      """)




# from odoo import models, fields
#
# class PurchaseStockReport(models.Model):
#     _name = 'purchase.stock.report'
#     _description = 'Purchase & Stock Report'
#     _auto = False  # SQL View model
#
#     date = fields.Datetime(string="Date")
#     expiration_date = fields.Datetime(string="Expiration Date")
#     location_id = fields.Many2one('stock.location', string="From")
#     lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
#     package_id = fields.Many2one('stock.quant.package', string="Packaging")
#     product_id = fields.Many2one('product.product', string="Product")
#     quantity = fields.Float(string="Quantity")
#     reference = fields.Char(string="Reference")
#     source_document = fields.Char(string="Source Document")
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('confirmed', 'Waiting'),
#         ('assigned', 'Ready'),
#         ('done', 'Done'),
#         ('cancel', 'Cancelled')
#     ], string="Status")
#     location_dest_id = fields.Many2one('stock.location', string="To")
#     uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
#     picking_id = fields.Many2one('stock.picking', string="Transfer/ASN Number")
#     purchase_order = fields.Char(string="Purchase Order")
#
#     def init(self):
#         self.env.cr.execute("DROP VIEW IF EXISTS purchase_stock_report CASCADE;")
#         self.env.cr.execute("""
#             CREATE VIEW purchase_stock_report AS (
#                 SELECT
#                     sml.id,
#                     sml.date,
#                     sml.location_id,
#                     sml.lot_id,
#                     sml.package_id,
#                     sml.product_id,
#                     sml.quantity AS quantity,
#                     po.name AS purchase_order,
#                     sml.reference,
#                     sp.origin AS source_document,
#                     sp.state,
#                     sml.location_dest_id,
#                     sml.product_uom_id AS uom_id,
#                     sml.picking_id,
#                     sml.expiration_date
#                 FROM stock_move_line sml
#                 JOIN stock_move sm ON sm.id = sml.move_id
#                 LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
#                 LEFT JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
#                 LEFT JOIN purchase_order po ON po.id = pol.order_id
#                 WHERE po.state = 'purchase'
#             )
        # """)

