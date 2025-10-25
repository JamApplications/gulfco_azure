from odoo import _, api, fields, models

class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    def launch_replenishment(self):
        product_id = False
        if self.env.context.get('active_model') == 'product.template':
            product_id = self.product_tmpl_id
        else:
            product_id = self.product_id
        if product_id and product_id.item_type == 'tradable' and product_id.responsible_id:
            buy_routes = product_id.route_ids.filtered(lambda s:s.is_buy_route)
            manufacture_routes = product_id.route_ids.filtered(lambda s:s.is_manufacture_route)
            message = False
            if buy_routes and manufacture_routes:
                message = '{} need to being Purchased or Manufactured'.format(product_id.name)
            elif buy_routes and not manufacture_routes:
                message = '{} need to being Purchased'.format(product_id.name)
            elif manufacture_routes and not buy_routes:
                message = '{} need to being Manufactured'.format(product_id.name)
            if message:
                product_id.message_post(
                    author_id=self.env.user.partner_id.id or None,  # None will set the default author in mail/mail_thread.py
                    body=message,
                    partner_ids=product_id.responsible_id.partner_id.ids,
                    message_type = "notification",
                    subtype_xmlid = "mail.mt_comment",
                    mail_auto_delete=False,
                )
        res = super(ProductReplenish,self).launch_replenishment()
        return res