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

class PleDiary(models.Model):
	_name='ple.diary'
	_inherit='ple.base'
	_description = "Modulo PLE Libros diary"

	ple_diary_line_ids=fields.One2many('ple.diary.line','ple_diary_id',string="Libro diary",readonly=True, states={'draft': [('readonly', False)]})


	### FILTROS DINÁMICOS
	######################### FILTROS DINAMICOS, NUEVOS CAMPOS AGREGADOS !!!
	partner_ids = fields.Many2many('res.partner','ple_diary_partner_rel','partner_id','ple_diary_id' ,string="Socios")
	options_partner=fields.Selection(selection=options,string="")

	account_ids = fields.Many2many('account.account','ple_diary_account_rel','account_id','ple_diary_id',string='Cuentas')
	options_account=fields.Selection(selection=options,string="")
	
	journal_ids = fields.Many2many('account.journal','ple_diary_journal_rel','journal_id','ple_diary_id',string="Diarios")
	
	options_journal=fields.Selection(selection=options,string="")

	move_ids = fields.Many2many('account.move','ple_diary_move_rel','move_id','ple_diary_id',string='Asientos Contables')
	
	options_move=fields.Selection(selection=options,string="")

	payment_ids = fields.Many2many('account.payment','ple_diary_payment_rel','payment_id','ple_diary_id',string="Pagos")
	
	options_payment=fields.Selection(selection=options,string="")
	
	########################################################

	## BLOQUES DE IMPRESIÓN
	block_counter=fields.Integer(string="Bloque de Impresión N°" , default=0 , readonly=True)
	block_size=fields.Integer(string="Número de Registros por bloque", default=3000)
	##########################
	##buffer para asientos a apuntes

	fecha_impresion=fields.Date(string="Fecha de Impresión manual" , default=datetime(datetime.now().year,datetime.now().month,datetime.now().day).date())
	#################################################
	fecha=fields.Boolean(string="Fecha" ,readonly=True , states={'draft': [('readonly', False)]})
	periodo=fields.Boolean(string="Periodo" ,readonly=True , states={'draft': [('readonly', False)]})

	date_from=fields.Date(string="Desde:" ,readonly=True , states={'draft': [('readonly', False)]})
	date_to=fields.Date(string="Hasta:" ,readonly=True , states={'draft': [('readonly', False)]})

	############## CHECK para indicar si se incluye o no registros anteriores no declarados
	incluir_anteriores_no_declarados = fields.Boolean(string="Incluir registros anteriores no declarados", default=False)

	fin_asiento=fields.Boolean(default=False)
	fin_documento=fields.Boolean(default=False)

	infimo=fields.Integer(default=0, string="Infimo")
	supremo=fields.Integer(default=0,string="Supremo")

	fecha_inicio=''
	fecha_fin=''
	###############################
	_sql_constraints = [
		('fiscal_month', 'unique(fiscal_month,fiscal_year,company_id)',  'Este periodo para el PLE ya existe , revise sus registros de PLE creados!!!'),
	]
	################################################################

	def open_wizard_print_form(self):
		res = super(PleDiary,self).open_wizard_print_form()

		view = self.env.ref('ple_diary.view_wizard_printer_ple_diary_form')
		if view:

			return {
				'name': _('FORMULARIO DE IMPRESIÓN DEL LIBRO PLE'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'wizard.printer.ple.diary',
				'views': [(view.id,'form')],
				'view_id': view.id,
				'target': 'new',
				'context': {
					'default_ple_diary_id': self.id,
					'default_company_id' : self.company_id.id,}}

	#################################################################
	def button_view_tree(self):	
		if self.ple_diary_line_ids:
			diccionario = {
				'name': 'Libro PLE Diario-Mayor-Simplificado',
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'ple.diary.line',
				'view_id': False,
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', [i.id for i in self.ple_diary_line_ids] or [])],
				'context':{
					'search_default_filter_cuenta':1}
			}
			return diccionario
	##############################################################
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
	def unlink (self):
		for line in self:
			for line2 in line.ple_diary_line_ids:
				line2.move_line_id.write({'declared_ple_5_1_5_2_6_1':False})
			return super(PleDiary, line).unlink()

	##############################################################################
	def saldo_account_move_in_account_account(self,move_id , code_account):
		return sum(move_id.line_ids.filtered(lambda r:r.account_id.code==code_account).mapped('balance'))

	def account_move_account_account_totales(self):
		## creando matriz de cuentas vs asientos contables !!

		# ACTIVOS
		# PASIVOS
		# GASTOS
		# INGRESOS
		# CUENTAS DE FUNCION DEL GASTO
		asientos_totales = self.ple_diary_line_ids.mapped('move_id')

		codigo_cuentas_activos = sorted(list(self.ple_diary_line_ids.mapped('move_line_id.account_id').filtered(lambda t:t.code[0] in ['1','2','3']).mapped('code')))
		codigo_cuentas_pasivos = sorted(list(self.ple_diary_line_ids.mapped('move_line_id.account_id').filtered(lambda t:t.code[0] in ['4']).mapped('code')))
		codigo_cuentas_gastos = sorted(list(self.ple_diary_line_ids.mapped('move_line_id.account_id').filtered(lambda t:t.code[0] in ['6']).mapped('code')))
		codigo_cuentas_ingresos = sorted(list(self.ple_diary_line_ids.mapped('move_line_id.account_id').filtered(lambda t:t.code[0] in ['7']).mapped('code')))
		codigo_cuentas_funcion_gasto = sorted(list(self.ple_diary_line_ids.mapped('move_line_id.account_id').filtered(lambda t:t.code[0] in ['9']).mapped('code')))
		return [asientos_totales,codigo_cuentas_activos,codigo_cuentas_pasivos,codigo_cuentas_gastos,codigo_cuentas_ingresos,codigo_cuentas_funcion_gasto]

	##############################################################################
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
	###############################################################################

	def reinicializar_parametros_bloque(self):
		self.block_counter=0
		self.fin_asiento=False
		self.fin_documento=False
		self.infimo=0
		self.supremo=0

	def generate_tree_records(self):
		if self.identificador_libro=='050100':
			array_total=[]
			for item in self.ple_diary_line_ids:
				array_total += [(item.move_id.id,item)]

			diccionario_asientos={}
			grupos_de_asientos=groupby(sorted(array_total),lambda x:x[0])

			for k , v in grupos_de_asientos:
				self.diccionario_asientos[k]=[i[1] for i in list(v)]

	def get_asientos_actuales(self):
		return list(set([i.move_id for i in self.ple_diary_line_ids[self.infimo:self.supremo]]))



	def _get_current_accounts(self):
		lines = sorted(self.ple_diary_line_ids , key=lambda PleDiaryLine: (PleDiaryLine.codigo_cuenta_desagregado, PleDiaryLine.asiento_contable, PleDiaryLine.fecha_contable))
		blocks = lines[self.infimo:self.supremo]
		end = self.supremo + 1 <= len(lines) and self.supremo + 1 or (len(lines) - 1)
		if blocks[-1].codigo_cuenta_desagregado_id.id == lines[end].codigo_cuenta_desagregado_id.id:
			if blocks[-1].id != lines[end].id:
				self.supremo = list(map(lambda line: line.codigo_cuenta_desagregado_id.id, lines)).index(blocks[-1].codigo_cuenta_desagregado_id.id)
			else:
				self.supremo =  end + 1



	def criterios_impresion(self):
		res = super(PleDiary, self).criterios_impresion() or []
		res += [('codigo_cuenta_desagregado','Código Cuenta Desagregado')]
		return res


	def _action_confirm_ple(self):  
		for line in self.ple_diary_line_ids:
			if(line.move_line_id.declared_ple_5_1_5_2_6_1 != True):
				super(PleDiary , self)._action_confirm_ple('account.move.line' , line.move_line_id.id ,{'declared_ple_5_1_5_2_6_1':True})
	
	def _get_datas(self, domain):
		orden="move_id asc"
		if self.print_order == 'date':
			orden += ',date asc , account_id asc '		
		elif self.print_order == 'codigo_cuenta_desagregado':
			orden +=  ',account_id asc , date asc '		
		elif self.print_order == 'nro_documento':
			orden += ',account_id asc ,date asc '
		return self._get_query_datas('account.move.line', domain, orden)


	def _get_order_print(self , object):

		if self.print_order == 'date': # ORDENAMIENTO POR LA FECHA CONTABLE
			total=sorted(object, key=lambda PleDiaryLine: (  PleDiaryLine.asiento_contable , PleDiaryLine.codigo_cuenta_desagregado , PleDiaryLine.fecha_contable) )
		elif self.print_order == 'nro_documento':
			total=sorted(object , key=lambda PleDiaryLine: (PleDiaryLine.asiento_contable) ) # ,PlediaryLine.asiento_contable)) #ORDENAMIENTO POR EL NUMERO DEASIENTO CONTABLE
		elif self.print_order == 'codigo_cuenta_desagregado':
			total=sorted(object , key=lambda PleDiaryLine: (PleDiaryLine.asiento_contable , PleDiaryLine.fecha_contable ,  PleDiaryLine.codigo_cuenta_desagregado ) ) # ORDENAMIENTO POR EL CODIGO DE CUENTA DESAGREGADO
		return total


	def _get_domain(self):

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

		domain = [
			('move_id.state','=','posted'),
			('declared_ple_5_1_5_2_6_1','!=',True),
			('date','>=',self.fecha_inicio),
			('date','<=',self.fecha_fin),
			('display_type','not in',['line_section']),
			]


		##############
		partners=tuple(self.partner_ids.mapped('id'))
		len_partners = len(partners or '')
		if len_partners:
			domain.append(('partner_id.id' ,self.options_partner or 'in' , partners))

		journals = tuple(self.journal_ids.mapped('id'))
		len_journals = len(journals or '')
		if len(self.journal_ids):
			domain.append(('journal_id.id' ,self.options_journal or 'in', journals))

		moves = tuple(self.move_ids.mapped('id'))
		len_moves = len(moves or '')
		if len(moves):
			domain.append(('move_id.id' ,self.options_move or 'in', moves))


		payments = tuple(self.payment_ids.mapped('id'))
		len_payments = len(payments or '')
		if len(payments):
			domain.append(('payment_id.id' ,self.options_payment or 'in', payments))


		accounts = tuple(self.account_ids.mapped('id'))
		len_accounts = len(accounts or '')
		if len(accounts):
			domain.append(('account_id.id' ,self.options_account or 'in', accounts))
		#########
			
		return domain



	def _periodo_fiscal(self):
		periodo = "%s%s00" % (self.fiscal_year or 'YYYY', self.fiscal_month or 'MM')
		return periodo



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

		self.state='open'
		self.ple_diary_line_ids.unlink()
		registro=[]
		registro_efectivo=[]
		registro_banco=[]
		k=0
		for line in self._get_datas(self._get_domain()):
			registro.append((0,0,{'move_id':line.move_id.id , 'move_line_id':line.id , 'periodo':self._periodo_fiscal()}))
		self.ple_diary_line_ids = registro
		# self.generate_tree_records()


	def _convert_object_date(self, date):
		# parametro date que retorna un valor vacio o el foramto 01/01/2100 dia/mes/año
		if date:
			return date.strftime("%d/%m/%Y")
		else:
			return ''
