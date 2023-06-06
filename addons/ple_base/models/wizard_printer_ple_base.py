# -*- coding: utf-8 -*-
from io import BytesIO
import calendar
from odoo import models, fields, api, _
from datetime import datetime, timedelta
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

class WizardPrinterPleBase(models.TransientModel):
	_name='wizard.printer.ple.base'
	_description = "Modulo base Impresor para el PLE Libros SUNAT"

	
	print_format = fields.Selection(selection='available_formats',string='Formato Impresión',
		default='txt',required=True)
		
	print_order = fields.Selection(selection='criterios_impresion',
		string="Criterio impresión",required=True) 
		

	company_id = fields.Many2one('res.company',
		string="Compañia", 
		default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
		domain = lambda self: [('id', 'in',[i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids] )],
		readonly=True,required=True)


	def word_month(self,month):
		meses={
			'01':'ENERO',
			'02':'FEBRERO',
			'03':'MARZO',
			'04':'ABRIL',
			'05':'MAYO',
			'06':'JUNIO',
			'07':'JULIO',
			'08':'AGOSTO',
			'09':'SEPTIEMBRE',
			'10':'OCTUBRE',
			'11':'NOVIEMBRE',
			'12':'DICIEMBRE'}
		return meses[month]


	@api.model
	def criterios_impresion(self):  ## LO RECOMENDABLE ES CONVERTIR ESTO A UN ARRAY !!!! 
		criterios = [
			('nro_documento','N° de registro'), # numero de registro es un consecutivo ## SE TRATA DEL ASIENTO CONTABLE !!
			('date','Fecha de emisión'), # fecha de registro u emision
			('invoice_number','N° de documento'),
			('prefix_code','N° de serie'),
			# ('table10_id','Tipo de documento')
			]
		return criterios


	def available_formats(self):
		formats=[
			('xlsx','xlsx'),
			('txt','txt'),
			('pdf','pdf')]
		return formats


	def _init_buffer(self, output):
		return output


	
	def action_print(self):
		return {
			'type': 'ir.actions.act_url',
			'url': 'reports/format/{}/{}/{}'.format(self._name, self.print_format, self.id),
			'target': 'new'
		}



	def document_print(self):
		output = BytesIO()
		output = self._init_buffer(output)
		output.seek(0)
		return output.read()


	def _get_query_datas(self, objet=False, domain=[], order_by=''):
		domain +=  [('company_id','in',[self.company_id.id])]
		return self.env[objet].search(domain + [('company_id','=',self.company_id.id)],order=order_by)