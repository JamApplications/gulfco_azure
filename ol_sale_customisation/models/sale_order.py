from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None
                # Use custom sequence code 'sale.quotation' instead of 'sale.order'
                vals['name'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code(
                    'sale.quotation', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    # def action_confirm(self):
    #     # Call the original action_confirm method
    #     # Update name with the original 'sale.order' sequence for confirmed orders
    #     for order in self:
    #         if order.state == 'sale':  # Ensure it's confirmed
    #             seq_date = fields.Datetime.context_timestamp(
    #                 self, fields.Datetime.to_datetime(order.date_order)
    #             )
    #             order.name = self.env['ir.sequence'].with_company(order.company_id.id).next_by_code(
    #                 'sale.order', sequence_date=seq_date) or _("SO001")
    #     result = super().action_confirm()
    #     return result
    def _action_confirm(self):
        for order in self:
            if order.state == 'sale':  # Ensure it's confirmed
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(order.date_order)
                )
                order.name = self.env['ir.sequence'].with_company(order.company_id.id).next_by_code(
                    'sale.order', sequence_date=seq_date) or _("SO001")
        res = super()._action_confirm()
        return res
    
    # def action_confirm(self):
    #     """Override action_confirm to handle van sales picking creation."""
    #     res = super(SaleOrder, self).action_confirm()
    #     for rec in self:
    #         for picking in rec.picking_ids:
    #             if picking.picking_type_id.code == 'outgoing' and rec.order_creation_source == 'vansales':
    #                 van_location = rec.assign_to.van_location
    #                 warehouse = van_location.warehouse_id
    #                 new_type = self.env['stock.picking.type'].search([('code','=','outgoing'),('warehouse_id','=',warehouse.id)],limit=1)
    #                 new_dest_loc = rec.partner_id.van_location
    #                 picking.sudo().with_context(van_sales = True).write({
    #                     'location_id': van_location.id,
    #                     'location_dest_id': new_dest_loc.id,
    #                     'picking_type_id':new_type.id,
    #                     'state':'draft',
    #                     'draft_trigger': True,
    #                 })
    #                 break
    #     return res
                    
                    
        # for order in self:
        #     if order.order_creation_source == 'vansales':
        #         # Create a single picking for van sales
        #         StockPicking = self.env['stock.picking']
        #         picking_type = self.env['stock.picking.type'].search([
        #             ('code', '=', 'outgoing'),
        #             ('company_id', '=', order.company_id.id)
        #         ], limit=1)
        #         if not picking_type:
        #             raise UserError("No delivery order picking type found for the company.")

        #         # Get source location from assign_to (van worker location)
        #         source_location = order.assign_to.property_stock_customer if order.assign_to and order.assign_to.property_stock_customer else False
        #         if not source_location:
        #             raise UserError("No source location defined for the assigned van worker.")

        #         # Get destination location (customer location)
        #         destination_location = order.partner_id.property_stock_customer

        #         picking = StockPicking.create({
        #             'picking_driver_id': order.partner_id.id,
        #             'picking_type_id': picking_type.id,
        #             'location_id': source_location.id,
        #             'location_dest_id': destination_location.id,
        #             'origin': order.name,
        #             'move_type': 'direct',
        #             'company_id': order.company_id.id,
        #             'partner_id': order.partner_id.id,
        #             'state': 'draft',  # Set status to draft
        #             'scheduled_date': order.commitment_date or fields.Date.today(),
        #         })

        #         # Create stock moves for each order line
        #         StockMove = self.env['stock.move']
        #         for line in order.order_line:
        #             StockMove.create({
        #                 'name': line.name,
        #                 'company_id': order.company_id.id,
        #                 'product_id': line.product_id.id,
        #                 'product_uom_qty': line.product_uom_qty,
        #                 'product_uom': line.product_uom.id,
        #                 'location_id': source_location.id,
        #                 'location_dest_id': destination_location.id,
        #                 'picking_id': picking.id,
        #                 'state': 'draft',
        #                 'origin': order.name,
        #                 'group_id': order.procurement_group_id.id if order.procurement_group_id else False,
        #             })

        #         picking.action_confirm()
        #         picking.action_assign()
        #         res = True
                
        #     else:
        #         res = super().action_confirm()
        # return res
        # # Call the parent action_confirm (includes original SaleOrderExt logic)