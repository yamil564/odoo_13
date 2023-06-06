import pytz
import calendar
import base64
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta
from . import arrays_general_balance_report as agbr


import logging
_logger=logging.getLogger(__name__)

class DorniersGeneralBalanceReportLine(models.Model):
	_name='dorniers.general.balance.report.line'

	dorniers_general_balance_report_id = fields.Many2one('dorniers.general.balance.report',
		string="Reporte de Estado Situación Financiera",ondelete="cascade",readonly=True)


	name = fields.Char(string="Nombre del Rubro",readonly=True)
	account_ids = fields.Many2many("account.account",
		string="Cuentas Asociadas al Rubro",readonly=True)
	
	grupo_informe = fields.Selection(selection=agbr.array_report_groups,readonly=True)
	grupo_elemento = fields.Selection(selection=agbr.array_element_groups,readonly=True)
	sub_grupo_elemento = fields.Selection(selection=agbr.array_element_sub_groups,readonly=True)

	saldo_rubro_contable = fields.Float(string="Saldo Rubro",readonly=True)

	######## campo flag para iden rubro variation ##
	is_variation = fields.Boolean(string="Es Rubro de Cuadre",default=False)


	def _convert_object_date(self, date):
		if date:
			return date.strftime('%d/%m/%Y')
		else:
			return ''