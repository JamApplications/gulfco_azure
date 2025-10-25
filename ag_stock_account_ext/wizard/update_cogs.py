from odoo import api, fields, models


class UpdateCogs(models.TransientModel):
    _name = 'product.cogs.update'
    _description = 'Update cogs'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    
    def action_update_cogs(self):
        start_date = self.start_date
        end_date = self.end_date

        # Get fixed accounts
        debit_side_account_id = self.env['account.account'].search([('code','=','611001')], limit=1).id
        credit_side_account_id = self.env['account.account'].search([('code','=','165022')], limit=1).id
        

        sale_lines = self.env['sale.order.line'].search([
            ('invoice_lines.move_id.date', '>=', self.start_date),
            ('invoice_lines.move_id.date', '<=', self.end_date)
        ])

        for sol in sale_lines:
            # Print for debugging
        
            for sol in sale_lines:

                svl_total = sum(
                    sol.move_ids.mapped('stock_valuation_layer_ids').filtered(
                        lambda svl: 'negative inventory' not in (svl.description or '').lower() or svl.quantity != 0
                    ).mapped('value')
                )

            
            # Iterate invoice lines of this sale line
            flag = False
            for aml in sol.order_id.invoice_ids.line_ids.filtered(lambda x: x.display_type == 'cogs' and x.product_id.id == sol.product_id.id):
                
                
                if aml.debit > 0:
                    flag = True
                    
                    update_debit_sql = """
                        UPDATE account_move_line
                        SET debit = %s,
                            balance = %s,
                            amount_currency = %s,
                            account_id = %s
                        WHERE id = %s
                        """
                    self.env.cr.execute(update_debit_sql, (
                        abs(svl_total),
                        abs(svl_total),
                        abs(svl_total),
                        debit_side_account_id,
                        aml.id  # replace with the actual COGS line ID
                    ))

                # Update credit line
                if aml.credit > 0:
                    flag = True
                    update_credit_sql = """
                        UPDATE account_move_line
                        SET credit = %s,
                            balance = %s,
                            amount_currency = %s,
                            account_id = %s
                        WHERE id = %s
                        """
                    self.env.cr.execute(update_credit_sql, (
                            abs(svl_total),
                            abs(svl_total) * -1,
                            abs(svl_total) * -1,
                            credit_side_account_id,
                            aml.id
                    ))

                if flag == False:
                    if aml.account_id.id == debit_side_account_id:
                        update_debit_sql = """
                            UPDATE account_move_line
                            SET debit = %s,
                                balance = %s,
                                amount_currency = %s,
                                account_id = %s
                            WHERE id = %s
                            """
                        self.env.cr.execute(update_debit_sql, (
                            abs(svl_total),
                            abs(svl_total),
                            abs(svl_total),
                            debit_side_account_id,
                            aml.id  # replace with the actual COGS line ID
                        ))
                    else:
                        update_credit_sql = """
                            UPDATE account_move_line
                            SET credit = %s,
                                balance = %s,
                                amount_currency = %s,
                                account_id = %s
                            WHERE id = %s
                        """
                        self.env.cr.execute(update_credit_sql, (
                                abs(svl_total),
                                abs(svl_total) * -1,
                                abs(svl_total) * -1,
                                credit_side_account_id,
                                aml.id
                        ))

            
        
      