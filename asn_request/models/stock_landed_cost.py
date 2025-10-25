from odoo import models
import logging
_logger = logging.getLogger(__name__)

class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    def _prepare_account_move_line_values(self):
        _logger.info("11111111111111111111111111111111111111111111111111111")
        _logger.info("call stock valuation adjustment line")
        _logger.info("11111111111111111111111111111111111111111111111111111")
        res = super()._prepare_account_move_line_values()
        if self.cost_id.picking_ids:
            analytic_account_ids = self.env['account.analytic.account']
            stock_analytic_account_ids = self.cost_id.picking_ids.mapped('location_dest_id').mapped('warehouse_id').mapped('stock_analytic_account_id')
            analytic_account_ids += stock_analytic_account_ids
            product_analytic_account_ids = self.cost_id.picking_ids.mapped('move_ids').mapped('product_id').mapped('costing_dept_code_id')
            analytic_account_ids += product_analytic_account_ids
            channel_plan = self.env['account.analytic.plan'].sudo().search([('is_channel_plan','=',True)],limit=1)
            analytic_account_ids += channel_plan.account_ids.filtered(lambda s:s.is_channel_common)
            if analytic_account_ids:
                res['analytic_distribution'] = {str(account_id) : 100 for account_id in analytic_account_ids.ids}
                # res['analytic_distribution'] = {",".join(str(account_id) for account_id in analytic_account_ids.ids): 100}
        return res

