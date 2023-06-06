# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
from itertools import *
import calendar
from datetime import datetime, timedelta
import logging
from odoo.addons import unique_library_accounting_queries as unique_queries

_logger = logging.getLogger(__name__)

class ReportAmountBalancesOptimizedNativeLine(models.Model):
	_name = 'report.amount.balances.optimized.native.line'
	_description = "Balance de Comprobación Nativo"
	# _rec_name = "name"
	report_amount_balances_optimized_id = fields.Many2one('report.amount.balances.optimized.native',string="Balance de Comprobación", ondelete="cascade", readonly=True)
	account_id = fields.Many2one('account.account', string="Cuenta", readonly=True)
	name_account=fields.Char(string="Cuenta", readonly=True)
	saldos_iniciales_deudor = fields.Char(string="Saldos Iniciales Deudor", readonly=True)
	saldos_iniciales_acreedor = fields.Char(string="Saldos Iniciales Acreedor", readonly=True)
	anio_fiscal_debe= fields.Char(string="Periodo Debe", readonly=True)
	anio_fiscal_haber= fields.Char(string="Periodo Haber", readonly=True)

	saldos_finales_deudor=fields.Char(string="Saldos Finales Deudor", readonly=True)
	saldos_finales_acreedor=fields.Char(string="Saldos Finales Acreedor", readonly=True)

	balance_general_activo=fields.Char(string="Balance General Activo", readonly=True)
	balance_general_pas_y_patr=fields.Char(string="Balance General Pas y Patr", readonly=True)

	resultados_naturaleza_perdidas=fields.Char(string="Resultados por Naturaleza Pérdidas", readonly=True)
	resultados_naturaleza_ganancias=fields.Char(string="Resultados por Naturaleza Ganancias", readonly=True)

	resultados_funcion_perdidas=fields.Char(string="Resultados por Función Pérdidas", readonly=True)
	resultados_funcion_ganancias=fields.Char(string="Resultados por Función Ganancias", readonly=True)

	### CAMPOS PARA CONSULTA DETALLE DE SALDOS
	exist_saldos_iniciales = fields.Boolean(string="Existen Saldos Iniciales",compute="compute_campo_exist_saldos_iniciales")
	exist_movimientos_periodo = fields.Boolean(string="Existen Movimientos Periodo",compute="compute_campo_exist_movimientos_periodo")
	###################################################################################################################################

	

	@api.depends('account_id','report_amount_balances_optimized_id')
	def compute_campo_exist_saldos_iniciales(self):
		for rec in self:
			if rec.account_id and rec.report_amount_balances_optimized_id:
				rec.exist_saldos_iniciales = True
			else:
				rec.exist_saldos_iniciales = False




	@api.depends('account_id','report_amount_balances_optimized_id')
	def compute_campo_exist_movimientos_periodo(self):
		for rec in self:
			if rec.account_id and rec.report_amount_balances_optimized_id:
				rec.exist_movimientos_periodo = True
			else:
				rec.exist_movimientos_periodo = False


	#####################################################################
	def query_account_amount_balances_opening_balances_ids(self):
		if self.report_amount_balances_optimized_id and self.exist_saldos_iniciales and self.account_id:
			filter_clause = self.report_amount_balances_optimized_id.get_query_filter_clause() or ''
			
			filter_clause += " and aml.account_id=%s "%(self.account_id.id)

			fecha_movimiento_debe = self.report_amount_balances_optimized_id.fecha_inicio.strftime("%Y-%m-%d")
			fecha_movimiento_haber = self.report_amount_balances_optimized_id.fecha_final.strftime("%Y-%m-%d")
			
			query = unique_queries.query_account_amount_balances_opening_balances_ids(fecha_movimiento_debe,fecha_movimiento_haber,filter_clause)
			
			self.env.cr.execute(query)
			records = self.env.cr.dictfetchall()

			return [i['id'] for i in records]

	#####################################################################
	def query_account_amount_balances_period_balances_ids(self):
		if self.report_amount_balances_optimized_id and self.exist_saldos_iniciales and self.account_id:
			filter_clause = self.report_amount_balances_optimized_id.get_query_filter_clause() or ''
			
			filter_clause += " and aml.account_id=%s "%(self.account_id.id)

			fecha_movimiento_debe = self.report_amount_balances_optimized_id.fecha_inicio.strftime("%Y-%m-%d")
			fecha_movimiento_haber = self.report_amount_balances_optimized_id.fecha_final.strftime("%Y-%m-%d")
			
			query = unique_queries.query_account_amount_balances_period_balances_ids(fecha_movimiento_debe,fecha_movimiento_haber,filter_clause)
			
			self.env.cr.execute(query)
			records = self.env.cr.dictfetchall()

			return [i['id'] for i in records]




	def button_view_saldos_iniciales(self):
		if self.exist_saldos_iniciales:
			return {
				'name': 'Movimientos de Saldo Inicial de la Cuenta %s'%(self.account_id.code),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'account.move.line',
				'view_id': False,
				'type': 'ir.actions.act_window',
				'domain': [('id','in', self.query_account_amount_balances_opening_balances_ids() or [])],
				'context': {
					'account_id': self.account_id.id,
				}
			}




	def button_view_movimientos_periodo(self):
		if self.exist_movimientos_periodo:
			return {
				'name': 'Movimientos del Periodo %s-%s de la Cuenta %s'%(
					self.report_amount_balances_optimized_id.fecha_inicio.strftime("%d-%m-%Y"),
					self.report_amount_balances_optimized_id.fecha_final.strftime("%d-%m-%Y"),self.account_id.code),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'account.move.line',
				'view_id': False,
				'type': 'ir.actions.act_window',
				'domain': [('id','in', self.query_account_amount_balances_period_balances_ids() or [])],
				'context': {
					'account_id': self.account_id.id,
				}
			}


