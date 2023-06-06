# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
from itertools import *
from datetime import datetime, timedelta

class AccountInvoiceRetentionLines(models.Model):
	_name = 'account.invoice.retention.lines'
	_description = "Lineas de Retención de la Factura"

	invoice_id=fields.Many2one('account.move',string="Documento",ondelete="cascade",readonly=True)

	retention_company_currency_id=fields.Many2one('res.currency',string="Moneda de la Compañia",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice').currency_id,
		compute="compute_retention_company_currency_id",store=True,readonly=True)
	amount_paid = fields.Monetary(string="Monto de Pago",currency_field="retention_company_currency_id",readonly=True)
	amount_paid_retention = fields.Monetary(string="Monto Retenido",currency_field="retention_company_currency_id",readonly=True)
	retention_date=fields.Date(string="Fecha de Registro de Retención",readonly=True)
	retention_journal_id = fields.Many2one('account.journal',string="Diario de Retención",readonly=True)
	retention_move_id = fields.Many2one('account.move',string="Asiento de Retención",readonly=True)
	nro_comprobante_retencion=fields.Char(string="Nro Comprobante Retención",readonly=True)
	##########################################
	retention_id = fields.Many2one('account.invoice.retention',string="Documento",ondelete="cascade",readonly=True)


	@api.depends('invoice_id','retention_id')
	def compute_retention_company_currency_id(self):
		for rec in self:
			if rec.invoice_id or rec.retention_id:
				rec.retention_company_currency_id=rec.invoice_id.company_id.currency_id or rec.invoice_id.company_id.currency_id



	def action_open_move_id(self):
		return {
			'name': 'Asiento Contable de Retención',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'account.move',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', [self.retention_move_id.id] or [])],
			'context': {'journal_id': self.retention_journal_id.id}}