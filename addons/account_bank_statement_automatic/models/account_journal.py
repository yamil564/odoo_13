from odoo import fields,models,api
import logging
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
	_inherit = "account.journal"

	periodo_registro = fields.Selection(selection='_criterios_periodo',
		string="Periodo de conciliación",default='Manual')


	inicio_semana=fields.Selection(selection=[
			('0','Domingo'),
			('1','Lunes'),
			('2','Martes'),
			('3','Miércoles'),
			('4','Jueves'),
			('5','Viernes'),
			('6','Sábado')
			] , string="Día de inicio de semana" , default='1')


	@api.model
	def _criterios_periodo(self): 
		criterios = [
			('Manual','Manual'),
			('Diario','Diario'),
			('Mensual','Mensual'),
			('Bimestral','Bimestral'),
			('Trimestral','Trimestral'),
			('Semestral','Semestral'),
			('Anual','Anual')
			]
		return criterios

	@api.model
	def _dia_inicio_semana(self): 
		inicio = [
			(0,'Domingo'),
			(1,'Lunes'),
			(2,'Martes'),
			(3,'Miércoles'),
			(4,'Jueves'),
			(5,'Viernes'),
			(6,'Sábado')
			]
		return inicio
