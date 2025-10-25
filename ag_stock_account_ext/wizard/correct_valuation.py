from odoo import api, fields, models


class CorrectValuation(models.TransientModel):
    _name = 'correct.valuation'
    _description = 'Correct Valuation'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)


    
    def action_correct_valuation(self):
        out_valuation = self.env['stock.valuation.layer'].search([('value','>',0),('description', 'not ilike', 'negative inventory'),]).filtered(
            lambda val: val.create_date.date() >= self.start_date 
            and val.create_date.date() <= self.end_date
            and val.stock_move_id.picking_code == 'outgoing' and not val.stock_move_id.purchase_line_id
        )
        if out_valuation:
            ids = tuple(out_valuation.ids)
            query = """
                UPDATE stock_valuation_layer
                SET value = -value,
                    quantity = -quantity
                WHERE id IN %s
            """
            self.env.cr.execute(query, (ids,))


            for val_line in out_valuation:
                move_id = val_line.account_move_id.id
                if not move_id:
                    continue

                debit_side_account_id = val_line.product_id.categ_id.property_stock_account_output_categ_id.id
                credit_side_account_id = val_line.product_id.categ_id.property_stock_valuation_account_id.id

                query = """
                    UPDATE account_move_line
                    SET account_id = %s
                    WHERE move_id = %s AND debit > 0
                """
                self.env.cr.execute(query, (debit_side_account_id, move_id))

                query = """
                    UPDATE account_move_line
                    SET account_id = %s
                    WHERE move_id = %s AND credit > 0
                """
                self.env.cr.execute(query, (credit_side_account_id, move_id))




        in_valuation = self.env['stock.valuation.layer'].search([('value','<',0),('description', 'not ilike', 'negative inventory'),]).filtered(
            lambda val: val.create_date.date() >= self.start_date 
            and val.create_date.date() <= self.end_date
            and val.stock_move_id.picking_code == 'incoming'
        )
        if in_valuation:
            in_ids = tuple(in_valuation.ids)
            query = """
                UPDATE stock_valuation_layer
                SET value = abs(value),
                    quantity = abs(quantity)
                WHERE id IN %s
            """
            self.env.cr.execute(query, (in_ids,))

            for val_line in in_valuation:
                move_id = val_line.account_move_id.id
                if not move_id:
                    continue

                debit_side_account_id = val_line.product_id.categ_id.property_stock_valuation_account_id.id
                credit_side_account_id = val_line.product_id.categ_id.property_stock_account_input_categ_id.id

                query = """
                    UPDATE account_move_line
                    SET account_id = %s
                    WHERE move_id = %s AND debit > 0
                """
                self.env.cr.execute(query, (debit_side_account_id, move_id))

                query = """
                    UPDATE account_move_line
                    SET account_id = %s
                    WHERE move_id = %s AND credit > 0
                """
                self.env.cr.execute(query, (credit_side_account_id, move_id))




