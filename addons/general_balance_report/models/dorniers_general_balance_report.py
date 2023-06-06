import calendar
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import xlsxwriter
from odoo.exceptions import UserError , ValidationError
from odoo.addons import unique_library_accounting_queries as unique_queries
import logging
from itertools import *
_logger=logging.getLogger(__name__)

options=[
	('in','esta en'),
	('not in','no esta en')
	]


class DorniersGeneralBalanceReport(models.Model):
	_name='dorniers.general.balance.report'
	_description = "Modulo de Reporte de Estado de Situación Financiera-Balance General"


	state = fields.Selection(selection=[('draft','Borrador'),('generated','Generado')],
		readonly=True, states={'draft': [('readonly', False)]},
		string="Estado", default="draft")

	company_id = fields.Many2one('res.company',
		string="Compañia", 
		default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
		domain = lambda self: [('id', 'in',[i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids] )],
		readonly=True)

	dorniers_general_balance_report_line_ids = fields.One2many('dorniers.general.balance.report.line',
		'dorniers_general_balance_report_id',
		string="Rubros del Estado de Situación Financiera",
		readonly=True, states={'draft': [('readonly', False)]})

	######################################################
	name = fields.Char(string="Nombre")
	observations = fields.Char(string="Observaciones")
	######################################################


	fecha_inicio=fields.Date(string="Fecha Inicio",required=True)
	fecha_final=fields.Date(string="Fecha Final",required=True)

	#### FILTROS DINAMICOS !!
	partner_ids = fields.Many2many('res.partner',string="Socios")
	partner_option=fields.Selection(selection=options , string="")

	account_ids = fields.Many2many('account.account',string='Cuentas')
	account_option=fields.Selection(selection=options , string="")

	journal_ids = fields.Many2many('account.journal',string="Diarios")
	journal_option=fields.Selection(selection=options , string="")

	move_ids = fields.Many2many('account.move',string='Asientos Contables')
	move_option=fields.Selection(selection=options , string="")

	payment_ids = fields.Many2many('account.payment',string="Pagos")
	payment_option=fields.Selection(selection=options , string="")

	template_general_balance_report_id = fields.Many2one('template.general.balance.report', string="Plantilla Estado de Situación Financiera",
		default=lambda self:self.env['template.general.balance.report'].search([],limit=1))

	######################################################
	print_format = fields.Selection(selection='_get_print_format',string='Formato Impresión',default='xlsx')
	#######################################################
	
	def name_get(self):
		result = []
		for rec in self:
			result.append((rec.id,"%s-%s"%(self._convert_object_date(rec.fecha_inicio),self._convert_object_date(rec.fecha_final)) or 'New'))
		return result

	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		args = args or []
		recs = self.search([('fecha_inicio', operator, name),('fecha_final', operator, name)] + args, limit=limit)
		return recs.name_get()
	##########################################################
	@api.model
	def _get_print_format(self):
		option = [
			('xlsx','xlsx')
		]
		return option


	def document_print(self):
		output = BytesIO()
		output = self._init_buffer(output)
		output.seek(0)
		return output.read()


	def action_print(self):
		if (self.print_format) :

			if self.print_format in ['xlsx']:
				return {
					'type': 'ir.actions.act_url',
					'url': 'reports/format/{}/{}/{}'.format(self._name, self.print_format, self.id),
					'target': 'new'}
		else:
			raise UserError(_('NO SE PUEDE IMPRIMIR !\nEl campo Formato de Impresión es obligatorio, por favor llene dicho campo.'))

	
	##########################################################

	def button_view_tree(self):	
		if self.dorniers_general_balance_report_line_ids:
			diccionario = {
				'name': 'Estado de Situación Financiera del %s al %s'%(
					self.fecha_inicio.strftime("%d-%m-%Y"),self.fecha_final.strftime("%d-%m-%Y")),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'dorniers.general.balance.report.line',
				'view_id': False,
				'type': 'ir.actions.act_window',
				'domain': [('id', 'in', [i.id for i in self.dorniers_general_balance_report_line_ids] or [])],
				'context':{
					'search_default_filter_grupo_informe':1,
					'search_default_filter_grupo_elemento':1,
					'search_default_filter_sub_grupo_elemento':1,
					
					}
			}
			return diccionario


	
	def query_balance_of_sums_and_balances(self,str_account_ids,fecha_movimiento_debe,fecha_movimiento_haber):

		filter_clause = ""
		partners=tuple(self.partner_ids.mapped('id'))
		len_partners = len(partners or '')
		if len_partners:
			filter_clause += " and aml.partner_id %s %s" % ('in' or self.partner_option , str(partners) if len_partners!=1 else str(partners)[0:len(str(partners))-2] + ')')

		journals = tuple(self.journal_ids.mapped('id'))
		len_journals = len(journals or '')
		if len(self.journal_ids):
			filter_clause += " and aml.journal_id %s %s " % ('in' or self.journal_option , str(journals) if len_journals!=1 else str(journals)[0:len(str(journals))-2] + ')')

		moves = tuple(self.move_ids.mapped('id'))
		len_moves = len(moves or '')
		if len(moves):
			filter_clause += " and aml.move_id %s %s " % ('in' or self.move_option , str(moves) if len_moves!=1 else str(moves)[0:len(str(moves))-2] + ')')

		payments = tuple(self.payment_ids.mapped('id'))
		len_payments = len(payments or '')
		if len(payments):
			filter_clause += " and aml.payment_id %s %s " % ('in' or self.payment_option , str(payments) if len_payments!=1 else str(payments)[0:len(str(payments))-2] + ')')


		accounts = tuple(self.account_ids.mapped('id'))
		len_accounts = len(accounts or '')
		if len(accounts):
			filter_clause += " and aml.account_id %s %s " % ('in' or self.account_option , str(accounts) if len_accounts!=1 else str(accounts)[0:len(str(accounts))-2] + ')')

		query = unique_queries.query_account_amount_balances_with_period_group_account_cum(str_account_ids , fecha_movimiento_debe , fecha_movimiento_haber , filter_clause)

		self.env.cr.execute(query)
		records = self.env.cr.dictfetchall()
		return records



	def file_name(self, file_format):
		
		file_name = "Estado_Situacion_financiera_%s_%s_%s.%s" % (self.company_id.vat,
			self.fecha_inicio.strftime('%d_%m_%Y'),self.fecha_final.strftime('%d_%m_%Y'),file_format)
		
		return file_name



	
	def generar_libro(self):
		self.state = 'generated'
		self.dorniers_general_balance_report_line_ids.unlink()
		registro=[]

		#####################################################################

		rubros_activos_corrientes = self.template_general_balance_report_id.template_activos_corrientes_line_ids
		rubros_activos_no_corrientes = self.template_general_balance_report_id.template_activos_no_corrientes_line_ids
		rubros_pasivos_corrientes = self.template_general_balance_report_id.template_pasivos_corrientes_line_ids
		rubros_pasivos_no_corrientes = self.template_general_balance_report_id.template_pasivos_no_corrientes_line_ids
		rubros_patrimonio = self.template_general_balance_report_id.template_patrimonio_line_ids

		TOTAL_BALANCE = 0.00

		for rubro in rubros_activos_corrientes:

			if rubro.calculation_type=='accounts':
				suma = [{'balance':0.00}]
				
				if rubro.account_ids:
					suma= self.query_balance_of_sums_and_balances(rubro.account_ids.mapped('id'),self.fecha_inicio.strftime('%Y-%m-%d'),self.fecha_final.strftime('%Y-%m-%d'))
				
				registro.append((0,0,{
					'name': rubro.name or False,
					'account_ids':list(rubro.mapped('account_ids.id')) or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':suma[0]['balance'] or False,
					}))

				TOTAL_BALANCE += suma[0]['balance'] or 0.00

			elif rubro.calculation_type=='manual':
				registro.append((0,0,{
					'name': rubro.name or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':rubro.movements_period or False,
					}))

				TOTAL_BALANCE += rubro.movements_period or 0.00
		#############################################################
		for rubro in rubros_activos_no_corrientes:

			if rubro.calculation_type=='accounts':
				suma = [{'balance':0.00}]
				
				if rubro.account_ids:
					suma= self.query_balance_of_sums_and_balances(rubro.account_ids.mapped('id'),self.fecha_inicio.strftime('%Y-%m-%d'),self.fecha_final.strftime('%Y-%m-%d'))
				registro.append((0,0,{
					'name': rubro.name or False,
					'account_ids':list(rubro.mapped('account_ids.id')) or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':suma[0]['balance'] or False,
					}))

				TOTAL_BALANCE += suma[0]['balance'] or 0.00

			elif rubro.calculation_type=='manual':
				registro.append((0,0,{
					'name': rubro.name or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':rubro.movements_period or False,
					}))

				TOTAL_BALANCE += rubro.movements_period or 0.00
		##############################################################

		for rubro in rubros_pasivos_corrientes:

			if rubro.calculation_type=='accounts':
				suma = [{'balance':0.00}]
				
				if rubro.account_ids:
					suma= self.query_balance_of_sums_and_balances(rubro.account_ids.mapped('id'),self.fecha_inicio.strftime('%Y-%m-%d'),self.fecha_final.strftime('%Y-%m-%d'))
				registro.append((0,0,{
					'name': rubro.name or False,
					'account_ids':list(rubro.mapped('account_ids.id')) or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':-(suma[0]['balance'] or 0.00),
					}))

				TOTAL_BALANCE += suma[0]['balance'] or 0.00

			elif rubro.calculation_type=='manual':
				registro.append((0,0,{
					'name': rubro.name or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':rubro.movements_period or False,
					}))

				TOTAL_BALANCE -= rubro.movements_period or 0.00

		#############################################################
		for rubro in rubros_pasivos_no_corrientes:

			if rubro.calculation_type=='accounts':
				suma = [{'balance':0.00}]
				
				if rubro.account_ids:
					suma= self.query_balance_of_sums_and_balances(rubro.account_ids.mapped('id'),self.fecha_inicio.strftime('%Y-%m-%d'),self.fecha_final.strftime('%Y-%m-%d'))
				registro.append((0,0,{
					'name': rubro.name or False,
					'account_ids':list(rubro.mapped('account_ids.id')) or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':-(suma[0]['balance'] or 0.00),
					}))

				TOTAL_BALANCE += suma[0]['balance'] or 0.00

			elif rubro.calculation_type=='manual':
				registro.append((0,0,{
					'name': rubro.name or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':rubro.movements_period or False,
					}))

				TOTAL_BALANCE -= rubro.movements_period or 0.00

		##############################################################
		
		for rubro in rubros_patrimonio:

			if rubro.calculation_type=='accounts':
				suma = [{'balance':0.00}]
				
				if rubro.account_ids:
					suma= self.query_balance_of_sums_and_balances(rubro.account_ids.mapped('id'),self.fecha_inicio.strftime('%Y-%m-%d'),self.fecha_final.strftime('%Y-%m-%d'))
				registro.append((0,0,{
					'name': rubro.name or False,
					'account_ids':list(rubro.mapped('account_ids.id')) or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':-(suma[0]['balance'] or 0.00),
					}))
				TOTAL_BALANCE += suma[0]['balance'] or 0.00

			elif rubro.calculation_type=='manual':
				registro.append((0,0,{
					'name': rubro.name or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'saldo_rubro_contable':rubro.movements_period or False,
					}))

				TOTAL_BALANCE -= rubro.movements_period or 0.00

			elif rubro.calculation_type=='variation':
				registro.append((0,0,{
					'name': rubro.name or False,
					'grupo_informe': rubro.grupo_informe or False,
					'grupo_elemento': rubro.grupo_elemento or False,
					'sub_grupo_elemento': rubro.sub_grupo_elemento  or False,
					'is_variation': True,
					'saldo_rubro_contable':0.00,
					}))

		self.dorniers_general_balance_report_line_ids = registro

		##### Cuadrando el EEFF , ubicando al rubro tipo variation para asignarle la diferencia.
		line_rubro_variation_id = self.dorniers_general_balance_report_line_ids.filtered(lambda t:t.is_variation)
		if line_rubro_variation_id:
			line_rubro_variation_id = line_rubro_variation_id[0]

		line_rubro_variation_id.write({'saldo_rubro_contable':TOTAL_BALANCE})



	
	def _init_buffer(self, output):
		# output parametro de buffer que ingresa vacio
		if self.print_format == 'xlsx':
			self._generate_xlsx(output)

		return output

	def _convert_object_date(self, date):
		# parametro date que retorna un valor vacio o el foramto 01/01/2100 dia/mes/año
		if date:
			return date.strftime('%d/%m/%Y')
		else:
			return ''


	
	def _generate_xlsx(self, output):
		workbook = xlsxwriter.Workbook(output)
		ws = workbook.add_worksheet('Estado Situación Financiera - Balance General')
		titulo1 = workbook.add_format({'font_size': 12,'valign': 'vcenter', 'align': 'center', 'text_wrap': True, 'bold': True, 'font_name':'Arial'})
		titulo_1 = workbook.add_format({'font_size': 8, 'align': 'left', 'text_wrap': True, 'bold': True, 'font_name':'Arial'})
		titulo2 = workbook.add_format({'font_size': 8, 'align': 'center','valign': 'vcenter','color':'black', 'text_wrap': True, 'left':True, 'right':True,'bottom': True, 'top': True, 'bold':True , 'font_name':'Arial'})
		titulo2_left = workbook.add_format({'font_size': 8, 'align': 'left','valign': 'vcenter','color':'black', 'text_wrap': True, 'left':True, 'right':True,'bottom': True, 'top': True, 'bold':True , 'font_name':'Arial'})
		titulo2_right = workbook.add_format({'font_size': 8, 'align': 'right','valign': 'vcenter','color':'black', 'text_wrap': True, 'left':True, 'right':True,'bottom': True, 'top': True, 'bold':True , 'font_name':'Arial'})
		titulo2_center = workbook.add_format({'font_size': 8, 'align': 'center','valign': 'vcenter','color':'black', 'text_wrap': True, 'left':True, 'right':True,'bottom': True, 'top': True, 'bold':True , 'font_name':'Arial'})
		#######################################################
		titulo_2 = workbook.add_format({'font_size': 8, 'align': 'center', 'text_wrap': True, 'bold': True, 'font_name':'Arial'})
		##################################################################
		number_left = workbook.add_format({'font_size': 8, 'align': 'left', 'num_format': '#,##0.00', 'font_name':'Arial'})
		number_right = workbook.add_format({'font_size': 8, 'align': 'right', 'num_format': '#,##0.00', 'font_name':'Arial'})
		number_right_tax_rate = workbook.add_format({'font_size': 8, 'align': 'right', 'num_format': '#,##0.000', 'font_name':'Arial'})
		
		letter1 = workbook.add_format({'font_size': 7, 'align': 'left', 'font_name':'Arial'})
		letter3_negrita = workbook.add_format({'font_size': 7, 'align': 'right','num_format': '#,##0.00', 'font_name':'Arial','bold': True})

		ws.set_column('A:A', 13,letter1)
		ws.set_column('B:B', 13,letter1)
		ws.set_column('C:C', 13,letter1)
		ws.set_column('D:D', 9,letter3_negrita)
		ws.set_column('E:E', 9,letter3_negrita)
		ws.set_column('F:F', 13,letter3_negrita)
		ws.set_column('G:G', 13,letter1)
		ws.set_column('H:H', 13,letter1)
		ws.set_column('I:I', 9,letter1)
		ws.set_column('J:J', 9,letter3_negrita)

		ws.merge_range('A1:I2','ESTADO DE SITUACIÓN FINANCIERA-BALANCE GENERAL ' \
			+ 'DEL ' + self.fecha_inicio.strftime('%d-%m-%Y') + '  AL ' + self.fecha_final.strftime('%d-%m-%Y'),titulo1)
	
		ws.merge_range('A4:D4','EJERCICIO:', titulo_1)
		ws.merge_range('E4:F4',self.fecha_final.strftime('%Y') or '', titulo_1)
		
		ws.merge_range('A5:D5','RUC:', titulo_1)
		ws.write('E5:F5',self.company_id.vat or '', titulo_1)

		ws.merge_range('A6:D6','APELLIDOS Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL:', titulo_1)
		ws.merge_range('E6:F6',self.company_id.name or '', titulo_1)

		#######################################################################
		rubros_activos_corrientes = self.dorniers_general_balance_report_line_ids.\
			filtered(lambda r:r.grupo_informe=='activo' and r.grupo_elemento=='activo' and r.sub_grupo_elemento=='activo_corriente')

		rubros_activos_no_corrientes = self.dorniers_general_balance_report_line_ids.\
			filtered(lambda r:r.grupo_informe=='activo' and r.grupo_elemento=='activo' and r.sub_grupo_elemento=='activo_no_corriente')	
		
		rubros_pasivos_corrientes = self.dorniers_general_balance_report_line_ids.\
			filtered(lambda r:r.grupo_informe=='pasivo_patrimonio' and r.grupo_elemento=='pasivo' and r.sub_grupo_elemento=='pasivo_corriente')

		rubros_pasivos_no_corrientes = self.dorniers_general_balance_report_line_ids.\
			filtered(lambda r:r.grupo_informe=='pasivo_patrimonio' and r.grupo_elemento=='pasivo' and r.sub_grupo_elemento=='pasivo_no_corriente')

		
		rubros_patrimonio = self.dorniers_general_balance_report_line_ids.\
			filtered(lambda r:r.grupo_informe=='pasivo_patrimonio' and r.grupo_elemento=='patrimonio' and r.sub_grupo_elemento=='patrimonio')

		
		TOTAL = 0.00
		TOTAL_ACTIVO_CORRIENTE = 0.00
		TOTAL_ACTIVO_NO_CORRIENTE = 0.00

		TOTAL_PASIVO_CORRIENTE = 0.00
		TOTAL_PASIVO_NO_CORRIENTE = 0.00

		TOTAL_PATRIMONIO = 0.00

		TOTAL_PASIVO_PATRIMONIO = 0.00
		
		#######################################################################

		fila = 9
		k=0

		ws.merge_range("A8:E8","ACTIVO",titulo2_center)

		ws.merge_range("A9:C9",'ACTIVO CORRIENTE',titulo2_left)
		ws.merge_range("D9:E9",'',titulo2_left)

		fila +=1

		for line in rubros_activos_corrientes:

			ws.merge_range("A%s:C%s"%(fila,fila),line.name or '',titulo2_left)
			ws.merge_range("D%s:E%s"%(fila,fila),line.saldo_rubro_contable or 0.00,titulo2_left)

			fila +=1
		
			TOTAL_ACTIVO_CORRIENTE += line.saldo_rubro_contable or 0.00

		ws.merge_range("A%s:C%s"%(fila,fila),'TOTAL ACTIVO CORRIENTE',titulo2_left)
		ws.merge_range("D%s:E%s"%(fila,fila),TOTAL_ACTIVO_CORRIENTE,titulo2_left)


		####################################################################
		fila +=1

		ws.merge_range("A%s:C%s"%(fila,fila),'ACTIVO NO CORRIENTE',titulo2_left)
		ws.merge_range("D%s:E%s"%(fila,fila),'',titulo2_left)

		fila +=1

		for line in rubros_activos_no_corrientes:

			ws.merge_range("A%s:C%s"%(fila,fila),line.name or '',titulo2_left)
			ws.merge_range("D%s:E%s"%(fila,fila),line.saldo_rubro_contable or 0.00,titulo2_left)

			fila +=1
		
			TOTAL_ACTIVO_NO_CORRIENTE += line.saldo_rubro_contable or 0.00

		ws.merge_range("A%s:C%s"%(fila,fila),'TOTAL ACTIVO NO CORRIENTE',titulo2_left)
		ws.merge_range("D%s:E%s"%(fila,fila),TOTAL_ACTIVO_NO_CORRIENTE,titulo2_left)

		TOTAL_ACTIVO = TOTAL_ACTIVO_CORRIENTE + TOTAL_ACTIVO_NO_CORRIENTE

		#################################################################
		#################################################################
		ws.merge_range("F8:J8","PASIVO",titulo2_center)

		ws.merge_range("F9:H9",'PASIVO CORRIENTE',titulo2_left)
		ws.merge_range("I9:J9",'',titulo2_left)

		fila_2 = 10

		for line in rubros_pasivos_corrientes:

			ws.merge_range("F%s:H%s"%(fila_2,fila_2),line.name or '',titulo2_left)
			ws.merge_range("I%s:J%s"%(fila_2,fila_2),line.saldo_rubro_contable or 0.00,titulo2_left)

			fila_2 +=1
		
			TOTAL_PASIVO_CORRIENTE += line.saldo_rubro_contable or 0.00

		ws.merge_range("F%s:H%s"%(fila_2,fila_2),'TOTAL PASIVO CORRIENTE',titulo2_left)
		ws.merge_range("I%s:J%s"%(fila_2,fila_2),TOTAL_PASIVO_CORRIENTE,titulo2_left)


		####################################################################
		fila_2 +=1

		ws.merge_range("F%s:H%s"%(fila_2,fila_2),'PASIVO NO CORRIENTE',titulo2_left)
		ws.merge_range("I%s:J%s"%(fila_2,fila_2),'',titulo2_left)

		fila_2 +=1

		for line in rubros_pasivos_no_corrientes:

			ws.merge_range("F%s:H%s"%(fila_2,fila_2),line.name or '',titulo2_left)
			ws.merge_range("I%s:J%s"%(fila_2,fila_2),line.saldo_rubro_contable or 0.00,titulo2_left)

			fila_2 +=1
		
			TOTAL_PASIVO_NO_CORRIENTE += line.saldo_rubro_contable or 0.00

		ws.merge_range("F%s:H%s"%(fila_2,fila_2),'TOTAL PASIVO NO CORRIENTE',titulo2_left)
		ws.merge_range("I%s:J%s"%(fila_2,fila_2),TOTAL_PASIVO_NO_CORRIENTE,titulo2_left)

		TOTAL_PASIVO = TOTAL_PASIVO_CORRIENTE + TOTAL_PASIVO_NO_CORRIENTE

		fila_2 +=1

		ws.merge_range("F%s:H%s"%(fila_2,fila_2),'TOTAL PASIVO',titulo2_left)
		ws.merge_range("I%s:J%s"%(fila_2,fila_2),TOTAL_PASIVO,titulo2_left)

		######################################################################

		fila_2 +=1

		ws.merge_range("F%s:J%s"%(fila_2,fila_2),"PATRIMONIO",titulo2_center)

		fila_2 +=1

		for line in rubros_patrimonio:

			ws.merge_range("F%s:H%s"%(fila_2,fila_2),line.name or '',titulo2_left)
			ws.merge_range("I%s:J%s"%(fila_2,fila_2),line.saldo_rubro_contable or 0.00,titulo2_left)

			fila_2 +=1
		
			TOTAL_PATRIMONIO += line.saldo_rubro_contable or 0.00

		ws.merge_range("F%s:H%s"%(fila_2,fila_2),'TOTAL PATRIMONIO',titulo2_left)
		ws.merge_range("I%s:J%s"%(fila_2,fila_2),TOTAL_PATRIMONIO,titulo2_left)

		TOTAL_PASIVO_PATRIMONIO = TOTAL_PASIVO + TOTAL_PATRIMONIO

		##############
		max_indice = max(fila,fila_2) +1

		#### write totales 
		ws.merge_range("A%s:C%s"%(max_indice,max_indice),'TOTAL ACTIVO',titulo2_left)
		ws.merge_range("D%s:E%s"%(max_indice,max_indice),TOTAL_ACTIVO,titulo2_left)

		ws.merge_range("F%s:H%s"%(max_indice,max_indice),'TOTAL PASIVO Y PATRIMONIO',titulo2_left)
		ws.merge_range("I%s:J%s"%(max_indice,max_indice),TOTAL_PASIVO_PATRIMONIO,titulo2_left)


		workbook.close()



	def is_menor(self,a,b):
		return a<b