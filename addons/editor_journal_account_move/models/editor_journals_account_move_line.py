from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
from itertools import *
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class EditorJournalsAccountMoveLine(models.TransientModel):
	_name = 'editor.journals.account.move.line'
	_description = "Editor de Diarios en Asientos Contables (Detalles)"

	editor_journals_account_move_id = fields.Many2one("editor.journals.account.move", string="Editar Asiento Contable", ondelete="cascade")

	move_id=fields.Many2one('account.move',string="Asiento Contable")
	date=fields.Date(string="Fecha del Asiento",compute="compute_campo_date",readonly=True)

	original_journal_id=fields.Many2one('account.journal', string='Diario Original',compute="compute_campo_original_journal_id",store=True)

	journal_id = fields.Many2one('account.journal', string='Diario')


	@api.depends('move_id')
	def compute_campo_date(self):
		for rec in self:
			if rec.move_id:
				rec.date=rec.move_id.date

	@api.depends('move_id')
	def compute_campo_original_journal_id(self):
		for rec in self:
			if rec.move_id:
				rec.original_journal_id=rec.move_id.journal_id


	def onchange_massive_journal(self):
		if self.editor_journals_account_move_id.massive_journal:
			if self.editor_journals_account_move_id.massive_journal:
				if self.move_id:
					self.journal_id = self.editor_journals_account_move_id.massive_journal