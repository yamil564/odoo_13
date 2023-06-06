import calendar
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import xlsxwriter
from odoo.exceptions import UserError , ValidationError

import logging
_logger=logging.getLogger(__name__)

options=[
	('in','esta en'),
	('not in','no esta en')
	]

class PlePurchase(models.Model):
	_name='ple.purchase'
	_inherit='ple.base'
	_description = "Modulo PLE Libros de Compras"

	ple_purchase_line_ids=fields.One2many('ple.purchase.line','ple_purchase_id',string="Registros de compra",
		readonly=False, states={'send': [('readonly',True)]})
	
	ple_purchase_line_no_domiciliados_ids=fields.One2many('ple.purchase.line','ple_purchase_id_no_domiciliados',
		string="Registros de compra" , readonly=False, states={'send': [('readonly',True)]})
	
	ple_purchase_line_recibo_honorarios_ids=fields.One2many('ple.purchase.line','ple_purchase_id_recibo_honorarios',
		string="Registros de compra" , readonly=True, states={'draft': [('readonly', False)]})
	
	identificador_operaciones = fields.Selection(selection=[('0','Cierre de operaciones'),('1','Empresa operativa'),('2','Cierre de libro')],
		string="Identificador de operaciones", required=True, default="1")


	######################### FILTROS DINAMICOS, NUEVOS CAMPOS AGREGADOS !!!
	partner_ids = fields.Many2many('res.partner','ple_purchase_partner_rel','partner_id','ple_purchase_id_1' ,string="Socio" ,readonly=True , states={'draft': [('readonly', False)]})
	journal_ids = fields.Many2many('account.journal','ple_purchase_journal_rel','journal_id','ple_purchase_id_3',string="Diario" ,readonly=True , states={'draft': [('readonly', False)]})
	move_ids = fields.Many2many('account.move','ple_purchase_move_rel','move_id','ple_purchase_id_4',string='Asiento Contable' ,readonly=True , states={'draft': [('readonly', False)]})
	currency_ids = fields.Many2many('res.currency','ple_purchase_currency_rel','currency_id','ple_purchase_id_6', string="Moneda" ,readonly=True , states={'draft': [('readonly', False)]})
	##################################################################################
	partner_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	journal_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	move_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	currency_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})

	########################################################
	## CAMPO PARA IMPRIMIR RECIBO POR HONORARIOS EN LOS REPORTES DE DOMICILIADOS

	fecha=fields.Boolean(string="Fecha" ,readonly=True , states={'draft': [('readonly', False)]})
	periodo=fields.Boolean(string="Periodo" ,readonly=True , states={'draft': [('readonly', False)]})

	date_from=fields.Date(string="Desde:" ,readonly=True , states={'draft': [('readonly', False)]})
	date_to=fields.Date(string="Hasta:" ,readonly=True , states={'draft': [('readonly', False)]})

	fecha_inicio=''
	fecha_fin=''
	############## CHECK para indicar si se incluye o no registros anteriores no declarados
	
	incluir_anteriores_no_declarados = fields.Boolean(string="Incluir registros anteriores no declarados",
		default=False)


	def open_wizard_print_form(self):
		res = super(PlePurchase,self).open_wizard_print_form()

		view = self.env.ref('ple_purchase.view_wizard_printer_ple_purchase_form')
		if view:

			return {
				'name': _('FORMULARIO DE IMPRESIÓN DEL LIBRO PLE'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'wizard.printer.ple.purchase',
				'views': [(view.id,'form')],
				'view_id': view.id,
				'target': 'new',
				'context': {
					'default_ple_purchase_id': self.id,
					'default_company_id' : self.company_id.id,}}
	######################################

	def button_view_tree_domiciliados(self):
		self.ensure_one()
		view = self.env.ref('ple_purchase.view_ple_purchase_domiciliados_line_tree')
		if self.ple_purchase_line_ids:
			diccionario = {
				'name': 'Libro PLE Compras Domiciliadas',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'ple.purchase.line',
				'view_id': view.id,
				'views': [(view.id,'tree')],
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', [i.id for i in self.ple_purchase_line_ids] or [])],
				'context':{
					'search_default_filter_proveedor':1,
					'search_default_filter_tipo_comprobante':1,
					}
			}
			return diccionario
	###########################################
	def button_view_tree_no_domiciliados(self):
		self.ensure_one()
		view = self.env.ref('ple_purchase.view_ple_purchase_no_domiciliados_line_tree')
		if self.ple_purchase_line_ids:
			diccionario = {
				'name': 'Libro PLE Compras No Domiciliadas',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'ple.purchase.line',
				'view_id': view.id,
				'views': [(view.id,'tree')],
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', [i.id for i in self.ple_purchase_line_no_domiciliados_ids] or [])],
				'context':{
					'search_default_filter_proveedor':1,
					'search_default_filter_tipo_comprobante':1,
					}
			}
			return diccionario
	#############################################
	def button_view_tree_recibo_honorarios(self):
		self.ensure_one()
		view = self.env.ref('ple_purchase.view_ple_purchase_domiciliados_line_tree')
		if self.ple_purchase_line_ids:
			diccionario = {
				'name': 'Libro PLE Compras Recibo Honorarios',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'ple.purchase.line',
				'view_id': view.id,
				'views': [(view.id,'tree')],
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', [i.id for i in self.ple_purchase_line_recibo_honorarios_ids] or [])],
				'context':{
					'search_default_filter_proveedor':1,
					'search_default_filter_tipo_comprobante':1,
					}
			}
			return diccionario

			
	@api.onchange('fecha')
	def onchange_fecha(self):
		for rec in self:
			if rec.fecha:
				rec.periodo=False

	@api.onchange('periodo')
	def onchange_periodo(self):
		for rec in self:
			if rec.periodo:
				rec.fecha=False

	#######################################
	def unlink (self):
		for line in self:
			for line2 in line.ple_purchase_line_ids + line.ple_purchase_line_no_domiciliados_ids + line.ple_purchase_line_recibo_honorarios_ids:
				line2.move_id.write({'declared_ple_8_1_8_2':False})
			return super(PlePurchase,line).unlink()



	def _action_confirm_ple(self):
		array_id=[]
		for line in self.ple_purchase_line_ids + self.ple_purchase_line_no_domiciliados_ids + self.ple_purchase_line_recibo_honorarios_ids:
			array_id.append(line.move_id.id)
		# self.env['account.move'].browse(array_id).write({'declared_ple':True})
		super(PlePurchase , self)._action_confirm_ple('account.move' , array_id ,{'declared_ple_8_1_8_2':True})

	
	def _get_datas(self, domain):
		orden =''
		if self.print_order == 'date':
			orden = "invoice_date asc"		
		elif self.print_order == 'invoice_number':
			orden = "name asc"
		return self._get_query_datas('account.move', domain, orden)


	def _get_order_print(self , object):
		total =''
		if self.print_order == 'date':
			total=sorted(object, key=lambda PlePurchaseLine: PlePurchaseLine.fecha_emision_comprobante)
		elif self.print_order == 'invoice_number':
			total=sorted(object , key=lambda PlePurchaseLine: PlePurchaseLine.numero_comprobante)
		return total


	def _get_domain(self):
		#####################
		domain = []

		if self.fecha:
			self.fecha_inicio=self.date_from
			self.fecha_fin=self.date_to

			domain = [
				('date','>=',self.fecha_inicio),
				('date','<=',self.fecha_fin),
				('type','in',['in_invoice','in_refund']),
				('state','in',['posted'])
				]


		elif self.periodo:

			if self.incluir_anteriores_no_declarados:

				self.fecha_fin= self._get_end_date()

				domain = [
					('date','<=',self.fecha_fin),
					('type','in',['in_invoice','in_refund']),
					('state','in',['posted']),
					('declared_ple_8_1_8_2','!=',True)
					]

			else:
				self.fecha_inicio= self._get_star_date()
				self.fecha_fin= self._get_end_date()

				domain = [
					('date','>=',self.fecha_inicio),
					('date','<=',self.fecha_fin),
					('type','in',['in_invoice','in_refund']),
					('state','in',['posted']),
					('declared_ple_8_1_8_2','!=',True)
					]
		#####################

		'''if self.fecha:
			self.fecha_inicio=self.date_from
			self.fecha_fin=self.date_to
		elif self.periodo:
			self.fecha_inicio= self._get_star_date()
			self.fecha_fin= self._get_end_date()'''

		"""domain = [
			('date','>=',self.fecha_inicio),
			('date','<=',self.fecha_fin),
			('type','in',['in_invoice','in_refund']),
			('state','in',['posted'])
			]"""


		partners=list(self.partner_ids.mapped('id'))
		len_partners = len(partners or '')
		if len_partners:
			domain.append(('partner_id.id' , self.partner_option or 'in', partners))

		journals = list(self.journal_ids.mapped('id'))
		len_journals = len(journals or '')
		if len(self.journal_ids):
			domain.append(('journal_id.id' , self.journal_option or 'in', journals))

		moves = list(self.move_ids.mapped('id'))
		len_moves = len(moves or '')
		if len(moves):
			domain.append(('id' ,self.move_option or 'in', moves))

		currencys = list(self.currency_ids.mapped('id'))
		len_currencys = len(currencys or '')
		if len(currencys):
			domain.append(('currency_id.id' ,self.currency_option or 'in', currencys))

			
		return domain



	def _periodo_fiscal(self):
		periodo = "%s%s00" % (self.fiscal_year or 'YYYY', self.fiscal_month or 'MM')
		return periodo

	#####################
	def type_document_parent(self,invoice):
		parent_type=''
		if invoice.reversed_entry_id:
			parent_type= invoice.reversed_entry_id.journal_id.invoice_type_code_id or ''
		return parent_type

	def alarm_fecha_periodo(self):
		for rec in self:
			if rec.fecha:
				if not rec.date_from or not rec.date_to:
					raise UserError(_('NO SE PUEDE GENERAR EL LIBRO!!\nLos campos: Fecha Desde y Fecha Hasta son obligatorios.'))
			elif rec.periodo:
				if not rec.fiscal_year or not rec.fiscal_month:
					raise UserError(_('NO SE PUEDE GENERAR EL LIBRO!!\nLos campos: Año y mes Fiscal son obligatorios.'))
			else:
				raise UserError(_('NO SE PUEDE GENERAR EL LIBRO!!\nElija la opción Fecha o Periodo para generar el Libro.'))


	def generar_libro(self):

		self.alarm_fecha_periodo()
		
		registro=[]
		registro_no_domiciliados=[]
		registro_recibo_honorarios=[]

		self.state='open'
		self.ple_purchase_line_ids.unlink()
		self.ple_purchase_line_no_domiciliados_ids.unlink()
		self.ple_purchase_line_recibo_honorarios_ids.unlink()
		
		####################################################
		for line in self._get_datas(self._get_domain()):

			if (str(line.journal_id.invoice_type_code_id or '').strip() in ['02']) or (self.type_document_parent(line) in ['02']):
				registro_recibo_honorarios.append((0,0,{'move_id':line.id}))
			else:
				#str(line.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or '').strip() not in  ['0']
				if str(line.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or '').strip() not in  ['0'] and\
					(str(line.journal_id.invoice_type_code_id or '').strip() not in ['91','97','98']):
					registro.append((0,0,{'move_id':line.id}))

				elif str(line.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or '').strip() in ['0'] and\
					(str(line.journal_id.invoice_type_code_id or '').strip() in ['00','91','97','98']):
					registro_no_domiciliados.append((0,0,{'move_id':line.id}))
		#####################################################

		self.ple_purchase_line_ids = registro
		self.ple_purchase_line_no_domiciliados_ids=registro_no_domiciliados
		self.ple_purchase_line_recibo_honorarios_ids=registro_recibo_honorarios



	def _convert_object_date(self, date):
		# parametro date que retorna un valor vacio o el formato 01/01/2100 dia/mes/año
		if date:
			return date.strftime('%d/%m/%Y')
		else:
			return ''