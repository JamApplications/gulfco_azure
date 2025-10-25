from odoo import api, fields, models, _


class StockRequestOrderRecycle(models.TransientModel):
    _name = 'stock.request.order.recycle'

    partner_id = fields.Many2one('res.partner', string="Re-Cycle Company")

    destruction_cert_attachment = fields.Binary(string="Destruction Certificate Attachment")
    destruction_cert_name = fields.Char(string="Destruction Certificate")

    number_of_pallet = fields.Float('Number of Pallet')


    def action_confirm(self):
        order_ids = self.env.context.get("active_ids")
        order = self.env["stock.request.order"].browse(order_ids)

        for rec in order:
            if self.number_of_pallet:
                rec.number_of_pallet = self.number_of_pallet
            if self.partner_id:
                rec.customer_id = self.partner_id

            if self.destruction_cert_name and self.destruction_cert_attachment:
                self.env['ir.attachment'].create({
                    'name': f"attachment_{self.destruction_cert_name}",
                    'datas': self.destruction_cert_attachment,
                    'res_model': 'stock.request.order',
                    'res_id': rec.id,
                    'type': 'binary',
                    'mimetype': 'application/pdf',  # You can dynamically detect this if needed
                })
            rec.state = 'delivery_recycle'
