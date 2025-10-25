from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    def _server_action_fix_entry_date(self):
        """
        Fix SVL accounting entry date to match picking effective date (date_done).
        """
        fixed_svl = []
        skipped_svl = []

        for svl in self:
            move = svl.stock_move_id
            picking = move.picking_id if move else False
            effective_date = picking.date_done if picking else False

            if not effective_date:
                skipped_svl.append(svl.id)
                continue

            try:
                # Regenerate accounting entries with correct date
                if svl.account_move_id.date != effective_date.date():
                    svl.account_move_id.sudo().button_draft()
                    svl.account_move_id.sudo().unlink()
                    svl.with_context(datafix_effective_date=effective_date.date())._validate_accounting_entries()
                    svl._validate_analytic_accounting_entries()

                    fixed_svl.append(svl.id)
            except Exception as e:
                skipped_svl.append((svl.id, str(e)))

        _logger.info(fixed_svl)
        _logger.info(skipped_svl)

