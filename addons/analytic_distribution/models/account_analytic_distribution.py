# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountAnalyticDistribution(models.Model):
	_inherit = 'account.analytic.distribution'

	account_destino_id = fields.Many2one('account.account', string="Cuenta de distribucion", required=False)

class AccountAnalyticTag(models.Model):
	_inherit = 'account.analytic.tag'

	account_contra_id = fields.Many2one('account.account', string="Cuenta contrapartida")
