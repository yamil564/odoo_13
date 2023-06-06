# -*- coding: utf-8 -*-
import calendar
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import xlsxwriter
from odoo.exceptions import UserError , ValidationError

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

class WizardPrinterPleDiary(models.TransientModel):
	_name='wizard.printer.ple.diary'
	_inherit='wizard.printer.ple.base'
	_description = "Modulo Formulario Impresión PLE Libro Diario"

	ple_diary_id = fields.Many2one('ple.diary',string="PLE DIARIO",readonly=True,required=True)

	identificador_operaciones = fields.Selection(selection=[('0','Cierre de operaciones'),('1','Empresa operativa'),('2','Cierre de libro')],
		string="Identificador de operaciones", required=True, default="1")
	identificador_libro = fields.Selection(selection='available_formats_diary_sunat', string="Identificador de libro" )
	print_order = fields.Selection(default="codigo_cuenta_desagregado")

	## BLOQUES DE IMPRESIÓN
	block_counter=fields.Integer(string="Bloque de Impresión N°" , default=0 , readonly=True)
	block_size=fields.Integer(string="Número de Registros por bloque", default=3000)
	##########################
	##buffer para asientos a apuntes

	fecha_impresion=fields.Date(string="Fecha de Impresión manual",
		default=datetime(datetime.now().year,datetime.now().month,datetime.now().day).date())

	fin_asiento=fields.Boolean(default=False)
	fin_documento=fields.Boolean(default=False)

	infimo=fields.Integer(default=0, string="Infimo")
	supremo=fields.Integer(default=0,string="Supremo")

	############################################################################
	def action_print(self):
		if (self.print_format and self.identificador_libro and self.identificador_operaciones) :
			if self.print_format =='pdf':
				return self.print_quotation()
			elif self.print_format =='xlsx' and self.identificador_libro=='050200':
				raise UserError(_("ESTE FORMATO NO ESTA DISPONIBLE !!"))
			else:
				return super(WizardPrinterPleDiary,self).action_print()
		else:
			raise UserError(_('NO SE PUEDE IMPRIMIR , Los campos: Formato Impresión , Identificador de operaciones y Identificador de libro son obligatorios, llene esos campos !!!'))



	def available_formats_diary_sunat(self):
		formats=[('050100','Libro diario'),
				('050200','Libro diario simplificado'),
				('060100','Libro Mayor'),
			]
		return formats


	
	def print_quotation(self):
		if self.identificador_libro=='050100':
			self.infimo=self.supremo
			self.supremo += self.block_size	

			if self.supremo <= len(self.ple_diary_id.ple_diary_line_ids)-1:
				if self.ple_diary_id.ple_diary_line_ids[self.supremo-1].move_id.id==self.ple_diary_id.ple_diary_line_ids[self.supremo].move_id.id:
					self.fin_asiento=False
				else:
					self.fin_asiento=True
			else:
				self.fin_asiento=True
				self.fin_documento=True

			self.block_counter += 1
			return self.env.ref('ple_diary.report_custom_a4').with_context(discard_logo_check=True).report_action(self)
		elif self.identificador_libro == '060100':
			self.infimo=self.supremo
			self.supremo += self.block_size	
			if self.supremo <= len(self.ple_diary_id.ple_diary_line_ids)-1:
				if self.ple_diary_id.ple_diary_line_ids[self.supremo-1].move_id.id==self.ple_diary_id.ple_diary_line_ids[self.supremo].move_id.id:
					self.fin_asiento=False
				else:
					self.fin_asiento=True
			else:
				self.fin_asiento=True
				self.fin_documento=True
			self.block_counter += 1
			self._get_current_accounts()
			return self.env.ref('ple_diary.report_custom_ledger').with_context(discard_logo_check=True).report_action(self)
		elif self.identificador_libro=='050200':
			return self.env.ref('ple_diary.report_custom_a4_simplificado').with_context(discard_logo_check=True).report_action(self)


	#########################################

	def _get_current_accounts(self):
		lines = sorted(self.ple_diary_id.ple_diary_line_ids , key=lambda PleDiaryLine: (PleDiaryLine.codigo_cuenta_desagregado, PleDiaryLine.asiento_contable, PleDiaryLine.fecha_contable))
		blocks = lines[self.infimo:self.supremo]
		end = self.supremo + 1 <= len(lines) and self.supremo + 1 or (len(lines) - 1)
		if blocks[-1].codigo_cuenta_desagregado_id.id == lines[end].codigo_cuenta_desagregado_id.id:
			if blocks[-1].id != lines[end].id:
				self.supremo = list(map(lambda line: line.codigo_cuenta_desagregado_id.id, lines)).index(blocks[-1].codigo_cuenta_desagregado_id.id)
			else:
				self.supremo =  end + 1



	def criterios_impresion(self):
		res = super(WizardPrinterPleDiary,self).criterios_impresion() or []
		res += [('codigo_cuenta_desagregado','Código Cuenta Desagregado')]
		return res


	def _get_order_print(self , object):

		if self.print_order == 'date': # ORDENAMIENTO POR LA FECHA CONTABLE
			total=sorted(object, key=lambda PleDiaryLine: (PleDiaryLine.asiento_contable , PleDiaryLine.codigo_cuenta_desagregado , PleDiaryLine.fecha_contable))
		elif self.print_order == 'nro_documento':
			total=sorted(object , key=lambda PleDiaryLine: (PleDiaryLine.asiento_contable))
		elif self.print_order == 'codigo_cuenta_desagregado':
			total=sorted(object , key=lambda PleDiaryLine: (PleDiaryLine.asiento_contable,PleDiaryLine.fecha_contable,PleDiaryLine.codigo_cuenta_desagregado ))
		return total


	def file_name(self, file_format):
		nro_de_registros = '1' if len(self.ple_diary_id.ple_diary_line_ids)>0 else '0'
		if self.ple_diary_id.periodo:
			file_name = "LE%s%s%s00%s%s%s1.%s" % (self.ple_diary_id.company_id.vat, self.ple_diary_id._periodo_fiscal(),
									self.identificador_libro, self.identificador_operaciones, nro_de_registros,
									self.ple_diary_id.currency_id.code_ple or '1', file_format)
		elif self.fecha:
			file_name = "LE%s%s%s00%s%s%s1.%s" % (self.ple_diary_id.company_id.vat, "%s00" %(self.date_to.strftime('%Y%m')),
									self.identificador_libro, self.identificador_operaciones, nro_de_registros,
									self.ple_diary_id.currency_id.code_ple or '1', file_format)
		return file_name


	def _init_buffer(self, output):
		if self.print_format == 'xlsx':
			if self.identificador_libro=='050100':
				self._generate_xlsx(output)
			elif self.identificador_libro=='060100':
				self._generate_ledger_xlsx(output)
			'''elif self.identificador_libro=='050200':
				raise UserError(_("ESTE FORMATO NO ESTA DISPONIBLE"))'''
				#raise UserError(_(salida))

		elif self.print_format == 'txt':
			if self.identificador_libro in ['050200','060100','050100']:
				self._generate_txt(output)
			
		return output


	def _convert_object_date(self, date):
		# parametro date que retorna un valor vacio o el foramto 01/01/2100 dia/mes/año
		if date:
			return date.strftime("%d/%m/%Y")
		else:
			return ''


	def _generate_txt(self, output):
	
		for line in self._get_order_print(self.ple_diary_id.ple_diary_line_ids) :
			escritura="%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n" % (
				line.periodo_apunte,
				(line.asiento_contable or '')[:40] ,
				(line.m_correlativo_asiento_contable or '')[:10] ,
				(line.codigo_cuenta_desagregado or '')[:24] ,
				(line.codigo_unidad_operacion or '')[:24]  ,
				(line.codigo_centro_costos or '')[:24] ,
				(line.tipo_moneda_origen or '')[:3] ,
				(line.tipo_doc_iden_emisor or '')[:1] ,
				(line.num_doc_iden_emisor or '')[:15] ,
				(line.tipo_comprobante_pago or '')[:2] ,
				(line.num_serie_comprobante_pago or '')[:20] ,
				(line.num_comprobante_pago or '')[:20],
				self._convert_object_date(line.fecha_contable) ,
				self._convert_object_date(line.fecha_vencimiento) ,
				self._convert_object_date(line.fecha_operacion) ,
				(line.glosa or '')[:200] ,
				(line.glosa_referencial or '')[:200],
				format(line.movimientos_debe,".2f") ,
				format(line.movimientos_haber,".2f") ,
				(line.dato_estructurado or '')[:92] ,
				line.indicador_estado_operacion or '' )

			output.write(escritura.encode())

	################################

	def get_initial_values(self):
		lines = self.env['account.move.line'].search([('date','<',"%s-%s-01" %(self.ple_diary_id.fiscal_year, self.ple_diary_id.fiscal_month))])
		account_dic = {}
		for line in lines:
			account_dic.setdefault(line.account_id,[0.0,0.0])
			account_dic[line.account_id][0] += line.debit
			account_dic[line.account_id][1] += line.credit
		return account_dic


	def get_initial_values_sql(self):
		fecha_inicial = ''

		if self.ple_diary_id.periodo:
			fecha_inicial = "%s-%s-01" %(self.ple_diary_id.fiscal_year, self.ple_diary_id.fiscal_month)
		elif self.ple_diary_id.fecha:
			fecha_inicial = self.ple_diary_id.date_from.strftime("%Y-%m-%d")

		query="""select aml.account_id,acac.code,acac.name 
			sum(aml.balance) from 
			account_move_line as aml join account_account acac on acac.id=aml.account_id 
			where aml.date < '%s' group by aml.account_id""" %(fecha_inicial)


	def _generate_xlsx(self, output):
		workbook = xlsxwriter.Workbook(output)
		ws = workbook.add_worksheet('Libro diario')
		titulo1 = workbook.add_format({'font_size': 16, 'align': 'center', 'text_wrap': True, 'bold': True, 'font_name':'Arial'})
		titulo_1 = workbook.add_format({'font_size': 8, 'align': 'left', 'text_wrap': True, 'bold': True, 'font_name':'Arial'})
		titulo2 = workbook.add_format({'font_size': 8, 'align': 'center','valign': 'vcenter','color':'black', 'text_wrap': True, 'left':True, 'right':True,'bottom': True, 'top': True, 'bold':True , 'font_name':'Arial'})
		#######################################################
		titulo_2 = workbook.add_format({'font_size': 8, 'align': 'center', 'text_wrap': True, 'bold': True, 'font_name':'Arial'})
		##################################################################
		titulo5 = workbook.add_format({'font_size': 10, 'align': 'left', 'text_wrap':True, 'font_name':'Arial', 'bold':True})

		titulo6 = workbook.add_format({'font_size': 8, 'align': 'right', 'text_wrap': True, 'top': True, 'bold':True , 'font_name':'Arial'})
		number_left = workbook.add_format({'font_size': 8, 'align': 'left', 'num_format': '#,##0.00', 'font_name':'Arial'})
		number_right = workbook.add_format({'font_size': 8, 'align': 'right', 'num_format': '#,##0.00', 'font_name':'Arial'})
		number_right_tax_rate = workbook.add_format({'font_size': 8, 'align': 'right', 'num_format': '#,##0.000', 'font_name':'Arial'})
		
		letter1 = workbook.add_format({'font_size': 7, 'align': 'left', 'font_name':'Arial'})
		letter3 = workbook.add_format({'font_size': 7, 'align': 'right','num_format': '#,##0.00', 'font_name':'Arial'})
		letter3_negrita = workbook.add_format({'font_size': 7, 'align': 'right','num_format': '#,##0.00', 'font_name':'Arial','bold': True})

		ws.set_column('A:A', 2,letter1)
		ws.set_column('B:B', 24,letter1)
		ws.set_column('C:C', 11.5,letter1)
		ws.set_column('D:D', 30,letter1)
		ws.set_column('E:E', 11,letter1)
		ws.set_column('F:F', 13,letter1)
		ws.set_column('G:G', 13,letter1)
		ws.set_column('H:H', 8,letter1)
		ws.set_column('I:I', 30,letter1)
		ws.set_column('J:J', 11.5,number_right)
		ws.set_column('K:K', 11.5,number_right)
		ws.set_column('L:L', 9,number_right)

		ws.merge_range('B1:E1','FORMATO 5.1: LIBRO DIARIO',titulo1)

		ws.merge_range("B7:B8",'NÚMERO CORRELATIVO DEL REGISTRO O CÓDIGO ÚNICO DE LA OPERACIÓN',titulo2)
		ws.merge_range("C7:C8",'FECHA DE LA OPERACIÓN',titulo2)
		ws.merge_range("D7:D8",'GLOSA O DESCRIPCIÓN DE LA OPERACIÓN',titulo2)

		ws.merge_range('E7:G7','REFERENCIA DE LA OPERACIÓN', titulo2)
		ws.write(7,4,'CÓDIGO DEL LIBRO O REGISTRO', titulo2)
		## 7 , 8 , 9 
		ws.write(7,5,'NÚMERO CORRELATIVO', titulo2)
		ws.write(7,6,'NÚMERO DEL DOCUMENTO SUSTENTATORIO', titulo2)

		ws.merge_range('H7:I7','CUENTA CONTABLE ASOCIADA A LA OPERACIÓN', titulo2)
		ws.write(7,7,'CÓDIGO', titulo2)
		ws.write(7,8,'DENOMINACIÓN', titulo2)
		ws.merge_range('J7:K7','MOVIMIENTO', titulo2)
		ws.write(7,9,'DEBE', titulo2)
		ws.write(7,10,'HABER', titulo2)
		

		ws.write(2,1,'PERIODO:',titulo_1)
		ws.write(3,1,'RUC:',titulo_1)
		ws.merge_range('B5:D5','APELLIDO Y NOMBRES, DENOMINACIÓN O RAZÓN SOCIAL:',titulo_1)
		ws.write(3,2,self.ple_diary_id.company_id.vat or '',titulo_2)

		ws.write(2,2,self.ple_diary_id._periodo_fiscal() or '',titulo_2)
		ws.merge_range('E5:I5',self.ple_diary_id.company_id.name or '',titulo_2)
		
		ws.freeze_panes(9,0)

		fila=8
		total=[0.0 ,0.0 ,0.0 ,0.0 ,0.0 ,0.0 ,0.0 ,0.0 ,0.0 ,0.0 ]

		asiento_contable_inicial=""
		haber_asiento_contable=0
		deber_asiento_contable=0
		total_haber=0
		total_deber=0
		ws.write(8,3,"PERIODO :" + self.ple_diary_id.fiscal_month)
		for line in  self._get_order_print(self.ple_diary_id.ple_diary_line_ids) :
			fila += 1
			if(fila > 9 and line.asiento_contable != asiento_contable_inicial ):
				ws.write(fila,8,"TOTAL EN EL RegCtb " + asiento_contable_inicial)
				ws.write(fila,9,deber_asiento_contable)
				ws.write(fila,10,haber_asiento_contable)
				deber_asiento_contable=0
				haber_asiento_contable=0
				fila += 1 
				ws.write(fila,3,"REGISTRO CONTABLE : " + (line.asiento_contable or ''))
				asiento_contable_inicial = line.asiento_contable
				fila += 1
			elif(line.asiento_contable != asiento_contable_inicial ):
				ws.write(fila,3,"REGISTRO CONTABLE : " + (line.asiento_contable or ''))
				asiento_contable_inicial = line.asiento_contable
				fila += 1

			ws.write(fila,1, line.asiento_contable)
			ws.write(fila,2,self._convert_object_date(line.fecha_operacion) or '' )
			ws.write(fila,4, "5")

			ws.write(fila,3,line.glosa or '' )

			ws.write(fila,6, (len(line.num_serie_comprobante_pago or '')!=0)*(str(line.num_serie_comprobante_pago or '') + '-' + str(line.num_comprobante_pago or '')) )
			ws.write(fila,7,line.codigo_cuenta_desagregado or '')
			ws.write(fila,8,line.codigo_cuenta_desagregado_id.name or '')
			ws.write(fila,9,line.movimientos_debe)
			ws.write(fila,10,line.movimientos_haber)
			haber_asiento_contable += line.movimientos_haber
			deber_asiento_contable += line.movimientos_debe
			total_haber += line.movimientos_haber
			total_deber += line.movimientos_debe
		########### ULTIMO ASIENTO
		fila += 1 
		ws.write(fila,8,"TOTAL EN EL RegCtb " + asiento_contable_inicial)
		ws.write(fila,9,deber_asiento_contable)
		ws.write(fila,10,haber_asiento_contable)
		##########################
		fila += 1
		ws.write(fila , 8,"TOTAL EN EL PERIODO " + self.ple_diary_id.fiscal_month)
		ws.write(fila  , 9 ,  total_deber)
		ws.write(fila  , 10 ,  total_haber)	
		workbook.close()

	##################

	def _generate_ledger_xlsx(self, output):
		workbook = xlsxwriter.Workbook(output)
		ws = workbook.add_worksheet('Libro Mayor')
		titulo_1_0 = workbook.add_format({'font_size': 10, 'font_name':'Arial'})
		titulo_1 = workbook.add_format({'font_size': 8, 'font_name':'Arial'})
		titulo_2 = workbook.add_format({ 'font_size': 8, 'font_name':'Arial', 'bold': True, 'align': 'center', 'valign': 'center', 'border': 1})
		titulo_3 = workbook.add_format({ 'font_size': 8, 'font_name':'Arial', 'bold': True})
		ws.set_column('A:A', 13,titulo_1)
		ws.set_column('B:B', 16,titulo_1)
		ws.set_column('C:C', 30,titulo_1)
		ws.set_column('G:G', 16,titulo_1)
		ws.set_column('H:H', 16,titulo_1)
		ws.set_row(5, 20,titulo_1)
		ws.write(0,0,'Formato 6.1', titulo_1)
		ws.write(0,1,'Libro Mayor', titulo_1_0)
		ws.write(1,0,'Periodo', titulo_1)
		ws.write(1,1,self.ple_diary_id._periodo_fiscal(), titulo_1)
		ws.write(2,0,'RUC', titulo_1)
		ws.write(2,1,self.ple_diary_id.company_id.vat, titulo_1)
		ws.write(3,0,'Razón Social', titulo_1)
		ws.write(3,1,self.ple_diary_id.company_id.name, titulo_1)
		ws.write(4,0,'Expresado en', titulo_1)
		ws.write(5,0,'FECHA',titulo_2)
		ws.write(5,1,'NÚMERO',titulo_2)
		ws.write(5,2,'DESCRIPCIÓN DE LA OPERACIÓN',titulo_2)
		ws.merge_range('D6:F6','DOCUMENTO REFERENCIA',titulo_2)
		ws.write(5,6,'CÓDIGO',titulo_2)
		ws.write(5,7,'MOVIMIENTO',titulo_2)
		ws.write(5,8,'',titulo_2)
		ws.write(6,0,'OPERACIÓN',titulo_2)
		ws.write(6,1,'COMPROBANTE',titulo_2)
		ws.write(6,2,'',titulo_2)
		ws.write(6,3,'TD',titulo_2)
		ws.write(6,4,'NÚMERO',titulo_2)
		ws.write(6,5,'FECHA',titulo_2)
		ws.write(6,6,'ANEXO',titulo_2)
		ws.write(6,7,'DEBE',titulo_2)
		ws.write(6,8,'HABER',titulo_2)
		row = 7
		initial_accounting_entry = ''
		debe = 0
		credit = 0
		lines = sorted(self.ple_diary_id.ple_diary_line_ids , key=lambda PleDiaryLine: (PleDiaryLine.codigo_cuenta_desagregado, PleDiaryLine.asiento_contable, PleDiaryLine.fecha_contable))
		initial_values = self.get_initial_values()

		def total_balances(row):
			ws.write(row,3,'TOTAL MOVIMIENTO CUENTA',titulo_1)
			ws.write(row,7,debe,titulo_1)
			ws.write(row,8,credit,titulo_1)
			row += 1
			ws.write(row,3,'SALDO ACTUAL',titulo_1)
			current_balance = debe + (previous_balance if previous_balance else 0) - credit
			if current_balance >= 0:
				ws.write(row,7,abs(round(current_balance,1)),titulo_1)
			else:
				ws.write(row,8,abs(round(current_balance,1)),titulo_1)
			return row
		
		previous_balance = False
		for line in lines:
			if line.codigo_cuenta_desagregado_id.id != initial_accounting_entry:
				if row > 7:
					row = total_balances(row)
					debe = 0
					credit = 0
					row += 1

				initial_accounting_entry = line.codigo_cuenta_desagregado_id.id
				ws.write(row,0,line.codigo_cuenta_desagregado_id.code, titulo_3)
				ws.write(row,1,line.codigo_cuenta_desagregado_id.name, titulo_3)
				row += 1
				ws.write(row,3,'SALDO ANTERIOR', titulo_1)
				previous_balance = initial_values.get(line.codigo_cuenta_desagregado_id, False)

				if previous_balance:
					previous_balance = previous_balance[0] - previous_balance[1]
					if previous_balance >= 0:
						ws.write(row,7,abs(round(previous_balance,1)) or '', titulo_1)
					else:
						ws.write(row,8,abs(round(previous_balance,1)) or '', titulo_1)
				else:
					ws.write(row,8,'', titulo_1)
				row += 1

			ws.write(row,0,self._convert_object_date(line.fecha_operacion or ''),titulo_1)
			ws.write(row,1,line.move_id.name or '',titulo_1)
			ws.write(row,2,line.glosa or '',titulo_1)
			ws.write(row,3,line.tipo_comprobante_pago or '',titulo_1)
			ws.write(row,4,"%s-%s"%(line.num_serie_comprobante_pago or "", line.num_comprobante_pago or "") or '',titulo_1)
			ws.write(row,5,self._convert_object_date(line.fecha_contable or ''),titulo_1)
			ws.write(row,6,line.num_doc_iden_emisor or '',titulo_1)
			ws.write(row,7,line.movimientos_debe or '',titulo_1)
			ws.write(row,8,line.movimientos_haber or '',titulo_1)
			debe += line.movimientos_debe
			credit += line.movimientos_haber
			row += 1
			if line == lines[-1]:
				row = total_balances(row)
				row += 1
				ws.write(row,3,'TOTAL GENERAL',titulo_1)
				ws.write(row,7,round(sum([i.movimientos_debe for i in lines]),2),titulo_1)
				ws.write(row,8,round(sum([i.movimientos_haber for i in lines]),2),titulo_1)
		workbook.close()


	def is_menor(self,a,b):
		return a<b