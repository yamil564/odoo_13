from odoo import fields, models

class ResPartnerBank(models.Model):
	_inherit = 'res.partner.bank'

	detraction_bank = fields.Boolean(string="Detraction bank", default=False)
