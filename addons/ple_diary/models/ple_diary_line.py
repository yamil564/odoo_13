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
class PleDiaryLine(models.Model):
	_name='ple.diary.line'

	ple_diary_id=fields.Many2one("ple.diary",string="id PLE", ondelete="cascade" )
	

	move_id=fields.Many2one("account.move", string="Asiento contable" , readonly=True )
	move_line_id=fields.Many2one("account.move.line" , string="Apuntes Contables" , readonly=True)

	# periodo=fields.Char(string="Periodo")
	###  SE EVITA USAR CAMPOS DEFAULT PARA PODER LLENAR CON INFORMACION LOS CAMPOS QUE NO PUDEN SER CALCULADOS POR FALTA DE INFORMACION EN LA DATA DE ASIENTOS CONTABLES !!!!
	periodo=fields.Char(string="Periodo PLE") ### ESTO CORRESPONDE AL MES DE LA CREACIÓN DEL PLE !!!
	
	periodo_apunte=fields.Char(string="Periodo del apunte contable", compute='_compute_campo_periodo_apunte' , store=True , readonly=True ) ### ESTO CORRESPONDE AL MES DE LA CREACIÓN DEL PLE !!!
	asiento_contable=fields.Char(string="Nombre del asiento contable", compute='_compute_campo_asiento_contable' , store=True , readonly=True) #############################
	m_correlativo_asiento_contable=fields.Char(string="M-correlativo asiento contable" ,compute='_compute_campo_m_correlativo_asiento_contable' ,store=True , readonly=True )# 
	codigo_cuenta_desagregado_id=fields.Many2one('account.account', string="Código cuenta contable desagregado" , compute='_compute_campo_codigo_cuenta_desagregado_id' , store=True)
	journal_id=fields.Many2one('account.journal' , string="Diario" , compute='_compute_campo_journal_id')
	codigo_cuenta_desagregado=fields.Char(string="Código cuenta contable desagregado" , compute='_compute_campo_codigo_cuenta_desagregado' , store=True )
	codigo_unidad_operacion=fields.Char(string="Código unidad operación" , default="" )
	codigo_centro_costos=fields.Char(string="Código centro de costos" , default="" )
	tipo_moneda_origen= fields.Char(string="Tipo de Moneda de origen" , compute='_compute_campo_tipo_moneda_origen' , store=True, readonly=True   )
	tipo_doc_iden_emisor = fields.Char(string="Tipo Documento Identidad Emisor", compute='_compute_campo_tipo_doc_iden_emisor', store=True , readonly=True  )
	num_doc_iden_emisor= fields.Char(string="Número Documento Identidad Emisor" ,  compute='_compute_campo_num_doc_iden_emisor', store=True , readonly=True )
	tipo_comprobante_pago= fields.Char(string="Tipo de Comprobante Pago" , compute='_compute_campo_tipo_comprobante_pago', store = True , readonly = True  )

	num_serie_comprobante_pago= fields.Char(string="Número serie Comprobante Pago", compute='_compute_campo_num_serie_comprobante_pago', store = True)#, inverse= '_inverse_compute_campo_num_serie_comprobante_pago', store = True , readonly=False )
	num_comprobante_pago= fields.Char(string="Número Comprobante de Pago",compute='_compute_campo_num_comprobante_pago',store = True)# inverse= '_inverse_compute_campo_num_comprobante_pago' ,store = True ,  readonly=False)

	fecha_contable= fields.Date(string="Fecha Contable" , compute='_compute_campo_fecha_contable', store=True  )
	fecha_vencimiento = fields.Date(string="Fecha de vencimiento" , compute='_compute_campo_fecha_vencimiento' , store=True )
	fecha_operacion = fields.Date(string="Fecha de la operación o emisión" , compute='_compute_campo_fecha_operacion' , store=True )
	glosa = fields.Char(string="Glosa o descripción naturaleza de operación" , compute='_compute_campo_glosa' ,inverse = '_inverse_compute_campo_glosa' , readonly=False)
	glosa_referencial = fields.Char(string="Glosa referencial" , default="")
	movimientos_debe = fields.Float(string="Movimientos del Debe" , compute='_compute_campo_movimientos_debe' , store=True)
	movimientos_haber = fields.Float(string="Movimientos del Haber" , compute='_compute_campo_movimientos_haber', store=True)
	dato_estructurado= fields.Char(string="Dato estructurado")# , compute='_compute_campo_dato_estructurado')
	indicador_estado_operacion= fields.Char(string="Dato estado operación" , compute='_compute_campo_indicador_estado_operacion'  )
	# conjunto=fields.Char(string="Libro al que pertenece")  ## este campo servirá para separar los asientos contables en libros

	@api.depends('move_id')
	def _compute_campo_periodo_apunte(self):
		for rec in self:
			mes=(rec.move_id.date and rec.move_id.date.month) or ''
			
			if mes<10:
				mes="0%s"%(mes)
			elif mes>=10:
				mes="%s"%(mes)

			if rec.move_id.date:
				rec.periodo_apunte = "%s%s00" % (rec.move_id.date and rec.move_id.date.year or 'YYYY', mes or 'MM')
			else:
				rec.periodo_apunte = "YYYYMM00"


	@api.depends('move_id')
	def _compute_campo_asiento_contable(self):
		for rec in self:
			rec.asiento_contable =rec.move_id.name or '-'

	@api.depends('move_line_id','move_id')
	def _compute_campo_m_correlativo_asiento_contable(self):### Esta función asigna correlativos m1 ,m2 , m3..a los elementos de un asiento , teniendo el cuenta
	##que los apuntes contables estan ordenados por codigo cuenta
		for rec in self:
			if rec.move_id.line_ids:
				indice= sorted([(line.account_id.code or '',line.id) for line in rec.move_id.line_ids]).index((rec.move_line_id.account_id.code or '',rec.move_line_id.id))
				rec.m_correlativo_asiento_contable='M' + str(indice+1)

	@api.depends('move_line_id')
	def _compute_campo_codigo_cuenta_desagregado_id(self):
		for rec in self:
			if rec.move_line_id:
				rec.codigo_cuenta_desagregado_id = rec.move_line_id.account_id or False


	@api.depends('codigo_cuenta_desagregado_id')
	def _compute_campo_codigo_cuenta_desagregado(self):
		for rec in self:
			rec.codigo_cuenta_desagregado = rec.codigo_cuenta_desagregado_id and rec.codigo_cuenta_desagregado_id.code or ''

	@api.depends('move_line_id')
	def _compute_campo_tipo_moneda_origen(self):
		for rec in self:
			rec.tipo_moneda_origen = rec.move_line_id.currency_id.name or rec.move_line_id.move_id.currency_id.name or rec.move_line_id.company_id.currency_id.name or ''


	@api.depends('move_line_id','move_id')
	def _compute_campo_tipo_doc_iden_emisor(self):
		for rec in self:
			rec.tipo_doc_iden_emisor=(rec.move_line_id.partner_id and rec.move_line_id.partner_id.l10n_latam_identification_type_id and rec.move_line_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code) or rec.move_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code or ''


	@api.depends('move_line_id','move_id')
	def _compute_campo_num_doc_iden_emisor(self):
		for rec in self:
			rec.num_doc_iden_emisor = rec.move_line_id.partner_id.vat or rec.move_id.partner_id.vat or ''
		

	############################################################################################################
	## invoice_type_code_id
	@api.depends('move_line_id')
	def _compute_campo_tipo_comprobante_pago(self):
		for rec in self:
			tabla_10=['00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19','20','21','22',
				'23','24','25','26','27','28','29','30','31','32','34','35','36','37','50','52','53','54','87','88','91','96','97','98','99']

			aux_tipo_comprobante='00'
			if rec.move_line_id.move_id.journal_id:
				aux_tipo_comprobante = (rec.move_line_id.move_id.journal_id.invoice_type_code_id) or '00'
			else:
				aux_tipo_comprobante = '00'
			
			if aux_tipo_comprobante in tabla_10:
				rec.tipo_comprobante_pago = aux_tipo_comprobante
			else:
				rec.tipo_comprobante_pago ='00'

	@api.depends('move_line_id','tipo_comprobante_pago')
	def _compute_campo_num_serie_comprobante_pago(self):
		for rec in self:
			prefix_code=''
			number=''
			if rec.tipo_comprobante_pago in ['01','02','07','08']:
				if rec.move_line_id.move_id:
					prefix_code = rec.move_line_id.move_id and rec.move_line_id.move_id.name and rec.move_line_id.move_id.name.split('-')[0] or ''
				else:
					prefix_code = rec.move_line_id.move_id.name or '-'
				

				if prefix_code:
					tam = len(prefix_code)
					ini = tam - 4
					if ini>0:
						number = prefix_code[ini:tam]
					elif ini<0:
						number = '0' * abs(ini) + prefix_code
					else:
						number = prefix_code
				else:
					number = ''
				rec.num_serie_comprobante_pago = number
			else:
				if rec.move_line_id.move_id and rec.move_line_id.move_id.name:
					partes = rec.move_line_id.move_id.name.split('-')
					rec.num_serie_comprobante_pago = partes[0] 


	@api.depends('move_line_id','tipo_comprobante_pago')
	def _compute_campo_num_comprobante_pago(self):
		for rec in self:
			invoice_number=''
			number=''
			if rec.tipo_comprobante_pago in ['01','02','07','08']:
				if rec.move_line_id.move_id:
					number_=rec.move_line_id.move_id.name.split('-')
					if len(number)>1:
						invoice_number = number_[1]
					else:
						invoice_number = rec.move_line_id.move_id.name

				if invoice_number:
					tam = len(invoice_number)
					ini = tam - 8
					if ini > 0:
						number = invoice_number[ini:tam].strip()
					elif ini < 0:
						number = '0' * abs(ini) + invoice_number.strip()
					else:
						number = invoice_number
				else:
					number = '-'
				rec.num_comprobante_pago = (number or '').strip()
			else:
				if rec.move_line_id.move_id and rec.move_line_id.move_id.name:
					partes = rec.move_line_id.move_id.name.split('-')
					if len(partes or '')>1:
						rec.num_comprobante_pago = partes[1] or '-'
					else:
						rec.num_comprobante_pago = partes[0] or '-'
				else:

					rec.num_comprobante_pago = '-'


	@api.depends('move_line_id') # ES LA FECHA QUE FIGURA EN EL APUNTE CONTABLE !!!!
	def _compute_campo_fecha_contable(self):
		for rec in self:
			rec.fecha_contable = rec.move_line_id.date

	@api.depends('move_line_id')
	def _compute_campo_fecha_vencimiento(self):
		for rec in self:
			rec.fecha_vencimiento = rec.move_line_id.date_maturity

	@api.depends('move_line_id')
	def _compute_campo_fecha_operacion(self): ## FECHA OPERACION O FECHA EMISION DE LA FACTURA !!!
		for rec in self:
			rec.fecha_operacion = rec.move_line_id.date

	@api.depends('move_line_id')
	def _compute_campo_glosa(self): #####EN ESTE CAMPO SE COLOCA LA DESCRIPCIÓN DE UN APUNTE CONTABLE , QUE EN ESTE CASO SERÁ LA ETIQUETA DEL APUNTE CONTABLE !!!
		for rec in self:
			if rec.move_line_id.payment_id:
				rec.glosa = rec.move_line_id.move_id.ref or '-'
			else:
				rec.glosa= rec.move_line_id.name or '-'


	@api.depends('move_line_id')
	def _compute_campo_movimientos_debe(self):
		for rec in self:
			rec.movimientos_debe = format(round(rec.move_line_id.debit,2) , ".2f") 


	@api.depends('move_line_id')
	def _compute_campo_movimientos_haber(self):
		for rec in self:
			rec.movimientos_haber = format(round(rec.move_line_id.credit,2), ".2f")


	@api.depends('fecha_contable','fecha_operacion','periodo')
	def _compute_campo_indicador_estado_operacion(self):
		for rec in self:
			if(rec.fecha_operacion):

				if rec.fecha_contable.strftime("%Y%m%d") >= (rec.periodo or '') :
					rec.indicador_estado_operacion='1'
				else:
					rec.indicador_estado_operacion='8'
				# elif tools.getDateYYYYMMDD(rec.fecha_contable) >=  tools.getDateYYYYMMDD(rec.fecha_operacion) :
				# 	rec.indicador_estado_operacion='8'
				# else:
				# 	rec.indicador_estado_operacion='9'
			else:
				rec.indicador_estado_operacion='1'

	###################################################################################
	def _convert_object_date(self, date):
		# parametro date que retorna un valor vacio o el foramto 01/01/2100 dia/mes/año
		if date:
			return date.strftime("%d/%m/%Y")
			#return '%s/%s/%s'%(date.split('-')[2] or '',date.split('-')[1] or '',date.split('-')[0] or '')
		else:
			return ''
	##################################################################################