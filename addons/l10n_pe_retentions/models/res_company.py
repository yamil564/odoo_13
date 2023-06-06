# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResCompany(models.Model):
	_inherit = 'res.company'

	es_agente_retencion = fields.Boolean(string="Es Agente Retención", default=False)
	es_agente_percepcion = fields.Boolean(string="Es Agente Percepción", default=False)
	es_buen_contribuyente = fields.Boolean(string="Es Buen Contribuyente", default=False)
