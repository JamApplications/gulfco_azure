from odoo import models, api, _, fields


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    asn_ids = fields.Many2many(
        "asn.request", string="ASN Reference", compute="_compute_asn_ids", store=False
    )

    @api.depends("picking_ids")
    def _compute_asn_ids(self):
        self.env.cr.execute("SELECT id FROM asn_request")
        all_asn_ids = [r[0] for r in self.env.cr.fetchall()]
        for cost in self:
            if cost.picking_ids and cost.picking_ids[0].asn_no_id:
                cost.asn_ids = [(6, 0, cost.picking_ids[0].asn_no_id.ids)]
            else:
                cost.asn_ids = [(6, 0, all_asn_ids)]
