from odoo import api, fields, models


class UpdateJv(models.TransientModel):
    _name = 'val.update.jv'
    _description = 'Update JV'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)


    def action_val_generate_jv(self):
        
        valuation_ids = self.env['stock.valuation.layer'].search([]).filtered(lambda val: val.create_date.date() >= self.start_date and val.create_date.date() <= self.end_date and not val.account_move_id)
        
        for val_line in valuation_ids:
            journal_id = val_line.product_id.categ_id.property_stock_journal.id
            if val_line.value != 0:
                
                val_line._validate_accounting_entries()

                

                if val_line.account_move_id:


                    query = """
                        UPDATE account_move
                        SET date = %s, 
                        journal_id = %s
                        WHERE id = %s
                    """
                    self.env.cr.execute(query, (val_line.create_date.date(), val_line.account_move_id.id, journal_id))
                    val_debit_move_id = val_line.account_move_id.line_ids.filtered(lambda line: line.debit > 0)
                    val_credit_move_id = val_line.account_move_id.line_ids.filtered(lambda line: line.credit > 0)
                    debit_side_account_id = val_line.product_id.categ_id.property_stock_account_output_categ_id.id
                    credit_side_account_id = val_line.product_id.categ_id.property_stock_valuation_account_id.id

                    if val_debit_move_id and val_credit_move_id:

                        if val_debit_move_id.account_id.id == val_credit_move_id.account_id.id:
                            if val_line.stock_move_id.picking_code == 'outgoing':
                                val_debit_move_id.write({'account_id': debit_side_account_id })
                                val_credit_move_id.write({'account_id': credit_side_account_id })

                            if val_line.stock_move_id.picking_code == 'incoming':
                                val_debit_move_id.write({'account_id': credit_side_account_id })
                                val_credit_move_id.write({'account_id': debit_side_account_id })

                else:
                    amount = val_line.value
                    move_vals = {
                        'date': val_line.create_date.date(),
                        'journal_id': journal_id,
                        'ref': val_line.stock_move_id.reference or '/',
                        'line_ids': [],
                    }

                    debit_side_account_id = val_line.product_id.categ_id.property_stock_account_output_categ_id.id
                    credit_side_account_id = val_line.product_id.categ_id.property_stock_valuation_account_id.id
                    
                    move_vals['journal_id'] = journal_id
                    move_vals['ref'] = val_line._description
                    move_vals['date'] = val_line.create_date.date()
                    if amount >= 0:
                        # Outgoing
                        move_vals['line_ids'] = [
                            (0, 0, {
                                'account_id': debit_side_account_id,
                                'debit': amount,
                                'credit': 0,
                                'product_id': val_line.product_id.id
                            }),
                            (0, 0, {
                                'account_id': credit_side_account_id,
                                'debit': 0,
                                'credit': amount,
                                'product_id': val_line.product_id.id
                            }),
                        ]
                    else:
                        # Incoming 
                        move_vals['line_ids'] = [
                            (0, 0, {
                                'account_id': credit_side_account_id,
                                'debit': abs(amount),
                                'credit': 0,
                                'product_id': val_line.product_id.id
                            }),
                            (0, 0, {
                                'account_id': debit_side_account_id,
                                'debit': 0,
                                'credit': abs(amount),
                                'product_id': val_line.product_id.id
                            }),
                        ]

                    new_move = self.env['account.move'].create(move_vals)
                    new_move.action_post()
                    val_line.account_move_id = new_move

