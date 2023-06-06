# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
import logging
import requests
import json
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
	_inherit = 'account.move'

	is_contingencia = fields.Boolean(string="Es Contingencia",
		compute="compute_campo_is_contingencia",store=True)

	name_contingencia = fields.Char(string="Serie-Correlativo de Contingencia")


	@api.depends('journal_id')
	def compute_campo_is_contingencia(self):
		for rec in self:
			if rec.journal_id and rec.journal_id.is_contingencia:
				rec.is_contingencia = True
			else:
				rec.is_contingencia = False


	##################################################