from odoo import api, fields, models


class ProductCostUpdates(models.TransientModel):
    _name = 'product.cost.update'
    _description = 'Update product cost and related accounting entries'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    current_cost = fields.Float(related='product_id.standard_price', string="Current Cost")
    new_cost = fields.Float(string="New Cost", required=True)

    def action_update_product_cost(self):
        product_id = self.product_id
        out_valuation = self.env['stock.valuation.layer'].search([('product_id','=',product_id.id)]).filtered(lambda val: val.create_date.date() >= self.start_date and val.create_date.date() <= self.end_date).\
        stock_move_id.filtered(
            lambda val: (val.picking_code == 'outgoing' and not val.purchase_line_id) or (val.trx_type == 'return_collection')
            
        )


        for move in out_valuation:
            total_value = 0.0
            valuation_lines = move.stock_valuation_layer_ids
            
            for val_line in valuation_lines:
                quantity = val_line.quantity
                if quantity == 0.0:
                    quantity = move.quantity 

                val_line.write({
                    'unit_cost': self.new_cost,
                    'value': quantity * self.new_cost
                })
                total_value+= quantity * self.new_cost
                
                    
                if not move.account_move_ids:
                    val_line._validate_accounting_entries()
                    
                if val_line.account_move_id:

                    journal_id = val_line.product_id.categ_id.property_stock_journal.id


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
                            if move.picking_code == 'outgoing':
                                val_debit_move_id.write({'account_id': debit_side_account_id })
                                val_credit_move_id.write({'account_id': credit_side_account_id })

                        if val_debit_move_id.account_id.id != debit_side_account_id:

                            val_debit_move_id.write({'account_id': debit_side_account_id })
                        if val_credit_move_id.account_id.id != credit_side_account_id:
                            val_credit_move_id.write({'account_id': credit_side_account_id })


                    

                    if val_line.account_move_id and not val_debit_move_id and not val_credit_move_id:
                        
                        if total_value < 0.0:
                            
                            val_debit_move_id = val_line.account_move_id.line_ids.filtered(lambda x:x.account_id.id == debit_side_account_id)
                            val_credit_move_id = val_line.account_move_id.line_ids.filtered(lambda x:x.account_id.id == credit_side_account_id)

                        if total_value > 0.0:
                            credit_move_id = val_line.account_move_id.line_ids.filtered(lambda x:x.account_id.code == '165022')
                            val_credit_move_id = val_line.account_move_id.line_ids.filtered(lambda x:x.account_id.code == '165001')
                
                    if val_debit_move_id and val_credit_move_id:
                   
                        update_debit_line = """
                            update account_move_line set debit = {}, balance = {}, amount_currency = {} where id in {}
                        """.format(abs(quantity * self.new_cost), abs(quantity * self.new_cost), abs(quantity * self.new_cost), str(tuple(val_debit_move_id.ids)).replace(',)',')'))
                        self._cr.execute(query=update_debit_line)

                        update_credit_line = """
                            update account_move_line set credit = {}, balance = {}, amount_currency = {} where id in {}
                        """.format(abs(quantity * self.new_cost), abs(quantity * self.new_cost) * -1, abs(quantity * self.new_cost) * -1, str(tuple(val_credit_move_id.ids)).replace(',)',')'))
                        self._cr.execute(update_credit_line)


                 
            
                

            if move.sale_line_id:
                move_id = move.sale_line_id.invoice_lines[
                    0].move_id.id if move.sale_line_id.invoice_lines else None
                if move_id:
                    cogs_debit_side_account_id =  move.product_id.categ_id.property_account_expense_categ_id.id
                    cogs_credit_side_account_id = move.product_id.categ_id.property_stock_account_output_categ_id.id
                    move_lines = self.env['account.move.line'].search(
                        [('product_id', '=', move.product_id.id),('move_id', '=', move_id), ('display_type', '=', 'cogs')])
                    
                    if move_lines and len(move_lines) == 2:
                        
                        cogs_debit_id = move_lines.filtered(lambda cogs: cogs.debit > 0)
                        cogs_credit_id = move_lines.filtered(lambda cogs: cogs.credit > 0)
                        
                        if cogs_debit_id.account_id.id != cogs_debit_side_account_id:
                            cogs_debit_id.write({'account_id': cogs_debit_side_account_id})
                        if cogs_credit_id.account_id.id != cogs_credit_side_account_id:
                            cogs_credit_id.write({'account_id': cogs_credit_side_account_id})

                        if not cogs_debit_id and not cogs_credit_id:
                            cogs_debit_id = move_lines.filtered(lambda cogs: cogs.account_type == 'expense_direct_cost')
                            cogs_credit_id = move_lines.filtered(lambda cogs: cogs.account_id.account_type == 'asset_current')

                        update_cogs_debit_line = """
                                        update account_move_line set debit = {}, balance = {}, amount_currency = {} where id = {}
                                    """.format(abs(total_value), abs(total_value), abs(total_value), cogs_debit_id.id)
                        self._cr.execute(query=update_cogs_debit_line)

                        update_cogs_credit_line = """
                                        update account_move_line set credit = {}, balance = {}, amount_currency = {} where id = {}
                                    """.format(abs(total_value), abs(total_value) * -1, abs(total_value) * -1,
                                               cogs_credit_id.id)
                        self._cr.execute(query=update_cogs_credit_line)

            source_document = move.picking_id.origin
            rma_id = self.env['rma'].search([('name','=',source_document)])
            if rma_id:
                move_id = rma_id.refund_id.id

                if move_id:
                    move_lines = self.env['account.move.line'].search(
                        [('move_id', '=', move_id), ('display_type', '=', 'cogs')])
                    if move_lines and len(move_lines) == 2:
                        cogs_debit_id = move_lines.filtered(lambda cogs: cogs.debit > 0)
                        cogs_credit_id = move_lines.filtered(lambda cogs: cogs.credit > 0)

                        

                        update_cogs_debit_line = """
                                        update account_move_line set debit = {}, balance = {}, amount_currency = {} where id = {}
                                    """.format(abs(total_value), abs(total_value), abs(total_value), cogs_debit_id.id)
                        self._cr.execute(query=update_cogs_debit_line)

                        update_cogs_credit_line = """
                                        update account_move_line set credit = {}, balance = {}, amount_currency = {} where id = {}
                                    """.format(abs(total_value), abs(total_value) * -1, abs(total_value) * -1,
                                               cogs_credit_id.id)
                        self._cr.execute(query=update_cogs_credit_line)




        self.product_id.with_context(skip_price_change_journal=True).write({
            'standard_price': self.new_cost
        })
