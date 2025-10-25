# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        try:            
            done_pickings = self.filtered(lambda r: r.state == 'done')
            if done_pickings:
                # Query to get draft landed costs directly
                self.env.cr.execute("""
                    SELECT DISTINCT aslc.stock_landed_cost_id
                    FROM asn_stock_landed_cost aslc
                    INNER JOIN stock_landed_cost slc ON aslc.stock_landed_cost_id = slc.id
                    WHERE aslc.picking_id = ANY(%s)
                        AND aslc.stock_landed_cost_id IS NOT NULL
                        AND slc.state = 'draft'
                """, (done_pickings.ids,))

                result = self.env.cr.fetchall()
                draft_landed_cost_ids = [row[0] for row in result]

                # Only browse if we have results and need the recordset
                if draft_landed_cost_ids:
                    draft_landed_costs = self.env['stock.landed.cost'].browse(draft_landed_cost_ids)
                else:
                    draft_landed_costs = self.env['stock.landed.cost']

                if draft_landed_costs:
                    draft_landed_costs.compute_landed_cost()
                    draft_landed_costs.button_validate()                    
            return res
        
        finally:
            return res

