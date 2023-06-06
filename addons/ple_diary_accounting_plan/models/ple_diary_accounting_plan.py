import calendar
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import xlsxwriter
from odoo.exceptions import UserError , ValidationError

import logging
_logger=logging.getLogger(__name__)

class PleDiaryAccountingPlan(models.Model):
	_name='ple.diary.accounting.plan'
	_inherit='ple.base'
	_description = "Modulo PLE Libros diario- Plan Contable"
	#5.4 LIBRO DIARIO DE FORMATO SIMPLIFICADO - DETALLE DEL PLAN CONTABLE UTILIZADO (*)

	ple_diary_accounting_plan_line_ids=fields.One2many('ple.diary.accounting.plan.line','ple_diary_accounting_plan_id',string="Libro diario-Plan Contable",readonly=True, states={'draft': [('readonly', False)]})
	
	fiscal_period= fields.Date(string="Día/Mes/Año Fiscal",required= True , readonly=True, states={'draft': [('readonly', False)]})

	################################################################

	def open_wizard_print_form(self):
		res = super(PleDiaryAccountingPlan,self).open_wizard_print_form()

		view = self.env.ref('ple_diary_accounting_plan.view_wizard_printer_ple_diary_accounting_plan_form')
		if view:

			return {
				'name': _('FORMULARIO DE IMPRESIÓN DEL LIBRO PLE'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'wizard.printer.ple.diary.accounting.plan',
				'views': [(view.id,'form')],
				'view_id': view.id,
				'target': 'new',
				'context': {
					'default_ple_diary_accounting_plan_id': self.id,
					'default_company_id' : self.company_id.id,}}

	#################################################################


	@api.onchange('fiscal_period')
	def _onchange_fiscal_period(self):
		for rec in self:
			if rec.fiscal_period:
				rec.fiscal_year=str(rec.fiscal_period.year)
				rec.fiscal_month=str(format(rec.fiscal_period.month,"02"))



	def _action_confirm_ple(self):
		return True

	
	def _get_datas(self, domain):
		orden=""
		if self.print_order == 'descripcion':
			orden = 'name asc'		
		elif self.print_order == 'codigo_cuenta_desagregado':
			# aux="invoice_id.invoice_number"
			orden =  'code asc '		
		
		return self._get_query_datas('account.account', domain, orden)


	def _get_domain(self): ## DADO QUE SON VALORES QUE NO CAMBIAN PERIODICAMENTE ESTA FUNCION NO SE REQUIERE !!
		domain = []
			# ('date','>=',self._get_star_date()),
			# ('date','<=',self._get_end_date()),
		return domain

	
	def generar_libro(self):
		
		self.state='open'
		
		self.ple_diary_accounting_plan_line_ids.unlink()
		registro=[]
		k=0
		for line in self._get_datas(self._get_domain()):
			registro.append((0,0,{'account_id':line.id,'codigo_cuenta_desagregado':line.code ,'descripcion_cuenta_contable': line.name} ) )

		self.ple_diary_accounting_plan_line_ids = registro ## EN EL MOMENTO DE ASIGNAR REGISTRO AL PUNTERO SE EMPIEZAN A CREAR LOS CAMPOS CORRESPONDIENTES AL MODELO

	

	def _convert_object_date(self, date):
		# parametro date que retorna un valor vacio o el foramto 01/01/2100 dia/mes/año
		if date:
			return date.strftime('%d/%m/%Y')
		else:
			return ''


	
	