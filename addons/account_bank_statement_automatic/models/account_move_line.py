from odoo import fields,models,api

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	statement_extract_line_id=fields.Many2one('account.bank.statement.line', string="Transacción Bancaria")

	