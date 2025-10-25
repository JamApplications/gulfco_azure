from odoo import fields, models, api


class WorkerJournal(models.Model):
    _name = 'worker.journal'
    _description = 'Journal Worker'

    worker_ids = fields.Many2many("res.partner")
    journal_id = fields.Many2one("account.journal")
    journal_type = fields.Selection([('cash_van',"Cash Van"),("presale","PreSale"),('other',"Other")],default="cash_van")
    active = fields.Boolean(default=True)

    _rec_name = 'journal_id'