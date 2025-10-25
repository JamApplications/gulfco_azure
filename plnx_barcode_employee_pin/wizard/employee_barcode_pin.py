from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import UserError


class BarcodePinWizard(models.TransientModel):
    _name = 'barcode.pin.wizard'
    _description = 'Barcode PIN Wizard'

    pin = fields.Char(string='Enter Your PIN', required=True)

    def confirm_pin(self):
        # Search for the employee with the entered PIN
        # employee = self.env['hr.employee'].search([('barcode_pin', '=', self.pin)], limit=1)
        employee = self.env["hr.employee"].get_employees_pin_validated(self.pin, res_id=self.env.context.get('active_id'), res_model=self.env.context.get('active_model'))
        if employee:
            if self.env.context.get('active_model') == 'stock.picking':
                picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))

                action = picking.with_context(pop_wiz=True).action_open_picking_client_action()
                return action
        else:
            raise UserError("Invalid PIN, \nThe PIN entered is incorrect.")
            # return {'warning': {'title': 'Invalid PIN', 'message': 'The PIN entered is incorrect.'}}
