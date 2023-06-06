from odoo import fields,models,api

class AccountBankStatementLine(models.Model):
	_inherit = "account.bank.statement.line"

	move_line_id = fields.Many2one('account.move.line', string="Apunte contable")
	operation_number = fields.Char(string="Número de operación")#, compute='_compute_operation_number',store=True)	


	def button_view_account_move_line(self):

		return {
			'name': 'Diarios',
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'account.move.line',
			'view_id': False,
			'type': 'ir.actions.act_window',
			'domain': [('id', 'in', self.mapped('move_line_id').ids or [])],
			'context': {
				'journal_id': self.journal_id.id,
			}
		}