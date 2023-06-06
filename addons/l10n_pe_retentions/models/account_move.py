from odoo import models, fields, api
class AccountMove(models.Model):
	_inherit = "account.move"

	is_retention = fields.Char(string="Es Retencion", copy=False)

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	is_retention = fields.Char(string="Es Retencion", copy=False)