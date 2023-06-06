# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
from itertools import *
import calendar
from datetime import datetime, timedelta
import logging
from io import BytesIO, StringIO
import xlsxwriter
from odoo.addons import unique_library_accounting_queries as unique_queries

_logger = logging.getLogger(__name__)

options=[
	('in','esta en'),
	('not in','no esta en')
	]

balance_cat=[
	('none', 'Ninguno'),
	('balance', 'Balance'),
	('function', 'Funcion'),
	('nature', 'Naturaleza'),
	('function_nature', 'Naturaleza y Funcion'),
	('all','Todos')
	]

class ReportAmountBalancesOptimizedNative(models.Model):
	_name = 'report.amount.balances.optimized.native'
	_description = "Balance de Comprobación Nativo"
	_rec_name = "name"

	state = fields.Selection(selection=[('draft','Borrador'),('generated','Generado')],
		readonly=True, states={'draft': [('readonly', False)]},
		string="Estado", default="draft")

	company_id = fields.Many2one('res.company',
		string="Compañia", 
		default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
		domain = lambda self: [('id', 'in',[i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids] )] , readonly=True)
	
	name = fields.Char(string="Nombre")
	observations=fields.Char(string="Observaciones a Anotar")

	fecha_inicio=fields.Date(string="Fecha Inicio",required=True)
	fecha_final=fields.Date(string="Fecha Final",required=True)

	report_amount_balances_optimized_line_ids = fields.One2many('report.amount.balances.optimized.native.line' , 'report_amount_balances_optimized_id' , string="Balance de Comprobación", readonly=True)

	partner_ids = fields.Many2many('res.partner','report_amount_balances_native_partner_rel','partner_id','report_amount_balances_native_id_1' ,string="Socios")
	partner_option=fields.Selection(selection=options , string="")

	account_ids = fields.Many2many('account.account','report_amount_balances_native_account_rel','account_id','report_amount_balances_native_id_2',string='Cuentas')
	account_option=fields.Selection(selection=options , string="")

	journal_ids = fields.Many2many('account.journal','report_amount_balances_native_journal_rel','journal_id','report_amount_balances_native_id_3',string="Diarios")
	journal_option=fields.Selection(selection=options , string="")

	move_ids = fields.Many2many('account.move','report_amount_balances_native_move_rel','move_id','report_amount_balances_native_id_4',string='Asientos Contables')
	move_option=fields.Selection(selection=options , string="")


	payment_ids = fields.Many2many('account.payment','report_amount_balances_native_payment_rel','payment_id','report_amount_balances_native_id_6',string="Pagos")
	payment_option=fields.Selection(selection=options , string="")


	##### FILTRO DE CATEGORIA DE BALANCE
	balance_category=fields.Selection(selection=balance_cat, string="Categoría de Balance" , default='all')

	################## IMPRESIÓN DE REPORTE !!
	print_format = fields.Selection(selection='_get_print_format' , string='Formato Impresión')#,

	order_print=fields.Selection(selection=[
		('1','Grupos de Cuentas'),
		('2','Despliegue Total')],
		string="Impresión agrupada por" , required=True , default='2')

	column_balance_category=fields.Many2many('balance.category.column.native', 'report_amount_balances_native_column_rel','category_column_id','report_amount_balances_native_id_7',
		string="Elegir Columnas a Imprimir")

	##########################################
	currency_id = fields.Many2one('res.currency',string="Moneda",default=lambda self: self.env['res.company']._company_default_get('account.invoice').currency_id , required=True)
	##########################################


	@api.model
	def _get_print_format(self):
		option = [
			('txt','txt'),
			('xlsx','xlsx')
		]
		return option


	####################################################################################

	def file_name(self, file_format):
		nro_de_registros = len(self.report_amount_balances_optimized_line_ids or '')
		anio = self.fecha_inicio.strftime("%Y")
		anio_final = self.fecha_final.strftime("%Y")

		file_name = "0710%s%s.%s" % (self.company_id.vat or '',anio if anio == anio_final else (str(anio) + "_" + str(anio_final)),file_format)
		return file_name


	def _init_buffer(self, output):
		# output parametro de buffer que ingresa vacio
		for rec in self:
			if rec.print_format == 'xlsx':
				rec._generate_xlsx(output)
			elif rec.print_format == 'txt':
				rec._generate_txt(output)
			return output


	def document_print(self):
		output = BytesIO()
		output = self._init_buffer(output)
		output.seek(0)
		return output.read()


	def action_print(self):
		if (self.print_format) :
			if self.print_format =='pdf':
				return self.print_report()
			elif self.print_format in ['xlsx','txt']:
				return {
					'type': 'ir.actions.act_url',
					'url': 'reports/format/{}/{}/{}'.format(self._name, self.print_format, self.id),
					'target': 'new'}
		else:
			raise UserError(_('NO SE PUEDE IMPRIMIR !\nEl campo Formato de Impresión es obligatorio, por favor llene dicho campo.'))




	def _generar_diccionario_de_agrupacion(self,line):
		indices_agrupamiento=[]
		diccionario={}
		if self.order_print=='1':
			indices_agrupamiento_grupo_cuentas=sorted(list(set([i.account_id.group_id.code_prefix or '' for i in line])))
			for i in indices_agrupamiento_grupo_cuentas:
				diccionario[i]=[]
	
			for j in line:
				diccionario[j.account_id.group_id.code_prefix or ''].append(j)

		return diccionario
	########################################################################


	def _convert_object_date(self, date):
		if date:
			return date.strftime('%d/%m/%Y')
		else:
			return ''

	
	def _convert_to_float(self,cad):
		return float(''.join([i for i in (cad or '0.00')if i!=',']))

	################################################################################################################
	def _get_data_from_category_column(self,category_balance_column,u):
		if category_balance_column=='initial_balance':
			if self.order_print=='1':
				return "%s|%s|"%(format(sum(self._convert_to_float(line.saldos_iniciales_deudor or '0.00') for line in u),".2f"),
					format(sum(self._convert_to_float(line.saldos_iniciales_acreedor or '0.00') for line in u),".2f"))
			elif self.order_print=='2':
				return "%s|%s|"%(u.saldos_iniciales_deudor,u.saldos_iniciales_acreedor)
		
		elif category_balance_column=='period_movements':
			if self.order_print=='1':
				return "%s|%s|"%(format(sum(self._convert_to_float(line.anio_fiscal_debe or '0.00') for line in u),".2f"),
					format(sum(self._convert_to_float(line.anio_fiscal_haber or '0.00') for line in u),".2f"))
			elif self.order_print=='2':
				return "%s|%s|"%(u.anio_fiscal_debe,u.anio_fiscal_haber)

		elif category_balance_column=='final_balance':
			if self.order_print=='1':
				return "%s|%s|"%(format(sum(self._convert_to_float(line.saldos_finales_deudor or '0.00') for line in u),".2f"),
					format(sum(self._convert_to_float(line.saldos_finales_acreedor or '0.00') for line in u),".2f"))
			elif self.order_print=='2':
				return "%s|%s|"%(u.saldos_finales_deudor,u.saldos_finales_acreedor)

		elif category_balance_column=='balance':
			if self.order_print=='1':
				return "%s|%s|"%(format(sum(self._convert_to_float(line.balance_general_activo or '0.00') for line in u),".2f"),
					format(sum(self._convert_to_float(line.balance_general_pas_y_patr or '0.00') for line in u),".2f"))
			elif self.order_print=='2':
				return "%s|%s|"%(u.balance_general_activo,u.balance_general_pas_y_patr)

		elif category_balance_column=='nature':
			if self.order_print=='1':
				return "%s|%s|"%(format(sum(self._convert_to_float(line.resultados_naturaleza_perdidas or '0.00') for line in u),".2f"),
					format(sum(self._convert_to_float(line.resultados_naturaleza_ganancias or '0.00') for line in u),".2f"))
			elif self.order_print=='2':
				return "%s|%s|"%(u.resultados_naturaleza_perdidas,u.resultados_naturaleza_ganancias)

		elif category_balance_column=='function':
			if self.order_print=='1':
				return "%s|%s|"%(format(sum(self._convert_to_float(line.resultados_funcion_perdidas or '0.00') for line in u),".2f"),
					format(sum(self._convert_to_float(line.resultados_funcion_ganancias or '0.00') for line in u),".2f"))
			elif self.order_print=='2':
				return "%s|%s|"%(u.resultados_funcion_perdidas,u.resultados_funcion_ganancias)
		else:
			return None




	def _generate_txt(self, output):
		if len(self.column_balance_category):
			if self.order_print=='1':
				records=self._generar_diccionario_de_agrupacion(self.report_amount_balances_optimized_line_ids[:len(self.report_amount_balances_optimized_line_ids)-6])
				for u in records:
					escritura = "%s|"%(u if self.order_print=='1' else (u.account_id.code or '') if self.order_print=='2' else '')
					for i in self.column_balance_category:
						escritura += self._get_data_from_category_column(i.code or '',records[u])
					escritura += "\n"
					output.write(escritura.encode())

			elif self.order_print=='2':
				records = self.report_amount_balances_optimized_line_ids[:len(self.report_amount_balances_optimized_line_ids)-6]
				for u in records:
					escritura = "%s|"%(u if self.order_print=='1' else (u.account_id.code or '') if self.order_print=='2' else '')
					for i in self.column_balance_category:
						escritura += self._get_data_from_category_column(i.code or '',u)
					escritura += "\n"
					output.write(escritura.encode())
	
	################################## GENERAR EXCEL
	def _generate_xlsx(self, output):
		workbook = xlsxwriter.Workbook(output)
		ws = workbook.add_worksheet('F3.17 Anx1 Bce Comp')
		styles = {'font_size': 10, 'font_name':'Arial', 'bold': True}
		styles_table = dict(styles,font_size=8,align='center',border=1)
		titulo_1 = workbook.add_format(styles)
		titulo_2 = workbook.add_format(dict(styles,font_size=8))
		titulo_3 = workbook.add_format(styles_table)
		titulo_4 = workbook.add_format(dict(styles_table,align=''))
		titulo_5 = workbook.add_format(dict(styles_table,align='',bold=False))
		ws.set_column('A:A',17,titulo_2)
		ws.set_column('B:B',45,titulo_2)
		ws.set_column('C:C',15,titulo_2)
		ws.set_column('D:D',15,titulo_2)
		ws.set_column('E:E',15,titulo_2)
		ws.set_column('F:F',15,titulo_2)
		ws.set_column('G:G',15,titulo_2)
		ws.set_column('H:H',15,titulo_2)
		ws.set_column('I:I',15,titulo_2)
		ws.set_column('J:J',18,titulo_2)
		ws.set_column('K:K',15,titulo_2)
		ws.set_column('L:L',15,titulo_2)
		ws.write(0,0,'REPORTE DE BALANCE DE COMPROBACIÓN"',titulo_1)
		ws.write(2,0,'EJERCICIO O PERIÓDO:',titulo_2)
		ws.write(2,1,'',titulo_2)
		ws.write(3,0,'RUC:',titulo_2)
		ws.write(3,1,self.company_id.vat or '',titulo_2)
		ws.merge_range('A5:B5','APELLIDO Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL:',titulo_2)
		ws.write(4,2,self.company_id.name or '',titulo_2)

		ws.merge_range('A8:B8','CUENTA Y SUBCUENTA CONTABLE',workbook.add_format(dict(styles_table,bottom=0)))
		ws.merge_range('A9:B9','',workbook.add_format(dict(styles_table,top=0)))
		ws.write(9,0,'CÓDIGO',titulo_3)
		ws.write(9,1,'DENOMINACIÓN',titulo_3)
		ws.merge_range('C8:D8','SALDOS INICIALES',workbook.add_format(dict(styles_table,bottom=0)))
		ws.merge_range('C9:D9','',workbook.add_format(dict(styles_table,top=0)))
		ws.write(9,2,'DEUDOR',titulo_3)
		ws.write(9,3,'ACREEDOR',titulo_3)
		ws.merge_range('E8:F8','MOVIMIENTOS',workbook.add_format(dict(styles_table,bottom=0)))
		ws.merge_range('E9:F9','',workbook.add_format(dict(styles_table,top=0)))
		ws.write(9,4,'DEBE',titulo_3)
		ws.write(9,5,'HABER',titulo_3)
		ws.merge_range('G8:H8','SALDOS FINALES',workbook.add_format(dict(styles_table,bottom=0)))
		ws.merge_range('G9:H9','',workbook.add_format(dict(styles_table,top=0)))
		ws.write(9,6,'DEUDOR',titulo_3)
		ws.write(9,7,'ACREEDOR',titulo_3)

		ws.merge_range('I8:N8','SALDOS FINALES DEL BALANCE GENERAL',workbook.add_format(dict(styles_table,bottom=0)))
		ws.write(9,8,'ACTIVO',titulo_3)
		ws.write(9,9,'PASIVO Y PATRIMONIO',titulo_3)
		ws.write(9,10,'PERDIDA N.',titulo_3)
		ws.write(9,11,'GANANCIAS N.',titulo_3)
		ws.write(9,12,'PERDIDA F.',titulo_3)
		ws.write(9,13,'GANANCIAS F.',titulo_3)

		#lines = self.report_amount_balances_optimized_line_ids.sorted(key=lambda ReportAmountBalancesOptimizedLine: (ReportAmountBalancesOptimizedLine.account_id.code))
		lines = self.report_amount_balances_optimized_line_ids
		initial_account = ''
		row = 10

		for line in lines:
			ws.write(row,0,line.account_id.code or '',titulo_5)
			ws.write(row,1,line.name_account or '',titulo_5)
			ws.write(row,2,line.saldos_iniciales_deudor or ' ',titulo_5)
			ws.write(row,3,line.saldos_iniciales_acreedor or ' ',titulo_5)
			ws.write(row,4,line.anio_fiscal_debe,titulo_5)
			ws.write(row,5,line.anio_fiscal_haber,titulo_5)
			ws.write(row,6,line.saldos_finales_deudor or '',titulo_5)
			ws.write(row,7,line.saldos_finales_acreedor or '',titulo_5)
			ws.write(row,8,line.balance_general_activo or '',titulo_5)
			ws.write(row,9,line.balance_general_pas_y_patr or '',titulo_5)
			ws.write(row,10,line.resultados_naturaleza_perdidas or '',titulo_5)
			ws.write(row,11,line.resultados_naturaleza_ganancias or '',titulo_5)
			ws.write(row,12,line.resultados_funcion_perdidas or '',titulo_5)
			ws.write(row,13,line.resultados_funcion_ganancias or '',titulo_5)
			row += 1
	
		workbook.close()



	def limpiar_campos(self):
		self.report_amount_balances_optimized_line_ids.unlink()
		self.name=None
		self.observations=None
		# self.fecha_inicio=None
		# self.fecha_final=None
		
		### LIMPIANDO FILTROS
		self.partner_ids=None
		self.account_ids=None
		self.journal_ids=None
		self.move_ids=None
		self.payment_ids=None
		#self.period_fiscal_year_ids=None
		### LIMPIANDO OPCIONES
		self.partner_option=None
		self.account_option=None
		self.journal_option=None
		self.move_option=None
		self.invoice_option=None
		self.payment_option=None
		self.periods_option=None
		self.balance_category='all'
		self.column_balance_category=None
		# self.order_print=None
		self.print_format=None

	###########################################################################################
	def get_query_filter_clause(self):

		filter_clause = ""
		
		if self.balance_category != 'all':
			filter_clause += " and acac.balance_category = '%s' " % (self.balance_category)

		partners=tuple(self.partner_ids.mapped('id'))
		len_partners = len(partners or '')
		if len_partners:
			filter_clause += " and aml.partner_id %s %s" % (self.partner_option or 'in', str(partners) if len_partners!=1 else str(partners)[0:len(str(partners))-2] + ')')

		journals = tuple(self.journal_ids.mapped('id'))
		len_journals = len(journals or '')
		if len(self.journal_ids):
			filter_clause += " and aml.journal_id %s %s " % (self.journal_option or 'in', str(journals) if len_journals!=1 else str(journals)[0:len(str(journals))-2] + ')')

		moves = tuple(self.move_ids.mapped('id'))
		len_moves = len(moves or '')
		if len(moves):
			filter_clause += " and aml.move_id %s %s " % (self.move_option or 'in', str(moves) if len_moves!=1 else str(moves)[0:len(str(moves))-2] + ')')


		payments = tuple(self.payment_ids.mapped('id'))
		len_payments = len(payments or '')
		if len(payments):
			filter_clause += " and aml.payment_id %s %s " % (self.payment_option or 'in', str(payments) if len_payments!=1 else str(payments)[0:len(str(payments))-2] + ')')


		accounts = tuple(self.account_ids.mapped('id'))
		len_accounts = len(accounts or '')
		if len(accounts):
			filter_clause += " and aml.account_id %s %s " % (self.account_option or 'in', str(accounts) if len_accounts!=1 else str(accounts)[0:len(str(accounts))-2] + ')')

		if self.currency_id and self.currency_id != self.company_id.currency_id:
			filter_clause += " and aml.currency_id=%s "%(self.currency_id.id)

		return filter_clause
	############################################################################################



	def query_balance_of_sums_and_balances(self,fecha_movimiento_debe,fecha_movimiento_haber):
		query=''
		
		filter_clause = self.get_query_filter_clause()
	
		if self.currency_id and self.currency_id == self.company_id.currency_id:
			query=unique_queries.query_account_amount_balances(fecha_movimiento_debe,fecha_movimiento_haber,filter_clause)

		elif self.currency_id:
			query=unique_queries.query_account_amount_balances_currency_native(fecha_movimiento_debe,fecha_movimiento_haber,filter_clause)

		self.env.cr.execute(query)
		records = self.env.cr.dictfetchall()
		return records



	def run_balance_of_sums_and_balances(self):
		self.report_amount_balances_optimized_line_ids.unlink()
		registro= []
		
		records=self.query_balance_of_sums_and_balances(self.fecha_inicio.strftime("%Y-%m-%d"),self.fecha_final.strftime("%Y-%m-%d"))

		saldo=[0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00]
		for line in records:
			account_id=self.env['account.account'].browse(line['id'])
			saldos_finales_deudor=(line['debit_saldo_inicial'] or 0.00) + (line['debit_movimiento_periodo'] or 0.00)
			saldos_finales_acreedor=(line['credit_saldo_inicial'] or 0.00) + (line['credit_movimiento_periodo'] or 0.00)

			balance_inicial=(line['debit_saldo_inicial'] or 0.00) - (line['credit_saldo_inicial'] or 0.00)

			balance=saldos_finales_deudor - saldos_finales_acreedor
			registro.append((0,0,{
				'account_id':line['id'],
				'name_account':' '.join([line['code'] or '' , line['name'] or '']),
				'saldos_iniciales_deudor':'{:,.2f}'.format(abs(balance_inicial)) if balance_inicial>0 else '',
				'saldos_iniciales_acreedor':'{:,.2f}'.format(abs(balance_inicial)) if balance_inicial<0 else '',
				'anio_fiscal_debe':'{:,.2f}'.format(line['debit_movimiento_periodo'] or 0.00) if line['debit_movimiento_periodo'] else '',
				'anio_fiscal_haber':'{:,.2f}'.format(line['credit_movimiento_periodo'] or 0.00) if line['credit_movimiento_periodo'] else '',
				'saldos_finales_deudor':'{:,.2f}'.format(abs(balance)) if balance>0 else '',
				'saldos_finales_acreedor':'{:,.2f}'.format(abs(balance)) if balance<0 else '',
				'balance_general_activo': '{:,.2f}'.format(abs(balance)) if account_id.balance_category=="balance" and balance>0 else '',
				'balance_general_pas_y_patr':'{:,.2f}'.format(abs(balance)) if account_id.balance_category=="balance" and balance<0 else '',
				'resultados_naturaleza_perdidas':'{:,.2f}'.format(abs(balance)) if account_id.balance_category in ["nature","function_nature"] and balance>0 else '',
				'resultados_naturaleza_ganancias':'{:,.2f}'.format(abs(balance)) if account_id.balance_category in ["nature","function_nature"] and balance<0 else '',
				'resultados_funcion_perdidas':'{:,.2f}'.format(abs(balance)) if account_id.balance_category in ["function","function_nature"] and balance>0 else '',
				'resultados_funcion_ganancias':'{:,.2f}'.format(abs(balance)) if account_id.balance_category in ["function","function_nature"] and balance<0 else '',
			}))

			saldo[0] += abs(balance_inicial) if balance_inicial>0 else 0.00
			saldo[1] += abs(balance_inicial) if balance_inicial<0 else 0.00
			saldo[2] += line['debit_movimiento_periodo'] or 0.00
			saldo[3] += line['credit_movimiento_periodo'] or 0.00
			saldo[4] += abs(balance) if balance>0 else 0.00
			saldo[5] += abs(balance) if balance<0 else 0.00
			saldo[6] += abs(balance) if account_id.balance_category=="balance" and balance>0 else 0.00
			saldo[7] += abs(balance) if account_id.balance_category=="balance" and balance<0 else 0.00
			saldo[8] += abs(balance) if account_id.balance_category in ["nature","function_nature"] and balance>0 else 0.00
			saldo[9] += abs(balance) if account_id.balance_category in ["nature","function_nature"] and balance<0 else 0.00
			saldo[10] += abs(balance) if account_id.balance_category in ["function","function_nature"] and balance>0 else 0.00
			saldo[11] += abs(balance) if account_id.balance_category in ["function","function_nature"] and balance<0 else 0.00


		registro.append((0,0,{
				'name_account':'SUMAS ',
				'saldos_iniciales_deudor':'{:,.2f}'.format(saldo[0]),
				'saldos_iniciales_acreedor':'{:,.2f}'.format(saldo[1]),
				'anio_fiscal_debe':'{:,.2f}'.format(saldo[2]),
				'anio_fiscal_haber':'{:,.2f}'.format(saldo[3]),
				'saldos_finales_deudor':'{:,.2f}'.format(saldo[4]),
				'saldos_finales_acreedor':'{:,.2f}'.format(saldo[5]),
				'balance_general_activo': '{:,.2f}'.format(saldo[6]),
				'balance_general_pas_y_patr':'{:,.2f}'.format(saldo[7]),
				'resultados_naturaleza_perdidas':'{:,.2f}'.format(saldo[8]),
				'resultados_naturaleza_ganancias':'{:,.2f}'.format(saldo[9]),
				'resultados_funcion_perdidas':'{:,.2f}'.format(saldo[10]),
				'resultados_funcion_ganancias':'{:,.2f}'.format(saldo[11]),
			}))


		resultado=[saldo[i-1]-saldo[i] for i in [1,3,5,7,9,11]]
		registro.append((0,0,{
				# 'account_id':,
				'name_account':'RESULTADO ',
				'saldos_iniciales_deudor':'{:,.2f}'.format(abs(resultado[0]) if resultado[0]>0 else 0.00),
				'saldos_iniciales_acreedor':'{:,.2f}'.format(abs(resultado[0]) if resultado[0]<=0 else 0.00),
				'anio_fiscal_debe':'{:,.2f}'.format(abs(resultado[1]) if resultado[1]>0 else 0.00),
				'anio_fiscal_haber':'{:,.2f}'.format(abs(resultado[1]) if resultado[1]<=0 else 0.00),
				'saldos_finales_deudor':'{:,.2f}'.format(abs(resultado[2]) if resultado[2]>0 else 0.00),
				'saldos_finales_acreedor':'{:,.2f}'.format(abs(resultado[2]) if resultado[2]<=0 else 0.00),
				'balance_general_activo': '{:,.2f}'.format(abs(resultado[3]) if resultado[3]<0 else 0.00),
				'balance_general_pas_y_patr':'{:,.2f}'.format(abs(resultado[3]) if resultado[3]>=0 else 0.00),
				'resultados_naturaleza_perdidas':'{:,.2f}'.format(abs(resultado[4]) if resultado[4]<0 else 0.00),
				'resultados_naturaleza_ganancias':'{:,.2f}'.format(abs(resultado[4]) if resultado[4]>=0 else 0.00),
				'resultados_funcion_perdidas':'{:,.2f}'.format(abs(resultado[5]) if resultado[5]<0 else 0.00),
				'resultados_funcion_ganancias':'{:,.2f}'.format(abs(resultado[5]) if resultado[5]>=0 else 0.00),
			}))


		registro.append((0,0,{
				'name_account':'TOTALES ',
				
				'saldos_iniciales_deudor':'0.00',
				'saldos_iniciales_acreedor':'0.00',
				'anio_fiscal_debe':'0.00',
				'anio_fiscal_haber':'0.00',
				'saldos_finales_deudor':'0.00',
				'saldos_finales_acreedor':'0.00',
				'balance_general_activo': '{:,.2f}'.format((abs(resultado[3]) if resultado[3]<0 else 0.00)+ saldo[6]),
				'balance_general_pas_y_patr':'{:,.2f}'.format((abs(resultado[3]) if resultado[3]>0 else 0.00)+ saldo[7]),
				'resultados_naturaleza_perdidas':'{:,.2f}'.format((abs(resultado[4]) if resultado[4]<0 else 0.00)+ saldo[8]),
				'resultados_naturaleza_ganancias':'{:,.2f}'.format((abs(resultado[4]) if resultado[4]>0 else 0.00)+ saldo[9]),
				'resultados_funcion_perdidas':'{:,.2f}'.format((abs(resultado[5]) if resultado[5]<0 else 0.00)+ saldo[10]),
				'resultados_funcion_ganancias':'{:,.2f}'.format((abs(resultado[5]) if resultado[5]>0 else 0.00)+ saldo[11]),
			}))
		

		self.report_amount_balances_optimized_line_ids=registro
		
		self.state='generated'
