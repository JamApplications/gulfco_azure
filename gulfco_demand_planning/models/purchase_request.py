from odoo import api, fields, models, _

class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    demand_planning_ids = fields.Many2many('demand.planning',string="Demand Planning")
    demand_planning_count = fields.Integer(compute="compute_demand_planning_count")
    request_type = fields.Selection([('normal', 'Normal'), ('order_analysis', 'Order Analysis')], default="normal",
                                    string="Request Type")

    @api.model
    def _get_default_name(self):
        if self.env.context.get('from_order_analysis'):
            if self.env.context.get('order_date'):
                return self.env["ir.sequence"].with_context(ir_sequence_date=self.env.context.get('order_date')).next_by_code("order.analysis")
            return self.env["ir.sequence"].next_by_code("order.analysis")
        return self.env["ir.sequence"].next_by_code("purchase.request")

    def compute_demand_planning_count(self):
        for record in self:
            if record.demand_planning_ids:
                record.demand_planning_count = len(record.demand_planning_ids)
            else:
                record.demand_planning_count = 0

    def action_view_demand_planning(self):
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_demand_planning.action_view_demand_planning")
        action['domain'] = [('id','in',self.demand_planning_ids.ids)]
        return action

    def action_view_demand_planning_report(self):
        action = self.env["ir.actions.actions"]._for_xml_id("gulfco_demand_planning.action_demand_planning")
        action['domain'] = [('id','in',self.demand_planning_ids.ids)]
        return action

    def action_view_purchase_request_line(self):
        if self.env.context.get('from_order_analysis'):
            action = (
                self.env.ref("gulfco_demand_planning.order_analysis_line_form_action")
                .sudo()
                .read()[0]
            )
        else:
            action = (
                self.env.ref("purchase_request.purchase_request_line_form_action")
                .sudo()
                .read()[0]
            )
        lines = self.mapped("line_ids")
        # if len(lines) > 1:
        action["domain"] = [("id", "in", lines.ids)]
        # elif lines:
        #     action["views"] = [
        #         (self.env.ref("purchase_request.purchase_request_line_form").id, "form")
        #     ]
        #     action["res_id"] = lines.ids[0]
        return action

