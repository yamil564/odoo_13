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

	ple_purchase_line_ids=fields.One2many('ple.purchase.line','ple_purchase_id',string="Registros de compra" ,readonly=True, states={'draft': [('readonly', False)]})
	ple_purchase_line_no_domiciliados_ids=fields.One2many('ple.purchase.line','ple_purchase_id_no_domiciliados',string="Registros de compra" , readonly=True, states={'draft': [('readonly', False)]})
	ple_purchase_line_recibo_honorarios_ids=fields.One2many('ple.purchase.line','ple_purchase_id_recibo_honorarios',string="Registros de compra" , readonly=True, states={'draft': [('readonly', False)]})
	
	identificador_operaciones = fields.Selection(selection=[('0','Cierre de operaciones'),('1','Empresa operativa'),('2','Cierre de libro')],
		string="Identificador de operaciones", required=True, default="1")
	identificador_libro = fields.Selection(selection='available_formats_purchase_sunat', string="Identificador de libro" )
	print_order = fields.Selection(default="date")

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
	imprimir_recibo_honorarios=fields.Boolean(string="Incluir Recibos por Honorarios", default=False)

	fecha=fields.Boolean(string="Fecha" ,readonly=True , states={'draft': [('readonly', False)]})
	periodo=fields.Boolean(string="Periodo" ,readonly=True , states={'draft': [('readonly', False)]})

	date_from=fields.Date(string="Desde:" ,readonly=True , states={'draft': [('readonly', False)]})
	date_to=fields.Date(string="Hasta:" ,readonly=True , states={'draft': [('readonly', False)]})

	fecha_inicio=''
	fecha_fin=''
	############## CHECK para indicar si se incluye o no registros anteriores no declarados
	
	incluir_anteriores_no_declarados = fields.Boolean(string="Incluir registros anteriores no declarados", default=False)

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

			
