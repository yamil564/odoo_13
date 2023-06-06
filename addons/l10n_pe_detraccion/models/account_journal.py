# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountJournalPe(models.Model):
	_inherit = 'account.journal'

	detraction = fields.Boolean(string="Detraccion", default=False)