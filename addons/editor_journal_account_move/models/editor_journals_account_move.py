from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
from itertools import *
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class EditorJournalsAccountMove(models.TransientModel):
	_name = 'editor.journals.account.move'
	_description = "Editor de Diarios en Asientos Contables"
	
	editor_journals_account_move_line_ids=fields.One2many('editor.journals.account.move.line','editor_journals_account_move_id',string="Asientos Contables a Editar")
	##############
	buffer_account_move_ids=fields.Many2many('account.move','account_move_editor_rel',
		'move_id','editor_id' ,string="Asientos Contables Seleccionados", readonly=False)
	###### OPERACIONES MASIVAS
	massive_journal=fields.Many2one('account.journal',string="Diario")


	def limpiar_buffer(self):
		for rec in self:
			rec.buffer_account_move_ids=None


	def add_lines(self):
		if self.buffer_account_move_ids:
			registro=[]
			for line in self.buffer_account_move_ids:
				registro.append({'move_id': line.id,'editor_journals_account_move_id':self.id})

			self.editor_journals_account_move_line_ids.create(registro)


	def aplication_massive(self):
		if self.editor_journals_account_move_line_ids:
			for line in self.editor_journals_account_move_line_ids:
				line.onchange_massive_journal()


	def update_account_move(self,move_id,journal_id):
		query_account_move_line = ""
		#if period_fiscalyear_id:
		query_account_move_line += """update account_move_line set journal_id=%s"""%(journal_id.id or 'Null')
		query_account_move_line += """ where move_id=%s"""%(move_id.id)

		self.env.cr.execute(query_account_move_line)
		###########################################################################
		
		query_account_move = """update account_move set journal_id=%s"""%(journal_id.id or 'Null')

		query_account_move += """ where id=%s"""%(move_id.id)

		self.env.cr.execute(query_account_move)


	def update_account_move_massive(self):
		if self.editor_journals_account_move_line_ids:

			for line in self.editor_journals_account_move_line_ids:
				self.update_account_move(line.move_id,line.journal_id)
		else:
			raise UserError(_('NO SE ESTA PROCESANDO NINGÚN ASIENTO CONTABLE, PROCEDA AGREGANDO LINEAS !!'))

