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
class PlePurchaseLine(models.Model):
	_name='ple.purchase.line'

	ple_purchase_id=fields.Many2one("ple.purchase",string="id PLE", ondelete="cascade" )

	ple_purchase_id_no_domiciliados = fields.Many2one("ple.purchase",string="id PLE" , ondelete="cascade")
	ple_purchase_id_recibo_honorarios=fields.Many2one("ple.purchase",string="id PLE",ondelete="cascade")
	# ple_purchase_id_recibo_honorarios
	###### CAMPO PRINCIPAL O CAMPO ROOT !!!
	move_id=fields.Many2one("account.move" , string="Documento" , readonly= True)

	journal_id=fields.Many2one("account.journal" , string="Diario" , compute='compute_journal_id', store=True)
	partner_id=fields.Many2one("res.partner", string="Proveedor" , compute='compute_partner_id', store=True) 
	currency_id=fields.Many2one("res.currency",string="Código moneda" , compute='compute_currency_id' ,store=True) 
	
	move_id_2=fields.Many2one("account.move", string="Documento de origen" , compute='compute_move_id_2' ,store=True) 

	partner_sunat_id=fields.Many2one("l10n_latam.identification.type" , string="Codigo documento identidad proveedor" , compute="compute_partner_sunat_id", store=True)

	asiento_contable=fields.Char(string="Nombre del asiento contable", compute='_compute_campo_asiento_contable' , store=True , readonly=True)
	m_correlativo_asiento_contable=fields.Char(string="M-correlativo asiento contable" ,compute='_compute_campo_m_correlativo_asiento_contable' ,store=True)
	fecha_emision_comprobante=fields.Date(string="Fecha emisión Comprobante" , compute='_compute_campo_fecha_emision_comprobante',store=True)
	fecha_vencimiento=fields.Date(string="Fecha de vencimiento" , compute='_compute_campo_fecha_vencimiento', store=True)
		
	tipo_comprobante=fields.Char(string="Tipo de Comprobante" , compute='_compute_campo_tipo_comprobante', store = True, readonly=True)
	serie_comprobante=fields.Char(string="Serie del Comprobante"  , compute='_compute_campo_serie_comprobante', store=True)
	
	anio_emision_DUA=fields.Char(string="Año Emisión DUA" , compute='_compute_campo_anio_emision_DUA' , store=True, default='0') 
	numero_comprobante=fields.Char(string="Número Comprobante",  compute='_compute_campo_numero_comprobante', store=True)
		
	operaciones_sin_igv=fields.Float(string="Operaciones sin igv" ,default=0.00)
	tipo_documento_proveedor=fields.Char(string="Tipo Documento Proveedor" ,  compute='_compute_campo_tipo_documento_proveedor', store=True , readonly=True)# 
	ruc_dni=fields.Char(string="RUC o DNI Proveedor" , compute='_compute_campo_ruc_dni',store=True)
		
	razon_social=fields.Char(string="Razón Social" ,compute='_compute_campo_razon_social',store=True) # ,
		
	base_imponible_igv_gravadas=fields.Float(string="Base crédito fiscal gravadas" ,compute='_compute_campo_base_imponible_igv_gravadas', store=True , readonly = True )
	monto_igv_1=fields.Float(string="Monto IGV", compute='_compute_campo_impuestos' ,store=True, readonly = True)
	base_imponible_igv_no_gravadas=fields.Float(string="base crédito fiscal no gravadas",default=0.00)
	monto_igv_2=fields.Float(string="Monto IGV",default=0.00)
	base_imponible_no_igv=fields.Float(string="Base sin Crédito fiscal",default=0.00 ) 
	monto_igv_3=fields.Float(string="Monto IGV",default=0.00 ) 
	valor_no_gravadas=fields.Float(string="Valor adquisiciones no gravadas", compute='_compute_campo_valor_no_gravadas',store=True) 
	isc=fields.Float(string="ISC",default=0.00 ) 

	impuesto_consumo_bolsas_plastico=fields.Float(string="Impuesto al Consumo de las Bolsas de Plástico",default=0.00 ,readonly=True, compute='_compute_campo_impuestos' ) # YA

	otros_impuestos=fields.Float(string="Otros Impuestos",compute='_compute_campo_impuestos',store=True) # , readonly=False , states={'send': [('readonly', True)]})

	importe_adquisiciones_registradas=fields.Float(string="Importe Adquisiciones Registradas", compute='_compute_campo_importe_adquisiciones_registradas' , store=True , readonly=True)
	codigo_moneda=fields.Char(string="Código Moneda" , compute='_compute_campo_codigo_moneda' , store=True, readonly=True) #,inverse='inverse_compute_campo_24', store=True)
	tipo_cambio=fields.Float(string="Tipo de Cambio", compute='_compute_campo_tipo_cambio',store=True , digits = (12,3) ) # , readonly=False ,
	fecha_emision_original=fields.Date(string="Fecha Emision Comprobante Original", compute='_compute_campo_fecha_emision_original' ,store=True) # , readonly=False , states={'send': [('readonly', True)]})
	tipo_comprobante_original=fields.Char(string="Tipo Comprobante Original", compute='_compute_campo_tipo_comprobante_original' ,store=True , readonly = True)
	serie_comprobante_original=fields.Char(string="Serie Comprobante Original", compute='_compute_campo_serie_comprobante_original' ,store=True) # ,
	codigo_dep_aduanera=fields.Char(string="Código Dependencia Aduanera" ) #, readonly=False , states={'send': [('readonly', True)]})
	numero_comprobante_original=fields.Char(string="Número Comprobante Original", compute='_compute_campo_numero_comprobante_original' ,store=True )
	fecha_detraccion=fields.Date(string="Fecha Detracción")#,compute='_compute_campo_fecha_detraccion' , store=True ) # ,
	numero_detraccion=fields.Char(string="Número Detracción")#,compute='_compute_campo_numero_detraccion' ,store=True ) #, readonly=False , states={'send': [('readonly', True)]})
	marca_retencion=fields.Char(string="Marca Retención") # , readonly=False , states={'send': [('readonly', True)]})
	clasificacion_bienes=fields.Char(string="Clasificación Bienes Adquiridos" ) #, readonly=False , states={'send': [('readonly', True)]})
	identificacion_contrato=fields.Char(string="Identificación Contrato" ) #, readonly=False , states={'send': [('readonly', True)]})
	error_1=fields.Char(string="Error Tipo 1")
	error_2=fields.Char(string="Error Tipo 2" )
	error_3=fields.Char(string="Error Tipo 3") 
	error_4=fields.Char(string="Error Tipo 4" ) 
	indicador_comprobantes=fields.Char(string="Indicador Comprobantes" ) 
	oportunidad_anotacion=fields.Char(string="Oportunidad Anotación Domiciliado",compute='_compute_campo_oportunidad_anotacion', store=True) 
	############################################################################################################
	partner_country_id=fields.Many2one('res.country',string="Pais residencia sujeto no domiciliado" , compute="compute_partner_country_id" , inverse='inverse_compute_partner_country_id' , store=True) #,
	

	############################################################################################################
	############## CAMPOS EXCLUSIVOS DE NO DOMICILIADOS !!!!!
	no_domiciliado_m_correlativo_asiento_contable=fields.Char(string="M-correlativo asiento contable",
		compute='_compute_campo_m_correlativo_asiento_contable' ,store=True) #,
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_valor_adquisiciones=fields.Float(string="Valor Adquisiciones" ,default=0.00 , store=True)#,
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_otros_conceptos_adicionales=fields.Float(string="Conceptos Adicionales" ,default=0.00, store=True) #,
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_tipo_comprobante_credito_fiscal=fields.Char(string="Tipo Comprobante Crédito fiscal", store=True)#,
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_serie_comprobante_credito_fiscal=fields.Char(string="Serie Comprobante Crédito fiscal", store=True)#,
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_numero_comprobante_pago_impuesto=fields.Char(string="Número Comprobante Pago Impuesto", store=True)#,
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_pais_residencia=fields.Char(string="Código pais residencia del no domiciliado",
		compute='_compute_campo_no_domiciliado_pais_residencia',store=True)
		# , readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_domicilio=fields.Char(string="Domicilio en el extranjero" ,
		compute='_compute_campo_no_domiciliado_domicilio',store=True)
		# readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_numero_identificacion=fields.Char(string="Número Identificación del no domiciliado",
		compute='_compute_campo_no_domiciliado_numero_identificacion',store=True )
		#, Readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_identificacion_beneficiario=fields.Char(string="Número Identificación beneficiario", store=True) # , readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_razon_social_beneficiario=fields.Char(string="Razón social beneficiario", store=True) # , readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_pais_beneficiario=fields.Char(string="Pais residencia beneficiario", store=True) # , readonly=False , states={'send': [('readonly', True)]})
	no_domiciliado_vinculo_entre_contribuyente_residente=fields.Char(string="Vinculo contribuyente-residente extranjero",store=True) 
	no_domiciliado_renta_bruta = fields.Float(string="Renta Bruta", store=True ,default=0.00) 
	no_domiciliado_deduccion_bienes = fields.Float(string="Deducción/Costo bienes capital", store=True , default = 0.00 ) 
	no_domiciliado_renta_neta = fields.Float(string="Renta Neta", store=True , default=0.00 ) 
	no_domiciliado_tasa_retencion = fields.Float(string="Tasa de retención", store=True , default=0.00 ) 
	no_domiciliado_impuesto_retenido = fields.Float(string="Impuesto retenido", store=True , default=0.00 )
	no_domiciliado_convenios =  fields.Char(string="Convenios para evitar doble imposición" , default='00', store=True ) 
	no_domiciliado_exoneracion = fields.Char(string="Exoneración aplicada", store=True ) 
	no_domiciliado_tipo_renta = fields.Char(string="Tipo de Renta" , default='00', store=True) 
	no_domiciliado_modalidad_servicio_prestado= fields.Char(string="Modalidad servicio prestado", store=True ) 
	no_domiciliado_aplicacion_ley_impuesto_renta = fields.Char(string="Aplicación Art. 76°" , store=True ) 
	no_domiciliado_oportunidad_anotacion= fields.Char(string="Oportunidad Anotación no Domiciliado",
		compute='_compute_campo_oportunidad_anotacion',store=True)

	###################################################################3
	### Campos domiciliados y algunos no domiciliados

	@api.depends('move_id')
	def compute_journal_id(self):
		for rec in self:
			if rec.move_id:
				rec.journal_id=rec.move_id.journal_id or None
			else:
				rec.journal_id= None

	@api.depends('move_id','partner_id')
	def compute_partner_sunat_id(self):
		for rec in self:
			if rec.move_id and rec.partner_id:
				rec.partner_sunat_id = rec.partner_id.l10n_latam_identification_type_id or None
			else:
				rec.partner_sunat_id = None


	@api.depends('move_id')
	def compute_partner_id(self):
		for rec in self:
			if rec.move_id:
				rec.partner_id= rec.move_id.partner_id or None

	#####################################
	@api.depends('move_id')
	def compute_currency_id(self):
		for rec in self:
			if rec.move_id:
				rec.currency_id= rec.move_id.currency_id or None
			else:
				rec.currency_id= None

	######################################
	@api.depends('move_id')
	def compute_move_id_2(self):
		for rec in self:
			if rec.move_id and rec.move_id.reversed_entry_id:
				rec.move_id_2= rec.move_id.reversed_entry_id or None
			else:
				rec.move_id_2= None




	@api.depends('move_id')
	def _compute_campo_m_correlativo_asiento_contable(self):
		for rec in self:
			if rec.move_id:
				rec.m_correlativo_asiento_contable='M1'
				rec.no_domiciliado_m_correlativo_asiento_contable='M1'



	@api.depends('move_id')
	def _compute_campo_fecha_emision_comprobante(self):
		for rec in self:
			if rec.move_id:
				rec.fecha_emision_comprobante = rec.move_id.invoice_date or ''
	


	@api.depends('move_id','tipo_comprobante')
	def _compute_campo_anio_emision_DUA(self):
		for rec in self:
			if rec.move_id.journal_id and (rec.tipo_comprobante in ['50']):
				rec.anio_emision_DUA=str(rec.move_id.invoice_date.year)
			else:
				rec.anio_emision_DUA = '0'



	@api.depends('move_id')
	def _compute_campo_fecha_vencimiento(self):
		for rec in self:
			if rec.move_id:
				rec.fecha_vencimiento=rec.move_id.invoice_date_due or ''
			else:
				rec.fecha_vencimiento=''



	@api.depends('move_id')
	def _compute_campo_serie_comprobante(self):
		for rec in self:
			if rec.move_id and rec.move_id.prefix_code:
				rec.serie_comprobante= rec.move_id.prefix_code
			else:
				rec.serie_comprobante = '-'



	@api.depends('move_id')
	def _compute_campo_numero_comprobante(self):
		for rec in self:
			if rec.move_id and rec.move_id.inv_supplier_ref:
				rec.numero_comprobante=rec.move_id.invoice_number
			else:
				rec.numero_comprobante = '-'




	@api.depends('move_id','tipo_cambio')
	def _compute_campo_base_imponible_igv_gravadas(self):
		for rec in self:
			if rec.move_id:
				rec.base_imponible_igv_gravadas= format(rec.move_id.total_venta_gravado*rec.tipo_cambio*( (rec.move_id.type=="in_refund")*(-2)+1 ),".2f")


	@api.depends('move_id','tipo_cambio')
	def _compute_campo_impuestos(self):
		for rec in self:
			if rec.move_id:
				rec.monto_igv_1= format(rec.move_id.amount_igv*rec.tipo_cambio*( (rec.move_id.type=="in_refund")*(-2)+1 ),".2f")
				rec.otros_impuestos= 0.00
				rec.impuesto_consumo_bolsas_plastico = 0.00


	@api.depends('move_id','tipo_cambio')
	def _compute_campo_valor_no_gravadas(self):
		for rec in self:
			if rec.move_id:
				rec.valor_no_gravadas=(rec.move_id.total_venta_gratuito or rec.move_id.total_venta_inafecto or rec.move_id.total_venta_exonerada or 0.00)*rec.tipo_cambio*((rec.move_id.type=="in_refund")*(-2)+1 )


	@api.depends('move_id')
	def _compute_campo_otros_impuestos(self):
		for rec in self:
			rec.otros_impuestos=0.00

	######################################################
	@api.depends('move_id','tipo_cambio')
	def _compute_campo_importe_adquisiciones_registradas(self):
		for rec in self:
			if rec.move_id:
				rec.importe_adquisiciones_registradas=format(rec.move_id.amount_total*rec.tipo_cambio*( (rec.move_id.type=="in_refund")*(-2)+1 ),".2f")

	## FACTURA RECTIFICATIVA PROVEEDOR : in_refund
	@api.depends('move_id')
	def _compute_campo_tipo_cambio(self):
		for rec in self:
			if rec.move_id.type=="in_refund":
				if rec.move_id.reversed_entry_id:
					rec.tipo_cambio=format(rec.move_id.reversed_entry_id.exchange_rate_day or 0.00,".3f")
				else:
					rec.tipo_cambio=format(rec.move_id.exchange_rate_day or 0.00,".3f")
			else:
				rec.tipo_cambio=format(rec.move_id.exchange_rate_day,".3f")


	###########################
	def pertenece_periodo(self,date_1,date_2):
		if date_1 and date_2:
			
			if date_1.year == date_2.year and date_1.month == date_2.month:
				return 1
			
			elif date_1 + timedelta(days=365) >= date_2:
				return 2
			
			elif date_1 + timedelta(days=365) < date_2:
				return 3

	###########################
	## LA CONSULTA DEBERIA EVITAR QUE SE FILTREN DOCUMENTOS CON MAS DE 12 MESES DE ANTIGUEDAD

	@api.depends('move_id')
	def _compute_campo_oportunidad_anotacion(self):
		for rec in self:
			valor_campo_3='-'
			if rec.move_id:
				date_periodo = datetime.strptime("%s-%s-01"%(self.ple_purchase_id.fiscal_year,self.ple_purchase_id.fiscal_month),"%Y-%m-%d").date()
				if self.pertenece_periodo(date_periodo,rec.move_id.invoice_date)==1 and (rec.move_id.amount_igv==0):
					valor_campo_3='0'
				elif self.pertenece_periodo(date_periodo,rec.move_id.invoice_date)==1 and (rec.move_id.amount_igv>0):
					valor_campo_3='1'

				elif self.pertenece_periodo(rec.move_id.invoice_date,date_periodo) in [1,2] and (rec.move_id.amount_igv>0 or rec.move_id.amount_igv==0):
					valor_campo_3='6'

				elif self.pertenece_periodo(rec.move_id.invoice_date,date_periodo)==3 and (rec.move_id.amount_igv==0):
					valor_campo_3='7'
			
			else:
				valor_campo_3='-'
			
			rec.oportunidad_anotacion = valor_campo_3

			rec.no_domiciliado_oportunidad_anotacion='0'


	@api.depends('move_id')
	def _compute_campo_asiento_contable(self):
		for rec in self:
			if rec.move_id:
				rec.asiento_contable=rec.move_id.name or ''


	@api.depends('journal_id')
	def _compute_campo_tipo_comprobante(self):
		for rec in self:
			if rec.journal_id:
				rec.tipo_comprobante=rec.journal_id.invoice_type_code_id or ''
			else:
				rec.tipo_comprobante=''

	
	###########################################################################################################################
	@api.depends('partner_sunat_id')
	def _compute_campo_tipo_documento_proveedor(self):
		for rec in self:
			if rec.partner_sunat_id:
				rec.tipo_documento_proveedor = rec.partner_sunat_id.l10n_pe_vat_code or ''
			else:
				rec.tipo_documento_proveedor = ''


	@api.depends('partner_id')
	def _compute_campo_ruc_dni(self):
		for rec in self:
			if rec.partner_id:
				rec.ruc_dni=rec.partner_id.vat or ''


	@api.depends('partner_id')
	def _compute_campo_razon_social(self):
		for rec in self:
			if rec.partner_id:
				rec.razon_social=rec.partner_id.name


	@api.depends('currency_id')
	def _compute_campo_codigo_moneda(self):
		for rec in self:
			if rec.currency_id:
				rec.codigo_moneda=rec.currency_id.name

	@api.depends('move_id_2')
	def _compute_campo_fecha_emision_original(self):
		for rec in self:
			if rec.move_id_2:
				rec.fecha_emision_original= rec.move_id_2.invoice_date
			else:
				rec.fecha_emision_original= ''
			

	@api.depends('move_id_2')
	def _compute_campo_tipo_comprobante_original(self):
		for rec in self:
			rec.tipo_comprobante_original=''
			if rec.move_id_2 and rec.move_id_2.journal_id:
				rec.tipo_comprobante_original= rec.move_id_2.journal_id.invoice_type_code_id or ''
			else:
				rec.tipo_comprobante_original=''
			
		

	@api.depends('move_id_2')
	def _compute_campo_serie_comprobante_original(self):
		for rec in self:
			if rec.move_id_2:
				rec.serie_comprobante_original=rec.move_id_2.prefix_code
			else:
				rec.serie_comprobante_original= ''
			

	@api.depends('move_id_2')
	def _compute_campo_numero_comprobante_original(self):
		for rec in self:
			if rec.move_id_2:
				rec.numero_comprobante_original = rec.move_id_2.invoice_number
			else:			
				rec.numero_comprobante_original= ''



	@api.depends('move_id')
	def _compute_campo_fecha_detraccion(self):
		for rec in self:
			if rec.move_id.register_detraction_id:
				rec.fecha_detraccion = rec.move_id.register_detraction_id.fecha_pago or False



	@api.depends('move_id')
	def _compute_campo_numero_detraccion(self):
		for rec in self:
			if rec.move_id.register_detraction_id:
				rec.numero_detraccion = rec.move_id.register_detraction_id.nro_constancia or ''

	############################################################################

	########################################### NO DOMICILIADOS CAMPOS COMPUTE !!!
	

	@api.depends('partner_id')
	def compute_partner_country_id(self):
		for rec in self:
			if rec.partner_id:
				rec.partner_country_id=rec.partner_id.country_id



	@api.depends('partner_id')
	def _compute_campo_no_domiciliado_domicilio(self):
		for rec in self:
			if rec.partner_id:
				rec.no_domiciliado_domicilio = rec.partner_id.street or ''


	
	@api.depends('partner_country_id')
	def _compute_campo_no_domiciliado_pais_residencia(self):
		for rec in self:
			if rec.partner_country_id:
				rec.no_domiciliado_pais_residencia=rec.partner_country_id.codigo_sunat


	
	@api.depends('partner_id')
	def _compute_campo_no_domiciliado_numero_identificacion(self):
		for rec in self:
			if rec.partner_id:
				rec.no_domiciliado_numero_identificacion=rec.partner_id.vat