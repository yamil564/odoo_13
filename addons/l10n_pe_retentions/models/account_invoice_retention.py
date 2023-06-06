# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
from itertools import *
from datetime import datetime, timedelta

class AccountInvoiceRetention(models.Model):
	_name = 'account.invoice.retention'
	_description = "Retención en Facturas/Documentos"

	########################################################################################################
	company_id = fields.Many2one('res.company',
		string="Compañia",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
		domain=lambda self: [('id', 'in', [i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids])],
		compute="compute_campo_company_id",store=True)
	########################################################################################################
	state = fields.Selection(selection=[
		('draft','Borrador'),('posted','Publicado'),('done','Pagado')],
		readonly=True, states={'draft': [('readonly', False)]},
		string="Estado", default="draft")

	account_retention_line_ids = fields.One2many('account.invoice.retention.lines','retention_id',
		string="Lineas de Retención de la Factura/Documento",readonly=True, states={'draft': [('readonly', False)]})

	#########################################################################################################
	is_retention=fields.Boolean(string="Documento sujeto a Retención",compute="_compute_retention",default=False,store=True)
	#########################################################################################################
	invoice_aml_id=fields.Many2one('account.move.line',string="Movimiento",required=True,
		domain="['&',('account_id.internal_type','in',['receivable']),'|',('amount_residual','>',0.00),('amount_residual_currency','>',0.00)]")

	partner_id=fields.Many2one('res.partner',string="Cliente",required=True)
	##################################################################################
	retention_move_id = fields.Many2one('account.move',string="Documento/Factura",readonly=True)
	receivable_retention_account_id = fields.Many2one('account.account',string="Cuenta por Cobrar del Documento",readonly=True)
	##################################################################################

	retention_company_currency_id=fields.Many2one('res.currency',string="Moneda de la Compañia",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice').currency_id,
		compute="compute_retention_company_currency_id",store=True,readonly=True)
	##########################################################################################################

	currency_id=fields.Many2one('res.currency',string="Moneda Documento",compute="compute_fields_aml_id",store=True)
	balance=fields.Monetary(string="Monto en MN del Documento",compute="compute_fields_aml_id",store=True,
		currency_field="retention_company_currency_id")

	amount_currency=fields.Monetary(string="Monto en ME del Documento",compute="compute_fields_aml_id",store=True,
		currency_field="currency_id")

	date_invoice=fields.Date(string="Fecha Emisión del Documento",compute="compute_fields_aml_id",store=True)
	amount_residual = fields.Monetary(string="Saldo Residual en MN",compute="compute_fields_aml_id",store=True,
		currency_field="retention_company_currency_id")

	amount_residual_currency = fields.Monetary(string="Saldo Residual en ME",compute="compute_fields_aml_id",store=True,
		currency_field="currency_id")
	
	is_paid=fields.Boolean(string="Documento Pagado",store=True,compute="compute_campo_is_paid")
	##########################################################################################################

	retention_amount = fields.Monetary(string="Monto Retención en ME",currency_field='currency_id',
		compute="_compute_retention",store=True)

	retention_amount_in_company_currency = fields.Monetary(string="Monto Retención en MN",currency_field='retention_company_currency_id',
		compute="_compute_retention",store=True)

	is_invoice_aml_in_ME=fields.Boolean(string="Documento en ME",default=False,compute="compute_is_invoice_aml_in_ME",store=True)
	
	porcentaje_retencion=fields.Float(default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_retencion')),
		copy=False,string="Porcentaje Retención")

	monto_minimo_retencion = fields.Float(default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('monto_minimo_retencion')),
		copy=False,string="Monto Mínimo Retención")
	#############################################################################################################


	def name_get(self):
		result = []
		for inv in self:
			rete_name = inv.invoice_aml_id and inv.invoice_aml_id.ref or 'Nuevo Registro'
			result.append((inv.id,"%s" % (rete_name)))
		return result



	@api.depends('company_id')
	def compute_campo_company_id(self):
		for rec in self:
			rec.company_id = self.env['res.company']._company_default_get('account.invoice')



	@api.depends('invoice_aml_id')
	def compute_retention_company_currency_id(self):
		for rec in self:
			if rec.invoice_aml_id:
				rec.retention_company_currency_id=rec.invoice_aml_id.company_id.currency_id



	@api.depends('invoice_aml_id','company_id','invoice_aml_id.currency_id','invoice_aml_id.balance','invoice_aml_id.amount_residual',
		'invoice_aml_id.date','invoice_aml_id.date_emission','invoice_aml_id.amount_residual','invoice_aml_id.amount_residual_currency')
	def compute_fields_aml_id(self):
		for rec in self:
			if rec.invoice_aml_id:
				rec.currency_id=rec.invoice_aml_id.currency_id or rec.company_id.currency_id
				rec.balance = abs(rec.invoice_aml_id.balance)
				rec.amount_currency = abs(rec.invoice_aml_id.amount_currency)
				rec.date_invoice = rec.invoice_aml_id.date_emission or rec.invoice_aml_id.date or False
				rec.amount_residual = abs(rec.invoice_aml_id.amount_residual)
				rec.amount_residual_currency = abs(rec.invoice_aml_id.amount_residual_currency)

	
	@api.onchange('invoice_aml_id')
	def onchange_partner_id(self):
		for rec in self:
			rec.partner_id = False
			rec.retention_move_id = False
			rec.receivable_retention_account_id = False

			if rec.invoice_aml_id:
				rec.partner_id = rec.invoice_aml_id.partner_id or False
				rec.retention_move_id = rec.invoice_aml_id.move_id or False
				rec.receivable_retention_account_id = rec.invoice_aml_id.account_id or False



	@api.depends('company_id','partner_id','company_id.es_agente_retencion','company_id.currency_id','company_id.es_agente_percepcion',
		'company_id.es_buen_contribuyente','balance','amount_currency','porcentaje_retencion','monto_minimo_retencion',
		'partner_id.es_agente_retencion','date_invoice','currency_id','retention_company_currency_id')
	def _compute_retention(self):
		for rec in self:
			if rec.partner_id.es_agente_retencion:
				if not(rec.company_id.es_agente_retencion or rec.company_id.es_agente_percepcion or rec.company_id.es_buen_contribuyente):
					aux_amount_in_company_currency = 0.00

					if rec.currency_id and rec.currency_id != rec.retention_company_currency_id:
							aux_amount_in_company_currency=rec.currency_id._convert(rec.amount_currency,
								rec.retention_company_currency_id,rec.company_id,rec.date_invoice)

					elif rec.currency_id:
							aux_amount_in_company_currency = rec.balance

					if aux_amount_in_company_currency > rec.monto_minimo_retencion:
						rec.retention_amount = rec.porcentaje_retencion*rec.amount_currency*0.01
						rec.retention_amount_in_company_currency=rec.porcentaje_retencion*aux_amount_in_company_currency*0.01
						rec.is_retention=True
	###########################################################################################################


	def action_open_wizard_retention_paid(self):
		self.ensure_one()
		view = self.env.ref('l10n_pe_retentions.wizard_paid_retention_view_form')
		return {
			'name': 'Registro de Retención',
			'view_type': 'form',
			'view_mode': 'form',
			'target': 'new',
			'res_model': 'wizard.paid.retention',
			'view_id': view.id,
			'views': [(view.id, 'form')],
			'type': 'ir.actions.act_window',
			'context': {'default_invoice_aml_id': self.invoice_aml_id.id,
						'default_retention_id': self.id,
						'default_amount_paid_currency':self.amount_residual_currency or self.amount_residual,
						'default_paid_currency_id':self.currency_id.id,
						'default_porcentaje_retencion':self.porcentaje_retencion}}




	@api.depends('currency_id','retention_company_currency_id','is_retention')
	def compute_is_invoice_aml_in_ME(self):
		for rec in self:
			if rec.is_retention:
				if rec.currency_id and rec.retention_company_currency_id != rec.currency_id:
					rec.is_invoice_aml_in_ME=True
				else:
					rec.is_invoice_aml_in_ME=False



	@api.depends('invoice_aml_id','amount_residual')
	def compute_campo_is_paid(self):
		for rec in self:
			if rec.invoice_aml_id and rec.amount_residual>0.00:
				rec.is_paid=False
			elif rec.invoice_aml_id and rec.amount_residual==0.00:
				rec.is_paid=True
