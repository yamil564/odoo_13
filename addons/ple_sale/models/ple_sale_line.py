import pytz
import calendar
import base64
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta
from odoo.addons import ple_base as tools

import logging
_logger=logging.getLogger(__name__)
class PleSaleLine(models.Model):
	_name='ple.sale.line'

	ple_sale_id=fields.Many2one("ple.sale",string="id PLE" , ondelete='cascade' , readonly=True )

	###### CAMPO PRINCIPAL O CAMPO ROOT !!!
	invoice_id=fields.Many2one("account.move" , string="Documento" , ondelete="cascade",readonly= True)	
	
	invoice_id_2=fields.Many2one("account.move", string="Documento de origen" , compute='compute_invoice_id_2' ,  store=True , readonly=True )
	partner_id=fields.Many2one("res.partner", string="Proveedor" , compute='compute_partner_id', store=True) 
	asiento_contable=fields.Char(string="Nombre del asiento contable", compute='_compute_campo_asiento_contable' , store=True , readonly=True) # YA 
	m_correlativo_asiento_contable=fields.Char(string="M-correlativo asiento contable" ,compute='_compute_campo_m_correlativo_asiento_contable' ,store=True ,readonly=True) # YA !!
	fecha_emision_comprobante=fields.Date(string="Fecha emisión Comprobante" , compute='_compute_campo_fecha_emision_comprobante',store=True ,readonly=True) # YA
	fecha_vencimiento=fields.Date(string="Fecha de vencimiento" , compute='_compute_campo_fecha_vencimiento' ,store=True ,readonly=True) # YA 
	tipo_comprobante=fields.Char(string="Tipo de Comprobante" , compute='_compute_campo_tipo_comprobante', store = True , readonly = True) ## YA
	serie_comprobante=fields.Char(string="Serie del Comprobante"  , compute='_compute_campo_serie_comprobante', store=True,readonly=True) ## YA
	numero_comprobante=fields.Char(string="Número Comprobante",  compute='_compute_campo_numero_comprobante' , store=True,readonly=True) # YA
	ventas_importe_total_maquina_registradora=fields.Float(string="Importe Máquina Registradora sin Crédito Fiscal" ,default=0.00 ,readonly=True) ##YA 
	tipo_documento_cliente=fields.Char(string="Tipo Documento Cliente" ,  compute='_compute_campo_tipo_documento_cliente', store=True , readonly=True)# YA !!!
	numero_documento_cliente=fields.Char(string="Número Documento Identidad Cliente" , compute='_compute_campo_numero_documento_cliente',store=True,readonly=True) ## YA
	razon_social=fields.Char(string="Razón Social Cliente" ,compute='_compute_campo_razon_social' ,store=True,readonly=True)# YA 

	ventas_valor_facturado_exportacion = fields.Float(string="Valor Facturado Exportación" ,compute='_compute_campo_ventas_valor_facturado_exportacion' ,store=True,readonly=True) # YA
	ventas_base_imponible_operacion_gravada = fields.Float(string="Base Imponible Operación Gravada" ,compute='_compute_campo_ventas_base_imponible_operacion_gravada' ,store=True,readonly=True) #YA
	ventas_descuento_base_imponible = fields.Float(string="Descuento Base Imponible" ,default=0.00 ,readonly=True) # YA
	ventas_igv = fields.Float(string="IGV y/o Impuesto Promoción Municipal" ,compute='_compute_campo_impuestos' ,store=True,readonly=True) # YA
	ventas_descuento_igv = fields.Float(string="Descuento del IGV" , default=0.00 ,readonly=True) # YA
	ventas_importe_operacion_exonerada = fields.Float(string="Importe total operación exonerada" ,compute='_compute_campo_ventas_importe_operacion_exonerada' ,store=True,readonly=True) # YA
	ventas_importe_operacion_inafecta = fields.Float(string="Importe total operación inafecta" ,compute='_compute_campo_ventas_importe_operacion_inafecta' ,store=True,readonly=True) # YA
	isc=fields.Float(string="ISC",default=0.00 , readonly=False) # YA 
	ventas_base_imponible_arroz_pilado=fields.Float(string="Base Imponible Arroz Pilado",default=0.00,readonly=True) # YA
	ventas_impuesto_arroz_pilado = fields.Float(string="Impuesto Arroz Pilado",default=0.00 ,readonly=True)# YA
	
	## AUMENTANDO EL IMPUESTO A LAS BOLSAS DE PLASTICO 
	impuesto_consumo_bolsas_plastico=fields.Float(string="Impuesto al Consumo de las Bolsas de Plástico",default=0.00 ,readonly=True, compute='_compute_campo_impuestos' ) # YA
	otros_impuestos=fields.Float(string="Otros conceptos tributarios",default=0.00 ,readonly=True, compute='_compute_campo_impuestos' ) # YA
	importe_total_comprobante=fields.Float(string="Importe Total comprobante", compute='_compute_campo_importe_total_comprobante' , store=True , readonly=True) # YA 
	codigo_moneda=fields.Char(string="Código Moneda" , compute='_compute_campo_codigo_moneda' , store=True , readonly=True) #YA
	tipo_cambio=fields.Float(string="Tipo de Cambio", compute='_compute_campo_tipo_cambio', store=True , readonly=True, digits = (12,3))

	fecha_emision_original=fields.Date(string="Fecha Emision Comprobante Original", compute='_compute_campo_fecha_emision_original' ,store=True , readonly=True)
	tipo_comprobante_original=fields.Char(string="Tipo Comprobante Original", compute='_compute_campo_tipo_comprobante_original' , store=True  , readonly=True)
	serie_comprobante_original=fields.Char(string="Serie Comprobante Original", compute='_compute_campo_serie_comprobante_original' ,store=True , readonly=True)
	numero_comprobante_original=fields.Char(string="Nùmero Comprobante Original", compute='_compute_campo_numero_comprobante_original', store=True , readonly=True)
	
	ventas_identificacion_contrato_operadores = fields.Char(string="Identificación Contrato Operadores Irregulares" ,readonly=True)
	error_1 = fields.Char(string="Error Tipo 1" , readonly=True)
	ventas_indicador_comprobantes_medios_pago = fields.Char(string="Indicador Comprobantes cancelados con medios de pago" ,readonly=True)
	oportunidad_anotacion=fields.Char(string="Oportunidad Anotación",compute='_compute_campo_oportunidad_anotacion', store=True ,readonly=True)


	@api.depends('invoice_id')
	def _compute_campo_asiento_contable(self):
		for rec in self:
			if rec.invoice_id:
				rec.asiento_contable=rec.invoice_id.name or ''
	

	@api.depends('invoice_id')
	def _compute_campo_m_correlativo_asiento_contable(self):
		for rec in self:
			if rec.invoice_id:
				rec.m_correlativo_asiento_contable='M1'


	
	@api.depends('invoice_id')
	def _compute_campo_fecha_emision_comprobante(self):
		for rec in self:
			if rec.invoice_id:
				rec.fecha_emision_comprobante=rec.invoice_id.invoice_date or ''
	


	@api.depends('invoice_id')
	def _compute_campo_fecha_vencimiento(self):
		for rec in self:
			if rec.invoice_id:
				rec.fecha_vencimiento=rec.invoice_id.invoice_date or ''
			else:
				rec.fecha_vencimiento=''


	@api.depends('invoice_id')
	def _compute_campo_tipo_comprobante(self):
		for rec in self:
			if rec.invoice_id and rec.invoice_id.journal_id:
				rec.tipo_comprobante=rec.invoice_id.journal_id.invoice_type_code_id or ''
			else:
				rec.tipo_comprobante=''



	@api.depends('invoice_id')
	def _compute_campo_serie_comprobante(self):
		for rec in self:
			if rec.invoice_id and rec.invoice_id.name:
				prefix_code=rec.invoice_id.name.split('-')
				if len(prefix_code)>1:
					rec.serie_comprobante= prefix_code[0] or ''
				else:
					rec.serie_comprobante= '-'
			else:
				rec.serie_comprobante = '-'

	
	@api.depends('invoice_id')
	def _compute_campo_numero_comprobante(self):
		for rec in self:
			if rec.invoice_id and rec.invoice_id.name:
				invoice_number=rec.invoice_id.name.split('-')
				if len(invoice_number)>1:
					rec.numero_comprobante= invoice_number[1] or ''
				else:
					rec.numero_comprobante= invoice_number
			else:
				rec.numero_comprobante = ''

	
	@api.depends('invoice_id')
	def compute_partner_id(self):
		for rec in self:
			if rec.invoice_id:
				rec.partner_id= rec.invoice_id.partner_id or None


	
	@api.depends('invoice_id')
	def _compute_campo_tipo_documento_cliente(self):
		for rec in self:
			if rec.invoice_id and rec.invoice_id.state not in ['cancel']:
				rec.tipo_documento_cliente=rec.invoice_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or ''
			elif rec.invoice_id.state in ['cancel']:
				rec.tipo_documento_cliente= ''


	@api.depends('invoice_id')
	def _compute_campo_numero_documento_cliente(self):
		for rec in self:
			if rec.invoice_id and rec.invoice_id.state not in ['cancel']:
				rec.numero_documento_cliente=rec.invoice_id.partner_id.vat or ''
			elif rec.invoice_id.state in ['cancel']:
				rec.numero_documento_cliente='00000000'

	@api.depends('invoice_id')
	def _compute_campo_razon_social(self):
		for rec in self:
			if rec.invoice_id and rec.invoice_id.state not in ['cancel']:
				rec.razon_social=rec.invoice_id.partner_id.name or ''
			elif rec.invoice_id.state in ['cancel']:
				rec.razon_social="ANULADO"


	@api.depends('invoice_id')
	def _compute_campo_ventas_valor_facturado_exportacion(self):
		for rec in self:
			if rec.invoice_id:
				rec.ventas_valor_facturado_exportacion=format(rec.invoice_id.total_venta_exportacion*rec.tipo_cambio*( (rec.invoice_id.type=="out_refund")*(-2)+1 )*((rec.invoice_id.state!='cancel')*1),".2f")


	@api.depends('invoice_id','tipo_cambio')
	def	_compute_campo_ventas_base_imponible_operacion_gravada(self):
		for rec in self:
			if rec.invoice_id:
				rec.ventas_base_imponible_operacion_gravada=format(rec.invoice_id.total_venta_gravado*rec.tipo_cambio*( (rec.invoice_id.type=="out_refund")*(-2)+1 )*((rec.invoice_id.state!='cancel')*1),".2f")


	@api.depends('invoice_id')
	def _compute_campo_ventas_importe_operacion_exonerada(self):
		for rec in self:
			if rec.invoice_id:
				rec.ventas_importe_operacion_exonerada = format(rec.invoice_id.total_venta_exonerada*rec.tipo_cambio*( (rec.invoice_id.type=="out_refund")*(-2)+1 )*((rec.invoice_id.state!='cancel')*1),".2f")

	@api.depends('invoice_id')
	def _compute_campo_ventas_importe_operacion_inafecta(self):
		for rec in self:
			if rec.invoice_id:
				rec.ventas_importe_operacion_inafecta = format(rec.invoice_id.total_venta_inafecto*rec.tipo_cambio*( (rec.invoice_id.type=="out_refund")*(-2)+1 )*((rec.invoice_id.state!='cancel')*1),".2f")

	##########################################
	@api.depends('invoice_id','tipo_cambio')
	def _compute_campo_impuestos(self):
		for rec in self:
			if rec.invoice_id:
				rec.ventas_igv=format(rec.invoice_id.amount_tax*rec.tipo_cambio*( (rec.invoice_id.type=="out_refund")*(-2)+1 )*((rec.invoice_id.state!='cancel')*1),".2f")
				rec.otros_impuestos= 0.00
				rec.impuesto_consumo_bolsas_plastico = 0.00


	@api.depends('invoice_id')
	def _compute_campo_tipo_cambio(self):
		for rec in self:
			if rec.invoice_id.type=="out_refund":
				if rec.invoice_id.reversed_entry_id:
					rec.tipo_cambio=format(rec.invoice_id.reversed_entry_id.exchange_rate_day or 0.00,".3f")
				else:
					rec.tipo_cambio=format(rec.invoice_id.exchange_rate_day or 0.00,".3f")
			else:
				rec.tipo_cambio=format(rec.invoice_id.exchange_rate_day,".3f")


	@api.depends('invoice_id','tipo_cambio')
	def _compute_campo_importe_total_comprobante(self):
		for rec in self:
			if rec.invoice_id:
				rec.importe_total_comprobante=format(rec.invoice_id.amount_total*rec.tipo_cambio*( (rec.invoice_id.type=="out_refund")*(-2)+1 )*((rec.invoice_id.state!='cancel')*1),".2f")


	@api.depends('invoice_id')
	def _compute_campo_codigo_moneda(self):
		for rec in self:
			if rec.invoice_id:
				rec.codigo_moneda=rec.invoice_id.currency_id.name or ''

	@api.depends('invoice_id')
	def compute_invoice_id_2(self):
		for rec in self:
			if rec.invoice_id:
				if rec.invoice_id.reversed_entry_id:
					rec.invoice_id_2= rec.invoice_id.reversed_entry_id



	############################################################
	@api.depends('invoice_id_2')
	def _compute_campo_fecha_emision_original(self):
		for rec in self:
			if rec.invoice_id_2:
				rec.fecha_emision_original= rec.invoice_id_2.invoice_date
			else:
				rec.fecha_emision_original= ''
			
			#rec.fecha_emision_original= ''

	@api.depends('invoice_id_2')
	def _compute_campo_tipo_comprobante_original(self):
		for rec in self:
			rec.tipo_comprobante_original=''
			if rec.invoice_id_2 and rec.invoice_id_2.journal_id:
				rec.tipo_comprobante_original= rec.invoice_id_2.journal_id.invoice_type_code_id or ''
			else:
				rec.tipo_comprobante_original=''
			
		

	@api.depends('invoice_id_2')
	def _compute_campo_serie_comprobante_original(self):
		for rec in self:
			if rec.invoice_id_2 and rec.invoice_id_2.name:
				prefix_code=rec.invoice_id_2.name.split('-')

				if len(prefix_code)>1:
					rec.serie_comprobante_original = prefix_code[0] or ''

				else:
					rec.serie_comprobante_original= ''
			

	@api.depends('invoice_id_2')
	def _compute_campo_numero_comprobante_original(self):
		for rec in self:
			if rec.invoice_id_2 and rec.invoice_id_2.name:
				invoice_number = rec.invoice_id_2.name.split('-')
				if len(invoice_number)>1:
					rec.numero_comprobante_original= invoice_number[1]
				else:
					rec.numero_comprobante_original= invoice_number
			else:			
				rec.numero_comprobante_original= ''
	###########################################################


	@api.depends('invoice_id','ple_sale_id')
	def _compute_campo_oportunidad_anotacion(self):
		for rec in self:
			if rec.invoice_id:
				valor_campo=''

				if rec.invoice_id.state not in ['cancel'] and rec.invoice_id.date and rec.invoice_id.invoice_date and \
					tools.getDateYYYYMM(rec.invoice_id.date) == tools.getDateYYYYMM(rec.invoice_id.invoice_date):
					
					if rec.invoice_id.journal_id.invoice_type_code_id=='03':
						valor_campo='1'
					else:

						if rec.invoice_id.amount_igv==0.00:
							if rec.invoice_id.total_venta_exportacion:
								valor_campo='1'
							else:
								valor_campo='0'

						elif rec.invoice_id.amount_igv>0.00:
							valor_campo='1'

				elif rec.invoice_id.state not in ['cancel'] and rec.invoice_id.date and rec.invoice_id.invoice_date and \
					tools.getDateYYYYMM(rec.invoice_id.date) > tools.getDateYYYYMM(rec.invoice_id.invoice_date):
					valor_campo='8'

				elif rec.invoice_id.state=='cancel' and rec.invoice_id.invoice_date and rec.ple_sale_id:

					anio=rec.ple_sale_id.fiscal_year
					mes = rec.ple_sale_id.fiscal_month
					
					if len(mes or '')==1:
						mes="0%s"%(mes)
					
					if "%s%s"%(anio,mes)==tools.getDateYYYYMM(rec.invoice_id.invoice_date):
						valor_campo='2'
					#elif "%s%s"%(anio,mes)>tools.getDateYYYYMM(rec.invoice_id.date):
					#	valor_campo='8'  ## Se esta en duda que un comprobante anulado entre en periodos posteriores.

				rec.oportunidad_anotacion=valor_campo
