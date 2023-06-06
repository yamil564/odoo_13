# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountJournal(models.Model):
	_inherit = 'account.journal'

	is_retention = fields.Boolean(string="Retención", default=False)