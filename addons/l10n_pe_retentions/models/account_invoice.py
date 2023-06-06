# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_is_zero, float_compare
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
	_inherit = 'account.invoice'

	retention_company_currency_id=fields.Many2one('res.currency',string="Moneda de la Compañia",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice').currency_id)

	account_invoice_retention_line_ids = fields.One2many('account.invoice.retention.lines','invoice_id',
		string="Lineas de Retención de la Factura",readonly=True, states={'draft': [('readonly', False)]})

	is_retention=fields.Boolean(string="Factura sujeta a Retención",compute="_compute_retention",default=False)

	retention_amount = fields.Monetary(string="Monto de Retención",currency_field='currency_id',
		compute="_compute_retention",store=True)

	is_invoice_in_ME=fields.Boolean(default=False,compute="compute_is_invoice_in_ME")

	retention_amount_in_company_currency = fields.Monetary(string="Monto de Retención en Moneda Compañía",currency_field='retention_company_currency_id',
		compute="_compute_retention",store=True)
	
	porcentaje_retencion=fields.Float(default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('porcentaje_retencion')),
		copy=False,string="% Retención ")
	
	monto_minimo_retencion = fields.Monetary(default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('monto_minimo_retencion')),
		copy=False,string="Monto Mínimo Retención")

	################################################################################################
	send_retention_data_to_cpe=fields.Boolean(string="Enviar Datos a JSON de Factura Electrónica",default=True)
	################################################################################################

	@api.one
	@api.depends('company_id','company_id.es_agente_retencion','company_id.currency_id','company_id.es_agente_percepcion',
		'company_id.es_buen_contribuyente','amount_total','porcentaje_retencion','monto_minimo_retencion',
		'partner_id.es_agente_retencion','totales_igv','date_invoice','currency_id')
	def _compute_retention(self):

		if self.totales_igv:
			if self.partner_id.es_agente_retencion:
				if not(self.company_id.es_agente_retencion or self.company_id.es_agente_percepcion or self.company_id.es_buen_contribuyente):
					
					aux_amount_in_company_currency = 0.00

					if self.currency_id and self.currency_id != self.company_id.currency_id:
							aux_amount_in_company_currency=self.currency_id._convert(self.amount_total,
								self.company_id.currency_id,self.company_id,self.date_invoice)

					elif self.currency_id:
							aux_amount_in_company_currency = self.amount_total

					if aux_amount_in_company_currency > self.monto_minimo_retencion:
						self.retention_amount = self.porcentaje_retencion*self.amount_total*0.01
						self.retention_amount_in_company_currency=self.porcentaje_retencion*aux_amount_in_company_currency*0.01
						self.is_retention=True
	###########################################################################################################

	@api.multi
	def action_open_wizard_retention_paid(self):
		self.ensure_one()
		view = self.env.ref('factiva_l10n_pe_retentions.wizard_paid_retention_view_form')
		return {
			'name': 'Registro Retención',
			'view_type': 'form',
			'view_mode': 'form',
			'target': 'new',
			'res_model': 'wizard.paid.retention',
			'view_id': view.id,
			'views': [(view.id, 'form')],
			'type': 'ir.actions.act_window',
			'context': {'default_invoice_id': self.id,
						'default_amount_paid_currency':self.residual_signed or self.residual_company_signed,
						'default_paid_currency_id':self.currency_id.id,
						'default_porcentaje_retencion':self.porcentaje_retencion}}



	@api.multi
	@api.depends('currency_id','company_id.currency_id','is_retention')
	def compute_is_invoice_in_ME(self):
		for rec in self:
			if rec.is_retention:
				if rec.currency_id and rec.company_id.currency_id != rec.currency_id:
					rec.is_invoice_in_ME=True
				else:
					rec.is_invoice_in_ME=False

	###############################################################################
	def _prepare_json(self):
		json = super(AccountInvoice, self)._prepare_json()
		
		if not (self.journal_id.tipo_doc_id.code == '07'):
			if self.type in ['out_invoice','out_refund']:
				if self.send_retention_data_to_cpe and self.is_retention:

					retention = {
						"importeOperacion": self.amount_total,
						"porcentajeRetencion": round(self.porcentaje_retencion*0.01 or 0.00,2),
						"importeRetencion": round(self.retention_amount, 2),
					}
					json["retencionIgv"] = retention

		return json
	#################################################

	### CORRESPONDE A CUOTAS PARA TIPO DE PAGO : CREDITO.
	@api.depends('send_retention_data_to_cpe','cuota_ids.importe','is_retention','retention_amount','amount_total','monto_total_anticipo','is_comprobante_anticipo','tipo_anticipo')
	def _compute_cuota_total(self):
		super(AccountInvoice, self)._compute_cuota_total()
		for record in self:
			if record.send_retention_data_to_cpe and record.is_retention and record.retention_amount > 0:
				record.cuota_total = sum(record.cuota_ids.mapped('importe'))
				rete_moneda = record.retention_amount
				######################################################################
				record.cuota_limite = record.amount_total - round(rete_moneda, 2) - round((record.monto_total_anticipo)*(record.is_comprobante_anticipo and record.tipo_anticipo=='02'),2)
			else:
				record.cuota_total = sum(record.cuota_ids.mapped('importe'))
				######################################################################
				record.cuota_limite = record.amount_total - round((record.monto_total_anticipo)*(record.is_comprobante_anticipo and record.tipo_anticipo=='02'),2)
	##############################