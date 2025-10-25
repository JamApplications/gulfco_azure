from odoo import models, fields,_,api
from odoo.exceptions import UserError
from odoo.tools import groupby
from odoo.tools import date_utils, SQL,Query
from odoo.osv import expression

class PurchaseBillMatchingReport(models.Model):
    _name = "purchase.bill.matching.report"
    _description = "Purchase Bill Matching Report"
    _auto = False

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string="PO Line", readonly=True)
    purchase_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)
    move_line_id = fields.Many2one('account.move.line', string="Bill Line", readonly=True)
    picking_id = fields.Many2one('stock.picking', string="Picking", readonly=True)
    received_qty = fields.Float(string="Received Qty", readonly=True)
    billed_qty = fields.Float(string="Billed Qty", readonly=True)
    variance_qty = fields.Float(string="Variance Qty", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', readonly=True)
    currency_id = fields.Many2one(comodel_name='res.currency', readonly=True)
    total_amount = fields.Monetary(string="Total Amount",currency_field='currency_id')

    # @api.model
    # def _search(self, domain, offset=0, limit=None, order=None) -> Query:
    #     if domain is None:
    #         domain = []
    #     domain = expression.AND([domain, ['|',('move_line_id','=',False),('variance_qty', '>', 0.0)]])
    #     return super()._search(domain,offset,limit,order)

    @property
    def _table_query(self):
        return """
            SELECT
                row_number() OVER() AS id,
                po.id AS purchase_id,
                pol.product_id AS product_id,
                pol.partner_id AS partner_id,
                pol.id AS purchase_line_id,
                pol.currency_id AS currency_id,
                sp.id AS picking_id,
                billed.move_line_id AS move_line_id,
                COALESCE(sm.received_qty, 0) AS received_qty,
                COALESCE(sm.received_qty * pol.price_unit, 0) AS total_amount,
                COALESCE(billed.billed_qty, 0) AS billed_qty,
                COALESCE(sm.received_qty, 0) - COALESCE(billed.billed_qty,0) AS variance_qty
            FROM purchase_order_line pol
            JOIN purchase_order po ON pol.order_id = po.id
            LEFT JOIN (
                SELECT sm.purchase_line_id, sm.picking_id, SUM(sm.quantity) AS received_qty
                FROM stock_move sm
                WHERE sm.state = 'done'
                GROUP BY sm.purchase_line_id, sm.picking_id
            ) sm ON sm.purchase_line_id = pol.id
            LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
            LEFT JOIN (
                SELECT 
                    r.stock_picking_id,
                    aml.product_id,
                    SUM(aml.quantity) AS billed_qty,
                    MAX(aml.id) AS move_line_id
                FROM stock_picking_bill_matching_rel r
                JOIN account_move_line aml ON aml.id = r.account_move_line_id
                WHERE aml.parent_state IN ('draft','posted')
                GROUP BY r.stock_picking_id, aml.product_id
            ) billed 
                ON billed.stock_picking_id = sp.id
               AND billed.product_id = pol.product_id
            WHERE sp.id IS NULL
               OR NOT EXISTS (
                    SELECT 1
                    FROM stock_picking_bill_matching_rel r2
                    JOIN account_move_line aml2 ON aml2.id = r2.account_move_line_id
                    WHERE r2.stock_picking_id = sp.id
                      AND aml2.product_id = pol.product_id
                      AND aml2.parent_state IN ('draft','posted')
                )
        """

    # @property
    # def _table_query(self):
    #     return """
    #         SELECT
    #             row_number() OVER() AS id,
    #             po.id AS purchase_id,
    #             pol.product_id AS product_id,
    #             pol.partner_id AS partner_id,
    #             pol.id AS purchase_line_id,
    #             pol.currency_id AS currency_id,
    #             aml.id AS move_line_id,
    #             sp.id AS picking_id,
    #             COALESCE(SUM(sm.quantity), 0) AS received_qty,
    #             COALESCE(SUM(sm.quantity) * pol.price_unit , 0) AS total_amount,
    #             COALESCE(SUM(aml.quantity), 0) AS billed_qty,
    #             COALESCE(SUM(sm.quantity), 0) - COALESCE(SUM(aml.quantity), 0) AS variance_qty
    #         FROM purchase_order_line pol
    #         JOIN purchase_order po ON pol.order_id = po.id
    #         LEFT JOIN stock_move sm ON sm.purchase_line_id = pol.id AND sm.state = 'done'
    #         LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
    #         LEFT JOIN account_move_line aml ON aml.purchase_line_id = pol.id AND aml.display_type = 'product' AND aml.parent_state in ('draft', 'posted') AND aml.purchase_line_id IS NULL
    #         LEFT JOIN account_move am ON am.id = aml.move_id
    #             AND am.move_type = 'in_invoice'
    #             AND am.state = 'posted'
    #         GROUP BY po.id, pol.id, aml.id, sp.id
    #     """

    @api.model
    def action_custom_create_bill_from_po_lines(self, partners, po_lines):
        """ Create a new vendor bill with the selected PO lines and returns an action to open it """
        bills = self.env['account.move']
        po_wise_lines = po_lines.grouped('order_id')
        # for po_order , po_lines_wise in po_wise_lines.items():
        bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id
            })
        bill.with_context(bill_matching_report_records=self)._add_purchase_order_lines(po_lines)
        bills += bill

        # for partner in partners:
        #     bill = self.env['account.move'].create({
        #         'move_type': 'in_invoice',
        #         'partner_id': partner.id,
        #     })
        #     bill.with_context(bill_matching_report_records=self)._add_purchase_order_lines(po_lines)
        #     bills += bill
        return bills._get_records_action()

    def action_custom_match_lines(self):
        if not self.purchase_line_id:  # we need POL(s) to either match or create bill
            raise UserError(_("You must select at least one Purchase Order line to match or create bill."))
        if len(self.purchase_id) > 1 and (len(self.purchase_id.partner_id) > 1 or len(self.purchase_id.currency_id) > 1):
            raise UserError(_("All selected lines purchase order must be from same vendor and with same currency."))
        if not self.move_line_id or (self.move_line_id and self.move_line_id.mapped('parent_state') not in ['draft','posted']):  # select POL(s) without AML -> create a draft bill with the POL(s)
            return self.with_context(bill_matching_report_records=self).action_custom_create_bill_from_po_lines(self.partner_id, self.purchase_line_id)
        # if len(self.move_line_id.mapped('move_id')) > 1:  # for purchase matching, disallow matching multiple bills at the same time
        #     raise UserError(_("You can't select lines from multiple Vendor Bill to do the matching."))

        pol_by_product = self.purchase_line_id.grouped('product_id')
        aml_by_product = self.move_line_id.grouped('product_id')
        residual_purchase_order_lines = self.purchase_line_id
        residual_account_move_lines = self.move_line_id
        residual_bill = self.move_line_id.move_id

        # Match all matchable POL-AML lines and remove them from the residual group
        for product, po_line in pol_by_product.items():
            po_line = po_line[0]  # in case of multiple POL with same product, only match the first one
            matching_bill_lines = aml_by_product.get(product)
            if matching_bill_lines:
                matching_bill_lines.purchase_line_id = po_line.id
                residual_purchase_order_lines -= po_line
                residual_account_move_lines -= matching_bill_lines

        # Delete all unmatched selected AML
        if residual_account_move_lines:
            residual_account_move_lines.unlink()

        # Add all remaining POL to the residual bill
        if residual_purchase_order_lines:
            residual_bill._add_custom_purchase_order_lines(residual_purchase_order_lines)