import calendar
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import xlsxwriter
from odoo.exceptions import UserError , ValidationError

import logging
_logger=logging.getLogger(__name__)

options = [('in','Esta en'),('not in','No esta en')]

class PleSale(models.Model):
	_name='ple.sale'
	_inherit='ple.base'
	_description = "Modulo PLE Libros de Ventas"

	ple_sale_line_ids=fields.One2many('ple.sale.line','ple_sale_id',string="Registros de venta")


	partner_ids = fields.Many2many('res.partner','ple_sale_partner_rel','partner_id','ple_sale_id_1' ,string="Socio" ,readonly=True , states={'draft': [('readonly', False)]})
	journal_ids = fields.Many2many('account.journal','ple_sale_journal_rel','journal_id','ple_sale_id_3',string="Diario" ,readonly=True , states={'draft': [('readonly', False)]})
	move_ids = fields.Many2many('account.move','ple_sale_move_rel','move_id','ple_sale_id_4',string='Factura' ,readonly=True , states={'draft': [('readonly', False)]})
	currency_ids = fields.Many2many('res.currency','ple_sale_currency_rel','currency_id','ple_sale_id_6', string="Moneda" ,readonly=True , states={'draft': [('readonly', False)]})

	####### Select Option Filter
	partner_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	journal_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	move_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	currency_option=fields.Selection(selection=options , string="",readonly=True , states={'draft': [('readonly', False)]})
	#######################

	fecha=fields.Boolean(string="Fecha" ,readonly=True , states={'draft': [('readonly', False)]})
	periodo=fields.Boolean(string="Periodo" ,readonly=True , states={'draft': [('readonly', False)]})

	date_from=fields.Date(string="Desde:" ,readonly=True , states={'draft': [('readonly', False)]})
	date_to=fields.Date(string="Hasta:" ,readonly=True , states={'draft': [('readonly', False)]})

	fecha_inicio=''
	fecha_fin=''

	############## CHECK para indicar si se incluye o no registros anteriores no declarados
	
	incluir_anteriores_no_declarados = fields.Boolean(string="Incluir registros anteriores no declarados", default=False)

	###############################
	_sql_constraints = [
		('fiscal_month', 'unique(fiscal_month,fiscal_year,company_id)',  'Este periodo para el PLE ya existe , revise sus registros de PLE creados!!!'),
	]

	######################################

	def open_wizard_print_form(self):
		res = super(PleSale,self).open_wizard_print_form()

		view = self.env.ref('ple_sale.view_wizard_printer_ple_sale_form')
		if view:

			return {
				'name': _('FORMULARIO DE IMPRESIÓN DEL LIBRO PLE'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'wizard.printer.ple.sale',
				'views': [(view.id,'form')],
				'view_id': view.id,
				'target': 'new',
				'context': {
					'default_ple_sale_id': self.id,
					'default_company_id' : self.company_id.id,}}

	######################################
	def button_view_tree_ple_sale_lines(self):
		self.ensure_one()
		view = self.env.ref('ple_sale.view_ple_sale_line_tree')
		if self.ple_sale_line_ids:
			diccionario = {
				'name': 'Libro PLE Ventas',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'ple.sale.line',
				'view_id': view.id,
				'views': [(view.id,'tree')],
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', [i.id for i in self.ple_sale_line_ids] or [])],
				'context':{
					'search_default_filter_cliente':1,
					'search_default_filter_tipo_comprobante':1,
					}
			}
			return diccionario
	###########################################


	def name_get(self):
		result = []
		for ple in self:
			if ple.periodo:
				result.append((ple.id, ple._periodo_fiscal() or 'New'))
			elif ple.fecha:
				result.append((ple.id,"%s-%s"%(self._convert_object_date(ple.date_from),self._convert_object_date(ple.date_to)) or 'New'))
			else:
				result.append((ple.id,'New'))
		return result


	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		args = args or []
		if self.periodo:
			recs = self.search([('fiscal_month', operator, name),('fiscal_year', operator, name)] + args, limit=limit)
		elif self.fecha:
			recs = self.search([('date_from', operator, name),('date_to', operator, name)] + args, limit=limit)
		return recs.name_get()
	###############################################

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

	def unlink (self):
		for line in self:
			for line2 in line.ple_sale_line_ids:
				line2.invoice_id.write({'declared_ple':False})
			return super(PleSale, line).unlink()



	def criterios_impresion(self):
		res = super(PleSale, self).criterios_impresion() or []
		res += [('invoice_number',u'N° de documento'),('num_serie',u'N° de serie'),('table10_id','Tipo de documento')]
		return res


	def _action_confirm_ple(self):
		array_id=[]
		for line in self.ple_sale_line_ids :
			array_id.append(line.invoice_id.id)
		super(PleSale ,self)._action_confirm_ple('account.move' ,array_id,{'declared_ple':True})

	def _get_datas(self, domain):
		# orden= []

		return self._get_query_datas('account.move', domain, "invoice_date asc , name asc")


	##############################################
	def _get_domain(self):
		#####################
		if self.fecha:
			self.fecha_inicio=self.date_from
			self.fecha_fin=self.date_to
			
		elif self.periodo:
			if self.incluir_anteriores_no_declarados:
				self.fecha_inicio= "%s-01-01" %(self.fiscal_year)
				self.fecha_fin= self._get_end_date()
			else:
				self.fecha_inicio= self._get_star_date()
				self.fecha_fin= self._get_end_date()
		#####################

		domain = [
			('date','>=',self.fecha_inicio),
			('date','<=',self.fecha_fin),
			('type','in',['out_invoice','out_refund']),
			('state','not in',['draft'])
			]


		partners=tuple(self.partner_ids.mapped('id'))
		len_partners = len(partners or '')
		if len_partners:
			domain.append(('partner_id.id' , self.partner_option or 'in', partners))

		journals = tuple(self.journal_ids.mapped('id'))
		len_journals = len(journals or '')
		if len(self.journal_ids):
			domain.append(('journal_id.id' ,self.journal_option or 'in', journals))

		moves = tuple(self.move_ids.mapped('id'))
		len_moves = len(moves or '')
		if len(moves):
			domain.append(('id' ,self.move_option or 'in', moves))

		currencys = tuple(self.currency_ids.mapped('id'))
		len_currencys = len(currencys or '')
		if len(currencys):
			domain.append(('currency_id.id' ,self.currency_option or 'in', currencys))


		return domain


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
		
		self.state='open'
		self.ple_sale_line_ids.unlink()
		for line in self._get_datas(self._get_domain()):
			#if ((line.prefix_code and line.invoice_number) or line.document_id):
			registro.append((0,0,{'invoice_id':line.id}))
		self.ple_sale_line_ids = registro



	def _convert_object_date(self, date):
		if date:
			return date.strftime('%d/%m/%Y')
		else:
			return ''

	############################################################################################ 