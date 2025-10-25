from odoo import fields, models, api, _
from odoo.exceptions import UserError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    # freeze_status = fields.Selection([
    #     ('full','Fully Freeze'),
    #     ('partial','Partially Freeze'),
    # ], string='Freeze Status', copy=False)

    is_freeze_location = fields.Boolean(string="Is Freeze",copy=False)

# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     is_freeze = fields.Boolean(string='Is Freeze?', copy=False)

class StockInventoryAdjustment(models.Model):
    _inherit = 'stock.inventory.adjustment'

    def action_start_inventory(self):
        super(StockInventoryAdjustment, self).action_start_inventory()
        for inventory in self:
            if inventory.location_id:
                location_ids = self.env['stock.location'].search([
                    ('id','child_of',[inventory.location_id.id])
                ])
                # if inventory.filter == 'category' :
                #     category_ids = self.env['product.category'].search([
                #         ('id','child_of',[inventory.category_id.id])
                #     ])
                #     product_ids = self.env['product.product'].search([
                #         ('categ_id','in',category_ids.ids)
                #     ])
                #     product_ids.write({'is_freeze':True})
                # elif inventory.filter == 'product' :
                #     inventory.product_id.is_freeze = True
                # if inventory.filter in ['none','partial'] :
                location_ids.write({'is_freeze_location':True})
                # else :
                #     location_ids.write({'freeze_status':'partial'})

    def set_freeze_false(self):
        for inventory in self:
            location_ids = self.env['stock.location'].search([
                ('id','child_of',[inventory.location_id.id])
            ])
            location_ids.write({'is_freeze_location':False})
            # if inventory.filter == 'category' :
            #     category_ids = self.env['product.category'].search([
            #         ('id','child_of',[inventory.category_id.id])
            #     ])
            #     product_ids = self.env['product.product'].search([
            #         ('categ_id','in',category_ids.ids)
            #     ])
            #     product_ids.write({'is_freeze':False})
            # elif inventory.filter == 'product' :
            #     inventory.product_id.is_freeze = False

    def action_validate(self):
        res = super(StockInventoryAdjustment, self.with_context(from_inventory_adjustment=True)).action_validate()
        self.set_freeze_false()
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'

    # @api.multi
    # def action_done(self):
    #     for me_id in self :
    #         if not me_id.picking_id and not me_id.inventory_id :
    #             if me_id.location_id.freeze_status == 'full' :
    #                 raise Warning("Can't move product %s from location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.name_get()[0][1],me_id.location_id.name_get()[0][1]))
    #             elif me_id.location_dest_id.freeze_status == 'full' :
    #                 raise Warning("Can't move product %s to location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.name_get()[0][1],me_id.location_dest_id.name_get()[0][1]))
    #             elif me_id.location_id.freeze_status and me_id.product_id.is_freeze :
    #                 raise Warning("Can't move product %s from location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.name_get()[0][1],me_id.location_id.name_get()[0][1]))
    #             elif me_id.location_dest_id.freeze_status and me_id.product_id.is_freeze :
    #                 raise Warning("Can't move product %s to location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done"%(me_id.product_id.name_get()[0][1],me_id.location_dest_id.name_get()[0][1]))
    #     return super(StockMove, self).action_done()

    def _action_done(self, cancel_backorder=False):
        for me_id in self:
            if not me_id.picking_id and not self.env.context.get('from_inventory_adjustment'):
                if me_id.location_id.is_freeze_location:
                    raise UserError(
                        "Can't move product %s from location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done" % (
                        me_id.product_id.display_name, me_id.location_id.display_name))
                elif me_id.location_dest_id.is_freeze_location:
                    raise UserError(
                        "Can't move product %s to location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done" % (
                        me_id.product_id.display_name, me_id.location_dest_id.display_name))
                # elif me_id.location_id.freeze_status:
                #     raise Warning(
                #         "Can't move product %s from location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done" % (
                #         me_id.product_id.name_get()[0][1], me_id.location_id.name_get()[0][1]))
                # elif me_id.location_dest_id.freeze_status and me_id.product_id.is_freeze:
                #     raise Warning(
                #         "Can't move product %s to location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done" % (
                #         me_id.product_id.name_get()[0][1], me_id.location_dest_id.name_get()[0][1]))
        return super(StockMove, self)._action_done(cancel_backorder)



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        if not self.env.context.get('from_inventory_adjustment'):
            for picking in self:
                # for pack in picking.pack_operation_product_ids:
                if picking.location_id.is_freeze_location:
                    raise UserError("Can't move product %s from location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(picking.product_id.display_name,picking.location_id.display_name))
                elif picking.location_dest_id.is_freeze_location:
                    raise UserError("Can't move product %s to location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(picking.product_id.display_name,picking.location_dest_id.display_name))
        return super().button_validate()

    # @api.multi
    # def do_transfer(self):
    #     for picking in self :
    #         for pack in picking.pack_operation_product_ids :
    #             if pack.location_id.freeze_status == 'full' :
    #                 raise Warning("Can't move product %s from location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(pack.product_id.name_get()[0][1],pack.location_id.name_get()[0][1]))
    #             elif pack.location_dest_id.freeze_status == 'full' :
    #                 raise Warning("Can't move product %s to location %s, because the location is in fully freeze status. Stock move can be process after inventory adjustment done"%(pack.product_id.name_get()[0][1],pack.location_dest_id.name_get()[0][1]))
    #             elif pack.location_id.freeze_status and pack.product_id.is_freeze :
    #                 raise Warning("Can't move product %s from location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done"%(pack.product_id.name_get()[0][1],pack.location_id.name_get()[0][1]))
    #             elif pack.location_dest_id.freeze_status and pack.product_id.is_freeze :
    #                 raise Warning("Can't move product %s to location %s, because the product and location is in freeze status. Stock move can be process after inventory adjustment done"%(pack.product_id.name_get()[0][1],pack.location_dest_id.name_get()[0][1]))
    #     return super(StockPicking, self).do_transfer()
        