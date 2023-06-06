# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
from itertools import *
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class WizardPaidRetention(models.TransientModel):
	_name = 'wizard.paid.retention'
	_description = "Registrar Retención"


	company_id = fields.Many2one('res.company',
		string="Compañia",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
		domain=lambda self: [('id', 'in', [i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids])],
		compute="compute_campo_company_id",store=True)

	invoice_id = fields.Many2one('account.move',string="Documento",readonly=True)

	############################### SOPORTE PARA APUNTES CONTABLES !!
	retention_id=fields.Many2one('account.invoice.retention',string="Registro de Retención",readonly=True)
	invoice_aml_id = fields.Many2one('account.move.line',string="Movimiento/Documento",readonly=True)
	###############################

	retention_company_currency_id=fields.Many2one('res.currency',string="Moneda de la Compañia",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice').currency_id,
		compute="compute_retention_company_currency_id",store=True,readonly=True)

	paid_currency_id=fields.Many2one('res.currency',string="Moneda de Pago",
		default=lambda self: self.env['res.company']._company_default_get('account.invoice').currency_id)

	amount_paid_currency = fields.Monetary(string="Monto de Pago",currency_field="paid_currency_id")

	amount_paid_MN = fields.Monetary(string="Monto de Pago en MN",currency_field="retention_company_currency_id",
		compute="compute_retention_amounts",store=True)
	amount_retention_paid_MN = fields.Monetary(string="Monto Retenido en MN",currency_field="retention_company_currency_id",
		compute="compute_retention_amounts",store=True)

	paid_journal_id = fields.Many2one('account.journal',string="Diario de Pago",required=True,domain=[('type', 'in',['cash','bank'])])

	retention_ref = fields.Char(string="Referencia")
	retention_date=fields.Date(string="Fecha de Registro de Retención",required=True,
		default=datetime(datetime.now().year,datetime.now().month,datetime.now().day).date())

	retention_journal_id = fields.Many2one('account.journal',string="Diario de Retención",required=True,
		domain=[('is_retention', 'in',[True])])

	nro_comprobante_retencion=fields.Char(string="Nro Comprobante Retención",required=True)

	retention_move_id = fields.Many2one("account.move")
	################################################################
	#### SE AÑADE CAMPO PORCENTAJE PARA SOPORTAR DIFERENTES TASAS DE RETENCIÓN POR PAGO.
	porcentaje_retencion=fields.Float(string="Porcentaje de Retención %")


	@api.depends('company_id')
	def compute_campo_company_id(self):
		for rec in self:
			rec.company_id = self.env['res.company']._company_default_get('account.invoice')


	@api.depends('invoice_id','invoice_aml_id')
	def compute_retention_company_currency_id(self):
		for rec in self:
			rec.retention_company_currency_id=self.env['res.company']._company_default_get('account.invoice').currency_id


	@api.depends('retention_company_currency_id','paid_currency_id','amount_paid_currency',
		'retention_date','invoice_id.company_id','invoice_aml_id.company_id','porcentaje_retencion')
	def compute_retention_amounts(self):
		for rec in self:

			if rec.paid_currency_id and (rec.paid_currency_id != rec.retention_company_currency_id) and rec.retention_date:
				rec.amount_retention_paid_MN = abs(rec.paid_currency_id._convert(rec.amount_paid_currency*rec.porcentaje_retencion*0.01,
					rec.retention_company_currency_id,rec.invoice_id.company_id or rec.invoice_aml_id.company_id or self.company_id,
					rec.retention_date))

				rec.amount_paid_MN = abs(rec.paid_currency_id._convert(rec.amount_paid_currency,rec.retention_company_currency_id,
					rec.invoice_id.company_id  or rec.invoice_aml_id.company_id or self.company_id,rec.retention_date))

			else:
				rec.amount_retention_paid_MN=rec.amount_paid_currency*rec.porcentaje_retencion*0.01
				rec.amount_paid_MN = rec.amount_paid_currency



	def create_paid_retention(self):
		if (self.invoice_id and self.invoice_id.invoice_payment_state != 'paid') or \
			(self.invoice_aml_id and (abs(self.invoice_aml_id.amount_residual)>0.00 or \
				abs(self.invoice_aml_id.amount_residual_currency)>0.00)):
			####################
			retention_move_id = self.env['account.move'].create({'date': self.retention_date, 'ref': self.retention_ref or '',
				'journal_id': self.retention_journal_id.id,'currency_id':self.paid_currency_id.id or '','is_retention':True})

			self.retention_move_id = retention_move_id

			new_account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
			## CALCULANDO MONTO DOLARES
			debit=0.00
			credit=0.00
			amount_currency=0.00
			currency_id=False

			if self.retention_company_currency_id and self.paid_currency_id and self.retention_company_currency_id != self.paid_currency_id:
				debit, credit, amount_currency, currency_id = new_account_move_line.with_context(date=self.retention_date).\
					_compute_amount_fields(self.amount_paid_currency*self.porcentaje_retencion*0.01,
						self.paid_currency_id, self.retention_company_currency_id)
			else:
				debit=self.amount_paid_currency*self.porcentaje_retencion*0.01
				credit=0.00
				amount_currency=0.00
				currency_id=False

			_logger.info('\n\nMONEDA COMPUTADA\n\n')
			_logger.info(currency_id)
			
			currency_id=self.env['res.currency'].browse(currency_id)

			## PRIMERO CREANDO EL APUNTE DE RETENCIÓN
			retention_move_line_id = new_account_move_line.create(self._get_shared_move_line_vals(
				account_id=self.retention_journal_id.default_debit_account_id,
				name=self.retention_ref or '',
				debit=debit,
				credit=credit,
				amount_currency=amount_currency,
				currency_id=currency_id
				))


			## SEGUNDO CREANDO EL APUNTE DE LIQUIDEZ
			liquidez_move_line_id = new_account_move_line.create(self._get_shared_move_line_vals(
				account_id=self.paid_journal_id.default_debit_account_id,
				name=self.retention_ref or '',
				debit=self.amount_paid_MN - debit,
				credit=credit,
				currency_id=currency_id,
				amount_currency=self.amount_paid_currency*(1-self.porcentaje_retencion*0.01) if self.retention_company_currency_id \
					and  self.paid_currency_id and self.retention_company_currency_id != self.paid_currency_id else 0.00))			


			##########################################################################################
			receivable_move_line_id=''
			if not self.paid_currency_id.is_zero(self.amount_paid_MN):
				if not self.paid_currency_id != self.retention_company_currency_id:
					amount_currency = 0
				liquidity_aml_dict = self._get_shared_move_line_vals(
					#account_id=self.invoice_id.account_id or self.invoice_aml_id.account_id,
					account_id=self.invoice_aml_id.account_id,
					name=self.retention_ref or '',
					credit=self.amount_paid_MN,
					debit=credit,
					currency_id=self.invoice_aml_id.currency_id or (self.paid_currency_id if self.retention_company_currency_id and self.paid_currency_id \
						and self.retention_company_currency_id != self.paid_currency_id else False) or False,
					#currency_id=self.invoice_id.currency_id or self.invoice_aml_id.currency_id or self.paid_currency_id or False,
					amount_currency=-self.amount_paid_currency if self.retention_company_currency_id and self.paid_currency_id \
						and self.retention_company_currency_id != self.paid_currency_id else 0.00
					)

				receivable_move_line_id = new_account_move_line.create(liquidity_aml_dict)

			else:
				if not self.paid_currency_id != self.retention_company_currency_id:
					amount_currency = 0
				liquidity_aml_dict = self._get_shared_move_line_vals(
					#account_id = self.invoice_id.account_id or self.invoice_aml_id.account_id,
					account_id = self.invoice_aml_id.account_id,
					name=self.retention_ref or '',
					credit=self.amount_paid_MN,
					debit=credit,
					#currency_id=self.invoice_id.currency_id or self.invoice_aml_id.currency_id or self.paid_currency_id or False,
					currency_id=self.invoice_aml_id.currency_id or (self.paid_currency_id if self.retention_company_currency_id and self.paid_currency_id \
						and self.retention_company_currency_id != self.paid_currency_id else False) or False,
					amount_currency=-self.amount_paid_currency if self.retention_company_currency_id and self.paid_currency_id \
						and self.retention_company_currency_id != self.paid_currency_id else 0.00
					)

				receivable_move_line_id = new_account_move_line.create(liquidity_aml_dict)

			self.retention_move_id.action_post()
			
			#### CREANDO REGISTRO EN FACTURA
			"""if self.invoice_id:
				self.invoice_id.account_invoice_retention_line_ids.create({
					'invoice_id':self.invoice_id.id,
					'amount_paid':self.amount_paid_MN,
					'amount_paid_retention':self.amount_retention_paid_MN,
					'retention_date':self.retention_date,
					'retention_journal_id':self.retention_journal_id.id,
					'retention_move_id':self.retention_move_id.id,
					'nro_comprobante_retencion':self.nro_comprobante_retencion
					})"""
			if self.retention_id:
				self.retention_id.account_retention_line_ids.create({
					'retention_id':self.retention_id.id,
					'amount_paid':self.amount_paid_MN,
					'amount_paid_retention':self.amount_retention_paid_MN,
					'retention_date':self.retention_date,
					'retention_journal_id':self.retention_journal_id.id,
					'retention_move_id':self.retention_move_id.id,
					'nro_comprobante_retencion':self.nro_comprobante_retencion
					})

			### CONCILIANDO LA CUENTA POR COBRAR
			invoice_move_line_id=''

			#if self.invoice_id:
			#	invoice_move_line_id=self.invoice_id.move_id.line_ids.filtered(lambda r: r.account_id==self.invoice_id.account_id)
			if self.invoice_aml_id:
				invoice_move_line_id=self.invoice_aml_id

			if invoice_move_line_id:
				invoice_move_line_id=invoice_move_line_id[0]

			(invoice_move_line_id + receivable_move_line_id).reconcile()

			if self.retention_id and self.retention_id.state=='draft':
				self.retention_id.write({'state':'posted'})
			#########################################################
			if self.retention_id and self.retention_id.state=='posted' and self.invoice_aml_id.amount_residual==0:
				self.retention_id.write({'state':'done'})


	##############################################################
	def _get_shared_move_line_vals(self,account_id,name,debit,credit,amount_currency,currency_id):
		line_vals = {
			#'partner_id':self.invoice_id.partner_id.id or self.retention_id.partner_id.id or False,
			'partner_id':self.retention_id.partner_id.id or False,
			'move_id': self.retention_move_id.id,
			'account_id':account_id.id,
			'debit': debit or 0.00,
			'credit': credit or 0.00,
			'amount_currency': amount_currency or False,
			'journal_id': self.retention_journal_id.id or False,
			'name': name or '',
			'currency_id':currency_id and currency_id.id or False,
			'date_maturity':self.retention_date or False,
			'is_retention':True}

		#'currency_id':self.paid_currency_id != self.invoice_id.company_id.currency_id and self.paid_currency_id.id or False,

		return line_vals

