
import pytz
import calendar
import base64
from io import BytesIO, StringIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta
from odoo.addons import ple_base as tools

import logging
_logger=logging.getLogger(__name__)
class PleDiaryAccountingPlanLine(models.Model):
	_name='ple.diary.accounting.plan.line'

	ple_diary_accounting_plan_id=fields.Many2one("ple.diary.accounting.plan",string="id PLE", ondelete="cascade" )
	
	
	account_id=fields.Many2one('account.account', string="Código de Cuenta Contable", readonly=True)
	
	codigo_cuenta_desagregado=fields.Char(string="Código cuenta contable desagregado" , required=True )
	descripcion_cuenta_contable=fields.Char(string="Descripción Cuenta Contable"  , required=True )
	codigo_plan_contable=fields.Char(string="Código Plan de Cuentas Deudor" , default="01" , size=2)
	descripcion_plan_contable_deudor=fields.Char(string="Descripción plan cuentas Deudor" ,  default="" )
	codigo_cuenta_contable_corporativa=fields.Char(string="Código Cuenta Contable Corporativa", default="")
	descripcion_cuenta_contable_corporativa=fields.Char(string="Descripción Cuenta Contable corporativa", default="")
	indicador_estado_operacion=fields.Char(string="Indicador Estado Operación" , default="1" , size=1 , required=True)




	