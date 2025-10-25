from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = "stock.move"

    asn_line_id = fields.Many2one("asn.request.line", string="ASN Line")

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        self.ensure_one()
        rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        _logger.info("6666666666666666666666666666666666666666666666666666666")
        _logger.info("inside asn_request _generate_valuation_lines_data")
        _logger.info("6666666666666666666666666666666666666666666666666666666")

        svl = self.env['stock.valuation.layer'].browse(svl_id)
        analytic_account_ids = self.env['account.analytic.account']
        _logger.info("ANS_REQUEST - STOCK_MOVE - %s - %s" %(svl, analytic_account_ids))
        if not svl.account_move_line_id.analytic_distribution:
            _logger.info("ANS_REQUEST - STOCK_MOVE not analytic_distructions - %s" % (svl.account_move_line_id.analytic_distribution))
            location_analytic_account_id = svl.stock_move_id.location_id.warehouse_id.stock_analytic_account_id
            analytic_account_ids += location_analytic_account_id
            product_analytic_account_id = svl.stock_move_id.product_id.costing_dept_code_id
            analytic_account_ids += product_analytic_account_id
            channel_plan = self.env['account.analytic.plan'].sudo().search([('is_channel_plan', '=', True)], limit=1)
            analytic_account_ids += channel_plan.account_ids.filtered(lambda s: s.is_channel_common)
            if analytic_account_ids:
                rslt['credit_line_vals']['analytic_distribution'] = {str(account_id): 100 for account_id in analytic_account_ids.ids}
                rslt['debit_line_vals']['analytic_distribution'] = {str(account_id): 100 for account_id in analytic_account_ids.ids}
        _logger.info("ASN_REQUEST - STOCK MOVE RESULT %s" % rslt)
        return rslt

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        aml_vals = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        if self.env.context.get('from_price_diff_move'):
            aml_vals['original_diff_move_ids'] = [(6, 0, self.env.context.get('from_price_diff_move').ids)]
        return aml_vals

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    asn_line_id = fields.Many2one("asn.request.line", related="move_id.asn_line_id",store=True)




