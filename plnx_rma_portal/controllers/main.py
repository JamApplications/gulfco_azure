# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PlnxRmaPortal(http.Controller):

    @http.route(["/my/rmas/create_view"], type="http", auth="public", website=True)
    def portal_my_rma_create(self, **kwargs):
        user_partner = request.env.user.partner_id
        if kwargs.get('origin_picking') and kwargs.get('origin_move'):
            create_vals = {
                'partner_id': user_partner.id,
                'product_uom_qty': float(kwargs.get('quantity')),
                'picking_id': int(kwargs.get('origin_picking')),
                'move_id': int(kwargs.get('origin_move')),
                'operation_id': int(kwargs.get('request_type')),
                'description': kwargs.get('description'),
            }
            rma = request.env['rma'].sudo().create(create_vals)
            rma._compute_product_id()
            rma._send_draft_email()
            return request.redirect('/my/rmas/%s' % rma.id)

        partner_pickings = request.env['stock.picking'].sudo().search(
            ['|', ('partner_id', '=', user_partner.id),('partner_id', 'in', user_partner.child_ids.ids)]).filtered(
            lambda picking: any(move.remaining_qty and move.picking_code == 'outgoing' for move in picking.move_ids_without_package)
        )
        operation_ids = request.env['rma.operation'].sudo().search([])
        values = {
            'page_name': 'rma_create',
            'user_partner': user_partner,
            'partner_pickings': partner_pickings,
            'operation_types': operation_ids,
            # 'lines': self.picking_lines(picking_id=partner_pickings[0].id) if partner_pickings else [],
        }
        return request.render("plnx_rma_portal.portal_rma_create_page", values)

    @http.route(["/my/rma/picking_lines"], type="json", auth="user", website=True, csrf=False, methods=['POST'])
    def picking_lines(self, **kwargs):
        # Fetch the picking
        if kwargs.get('picking_id'):
            picking_id = kwargs.get('picking_id')
        else:
            return {'error': 'Picking not found'}
        picking = request.env['stock.picking'].sudo().browse(int(picking_id))
        # Prepare lines
        lines = picking.mapped('move_ids_without_package').filtered(lambda l: l.remaining_qty)
        result = [{
            'id': line.id,
            'product_id': {
                'id': line.product_id.id,
                'display_name': line.product_id.display_name,
            },
            'quantity': line.product_qty,
        } for line in lines]

        return result

    @http.route(["/my/rma/moves"], type="json", auth="user", website=True, csrf=False, methods=['POST'])
    def moves(self, **kwargs):
        # Fetch the picking
        if kwargs.get('move_id'):
            move = kwargs.get('move_id')
        else:
            return {'error': 'Move not found'}
        move_id = request.env['stock.move'].sudo().browse(int(move))
        result = {
            'move_id': move_id.id,
            'quantity': move_id.product_qty,
        }

        return result
