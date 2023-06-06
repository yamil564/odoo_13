from odoo import fields,models,api
import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError , ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
	_inherit = "account.move"



	def button_cancel(self):
		for rec in self:
			rec._balance_end_real()
			super(AccountMove,rec).button_cancel()

	## al pasar a borrador no se elimina el registro del extracto, por ello cuando el asiento se vuelve a publicar,se vuelve a
	## insertar el mismo movimiento en el extracto
	def button_draft(self):
		for rec in self:
			rec._balance_end_real()
			super(AccountMove,rec).button_draft()



	def _balance_end_real(self):
		statement_line_obj = self.mapped('line_ids.statement_extract_line_id')
		statement_obj = statement_line_obj.mapped('statement_id')
		statement_line_obj.unlink()
		for statement in statement_obj:
			statement.balance_end_real = statement.balance_start + sum(l.amount for l in statement.line_ids)


	def post(self):
		res = super(AccountMove , self).post()
		for rec in self:
			self._create_bank_reconcile()
		
		return res


	def get_line_ids(self, account_ids):
		return self.mapped('line_ids').filtered(lambda line: line.account_id.id in account_ids.ids)


	def _create_bank_reconcile(self):
		diarios_ids = self.env['account.journal'].search([('type','in',['bank','cash']),('periodo_registro','!=','Manual')])
		account_ids = diarios_ids.mapped("default_debit_account_id") + diarios_ids.mapped("default_credit_account_id")
		line_ids = self.mapped('line_ids').filtered(lambda line: line.account_id.id in account_ids.ids)
		

		for line in line_ids:

			j = diarios_ids.filtered(lambda d: line.account_id == d.default_debit_account_id or line.account_id == d.default_credit_account_id)
			if len(j or '')>1:
				raise UserError("La cuenta %s-%s existe en varios diarios" %(line.account_id.code, line.account_id.name))

			statement_obj = line.move_id._search_or_create_bank_statement(j[0])
			statement_line_data = line.move_id._create_bank_statement_line_data(statement_obj, line)
			statement_line = self.env['account.bank.statement.line'].create(statement_line_data)
			line.statement_extract_line_id = statement_line.id
			statement_obj.balance_end_real = statement_obj.balance_start + sum(l.amount for l in statement_obj.line_ids)


	# def _create_bank_reconcile(self):
	# 	diarios_ids = self.env['account.journal'].search([('type','in',['bank','cash']),('periodo_registro','!=','Manual')])
	# 	for move in self:
	# 		for line in move.line_ids:
	# 			for j in diarios_ids:
	# 				if (line.account_id == j.default_debit_account_id or line.account_id == j.default_credit_account_id):
	# 					statement_obj = move._search_or_create_bank_statement(j)
	# 					statement_line_data = move._create_bank_statement_line_data(statement_obj, line)
	# 					statement_line = self.env['account.bank.statement.line'].create(statement_line_data)
	# 					line.statement_extract_line_id = statement_line.id
	# 					statement_obj.balance_end_real = statement_obj.balance_start + sum(l.amount for l in statement_obj.line_ids)

	def _create_bank_statement_line_data(self, statement_obj, line):
		values = {
			'amount':line.balance,
			'date':line.date ,
			'name':line.name or '',
			'partner_id':line.partner_id and line.partner_id.id or False,
			'statement_id':statement_obj.id,
			'ref':line.move_id.ref or '',
			'move_line_id' : line.id,
			'company_id':line.company_id.id or False,
		}
		if line.journal_id.currency_id and line.journal_id.currency_id != line.company_currency_id:
			values.update(
				# currency_id=line.currency_id.id,
				amount = line.amount_currency,
				amount_currency = line.balance,
				)
		if line.payment_id:
			if 'operation_number' in line.payment_id._fields and line.payment_id.operation_number:
				values.update(
					operation_number = line.payment_id.operation_number
					)
		return values


	def _search_or_create_bank_statement(self, journal):
		record=self.env['account.bank.statement'].search(
			[('date','<=',self.date),('fecha_fin','>=',self.date),('journal_id.id','=',journal.id),
			('state','!=','confirm')], order='date desc' , limit=1 )
		
		if not record:
			vals = {
				'name': self._create_name_account_bank_statement(journal) ,
				'date':self._format_register(journal.periodo_registro),
				'fecha_fin': self._get_date_end(journal.periodo_registro),
				'journal_id': journal.id,}

			record=self.env['account.bank.statement'].create(vals)
		return record


	def _get_month(self, month, nro, ult=False):
		if month%nro == 0:
			if ult:
				return month
			return month - nro + 1
		mes = month - (month%nro) + nro
		incremento = 1
		if ult:
			incremento = nro
		mes = mes - nro + incremento
		return mes


	def _get_day(self, date, type, number_day,ult):
		if type =='Diario':
			return date
		elif type=='Semanal':
			interval=int(date.strftime("%w"))-number_day
			if interval>=0:
				if ult:
					return date + timedelta(days=6-interval)
				else:
					return date - timedelta(days=interval)
			else:
				if ult:
					return date + timedelta(days=-interval-1)
				else:
					return date - timedelta(days=7+interval)
		elif type=='Quincenal':
			if date.day<=15:
				if ult:
					return datetime(date.year, date.month,15)
				else:
					return datetime(date.year,date.month,1)
			else:
				if ult:
					return datetime(date.year,date.month,calendar.monthrange(date.year, date.month)[1])
				else:
					return datetime(date.year, date.month,16)

	def _format_register(self, type):
		fecha = self.date
		dic={
			'Diario' : 1,
			'Semanal' : 1, #esta por verse
			'Quincenal' : 1, #esta por verse
			'Mensual' : 1,
			'Bimestral' : 2,
			'Trimestral' : 3,
			'Cuatrimestre' : 4,
			'Semestral' : 6,
			'Anual' : 12,
		}
		if type in ['Diario','Semanal','Quincenal']:
			return self._get_day(self.date,type,int(self.journal_id.inicio_semana),False)
		date = datetime(fecha.year, self._get_month(fecha.month, dic[type]),1)
		return date


	def _get_date_end(self, type):
		fecha = self.date
		dic={
			'Diario' : 1,
			'Semanal' : 1, #esta por verse
			'Quincenal' : 1, #esta por verse
			'Mensual' : 1,
			'Bimestral' : 2,
			'Trimestral' : 3,
			'Cuatrimestre' : 4,
			'Semestral' : 6,
			'Anual' : 12,
		}
		if type == 'Diario':
			return self._get_day(self.date,type,int(self.journal_id.inicio_semana),True)
		mes = self._get_month(fecha.month, dic[type], ult=True)
		date = datetime(fecha.year, mes, calendar.monthrange(fecha.year, mes)[1])
		return date


	def _create_name_account_bank_statement(self,journal_id):
		fecha = self._format_register(journal_id.periodo_registro)
		return journal_id.name + '/' + journal_id.periodo_registro + '/'+ fecha.strftime("%d-%m-%Y")