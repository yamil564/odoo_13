# -*- coding: utf-8 -*-
import calendar
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import xlsxwriter
from odoo.exceptions import UserError , ValidationError

import logging
_logger=logging.getLogger(__name__)

meses=[
	('01','Enero'),
	('02','Febrero'),
	('03','Marzo'),
	('04','Abril'),
	('05','Mayo'),
	('06','Junio'),
	('07','Julio'),
	('08','Agosto'),
	('09','Septiembre'),
	('10','Octubre'),
	('11','Noviembre'),
	('12','Diciembre')]

class WizardPrinterPleDiaryAccountingPlan(models.TransientModel):
	_name='wizard.printer.ple.diary.accounting.plan'
	_inherit='wizard.printer.ple.base'
	_description = "Modulo Formulario Impresión PLE Libro Diario Plan Contable"


	ple_diary_accounting_plan_id = fields.Many2one('ple.diary.accounting.plan',
		string="PLE DIARIO PLAN CONTABLE",readonly=True,required=True)

	identificador_operaciones = fields.Selection(selection=[('0','Cierre de operaciones'),('1','Empresa operativa'),('2','Cierre de libro')],
		string="Identificador de operaciones", required=True, default="1")

	identificador_libro = fields.Selection(selection='available_formats_diary_accounting_plan_sunat', string="Identificador de libro" )
	
	print_order = fields.Selection(default='codigo_cuenta_desagregado')


	def action_print(self):
		
		if ( self.print_format and self.identificador_libro and self.identificador_operaciones) :
			return super(WizardPrinterPleDiaryAccountingPlan,self).action_print()
		else:
			raise UserError(_('NO SE PUEDE IMPRIMIR , Los campos: Formato Impresión , Identificador de operaciones y Identificador de libro son obligatorios, llene esos campos !!!'))


	def available_formats_diary_accounting_plan_sunat(self):
		formats=[('050300','Libro diario-Plan Contable'),
				('050400','Libro diario simplificado-Plan Contable')
			]
		return formats

	
	def criterios_impresion(self):
		res = [('codigo_cuenta_desagregado','Código Cuenta Desagregado'),('descripcion','Descripción de la Cuenta contable')]
		
		return res


	def _get_order_print(self , object):

		if self.print_order == 'description': # ORDENAMIENTO POR LA FECHA CONTABLE
			total=sorted(object, key=lambda PleDiaryAccountingPlanLine: PleDiaryAccountingPlanLine.descripcion_cuenta_contable) 
		
		elif self.print_order == 'codigo_cuenta_desagregado':
			total=sorted(object , key=lambda PleDiaryAccountingPlanLine: PleDiaryAccountingPlanLine.codigo_cuenta_desagregado ) # ORDENAMIENTO POR EL CODIGO DE CUENTA DESAGREGADO
		
		return total
	

	def file_name(self, file_format):
		nro_de_registros = '1' if len(self.ple_diary_accounting_plan_id.ple_diary_accounting_plan_line_ids)>0 else '0'

		file_name = "LE%s%s%s00%s%s%s1.%s" % (self.ple_diary_accounting_plan_id.company_id.vat, self.ple_diary_accounting_plan_id._periodo_fiscal(),
								self.identificador_libro, self.identificador_operaciones, nro_de_registros,
								self.ple_diary_accounting_plan_id.currency_id.code_ple or '1', file_format)
		return file_name

	######################################################
	def _periodo_fiscal_line(self):

		periodo = "%s%s%s" % (self.ple_diary_accounting_plan_id.fiscal_period.year or 'YYYY',
			format(self.ple_diary_accounting_plan_id.fiscal_period.month,"02") or 'MM',
			format(self.ple_diary_accounting_plan_id.fiscal_period.day,"02") or 'DD') # , self.fiscal_day or 'DD')

		return periodo
	

	def _init_buffer(self, output):
		# output parametro de buffer que ingresa vacio
		if self.print_format == 'xlsx':
			self._generate_xlsx(output)
		elif self.print_format == 'txt':
			self._generate_txt(output)
		return output
	

	def _generate_txt(self, output):
	
		for line in self._get_order_print(self.ple_diary_accounting_plan_id.ple_diary_accounting_plan_line_ids) :
			###########################################################
			escritura="%s|%s|%s|%s|%s|%s|%s|%s|\n" % (
				self._periodo_fiscal_line() ,
				line.codigo_cuenta_desagregado[:24] ,
				line.descripcion_cuenta_contable[:100] ,
				line.codigo_plan_contable ,
				line.descripcion_plan_contable_deudor[:60]  ,
				line.codigo_cuenta_contable_corporativa[:24]  ,
				line.descripcion_cuenta_contable_corporativa[:100] ,
				line.indicador_estado_operacion )
				
			output.write(escritura.encode())
			####################################################################

