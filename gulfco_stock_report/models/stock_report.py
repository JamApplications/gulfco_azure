# -*- coding: utf-8 -*-
#############################################################################
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, tools




class GulfcoStockReport(models.Model):
    _name = "gulfco.stock.report"
    _description = "Stock Report View"
    _auto = False

    line_id = fields.Many2one('stock.move', string='Order Line')
    ############################################(Sale Order)########################################
    default_code = fields.Char("Item Code")
    name = fields.Char("Item Name")
    #standard_price = fields.Char("Cost")
    complete_name = fields.Char("Source Name")
    location = fields.Char("Location Full Name")
    location_name = fields.Char("Location Name")
    lot_name = fields.Char("Lot")
    expiration_date = fields.Date("Lot Expiration")
    product_id = fields.Many2one("product.product", "Product")
    #location_id = fields.Many2one("stock.location", "Location")
    planned_quantity=fields.Float("Planned QTY")
    qty = fields.Float("QTY")
    state = fields.Char("State")
    date = fields.Datetime("Date")
    picking_type_id = fields.Many2one("stock.picking.type", "Picking Type")
    operation_type = fields.Char("Operation Type")
    usage = fields.Char("Location Type")
    trx_type = fields.Char("TRX Type")
    cost = fields.Float("Cost")
    total_cost = fields.Float("Total Cost")
    category_id = fields.Many2one("product.category", "Product Category")


    def _init_report_view(self):
        tools.drop_view_if_exists(self._cr, 'gulfco_stock_report')
        self._cr.execute("""CREATE OR REPLACE VIEW gulfco_stock_report AS
                (SELECT
                    sm.id AS id,  -- Use the actual line ID as the primary ID
                    sm.id AS line_id,
                    sm.product_id,
                    --sm.location_dest_id location_id,
                    sm.product_uom_qty as planned_quantity,
                    sml.quantity as qty,
                    pt.default_code,
                    pt.categ_id AS category_id,
                    (pp.standard_price ->> '1')::numeric AS cost,
                    (((pp.standard_price ->> '1')::numeric)*sml.quantity) AS total_cost,
                    -- pp.standard_price as cost,
                    sm.state,
                    sm.date,
                    sm.picking_type_id,
                    sl_source.complete_name as complete_name,
                    sl_dest.complete_name as location,
                    sl_dest.name as location_name,
                    lot."name" lot_name,
                    lot.expiration_date,
                    spt.name ->> 'en_US' as operation_type,
                    --spt.name as operation_type,
                    sl_dest."usage",
                    'IN' trx_type
                    
                         
                FROM stock_move sm
                JOIN product_product pp ON sm.product_id = pp.id
                join product_template pt on pt.id =pp.product_tmpl_id 
                JOIN stock_location sl_source ON sm.location_id = sl_source.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                LEFT JOIN stock_picking_type spt ON sm.picking_type_id = spt.id
                join stock_move_line sml on sm.id = sml.move_id
                left join stock_lot lot on sml.lot_id = lot.id
                WHERE sm.state = 'done'  -- Only completed moves
                and sl_dest."usage" ='internal'

                union all 
                
                SELECT 
                    sm.id AS id,  -- Use the actual line ID as the primary ID
                    sm.id AS line_id,
                    sm.product_id,
                    --sm.location_dest_id location_id,
                    sm.product_uom_qty as planned_quantity,
                    (-1*sml.quantity) as qty,
                    pt.default_code,
                    pt.categ_id AS category_id,
                    (pp.standard_price ->> '1')::numeric AS cost,
                    (((pp.standard_price ->> '1')::numeric)*sml.quantity) AS total_cost,
                    -- pp.standard_price as cost,
                    sm.state,
                    sm.date,
                    sm.picking_type_id,
                    sl_source.complete_name as complete_name,
                    sl_dest.complete_name as location,
                    sl_dest.name as location_name,
                    lot."name" lot_name,
                    lot.expiration_date,
                    spt.name ->> 'en_US' as operation_type,
                    --spt.name as operation_type,
                    sl_dest."usage",
                    'Out' trx_type
                FROM stock_move sm
                JOIN product_product pp ON sm.product_id = pp.id
                join product_template pt on pt.id =pp.product_tmpl_id 
                JOIN stock_location sl_source ON sm.location_id = sl_source.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                LEFT JOIN stock_picking_type spt ON sm.picking_type_id = spt.id
                join stock_move_line sml on sm.id = sml.move_id
                left join stock_lot lot on sml.lot_id = lot.id
                WHERE sm.state = 'done'  -- Only completed moves
                and sl_source."usage" ='internal'               
                );
        """)

    def init(self):
        """Model initialization - creates the view when module is installed/updated"""
        self._init_report_view()




 