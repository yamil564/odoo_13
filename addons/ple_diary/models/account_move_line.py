# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	declared_ple_5_1_5_2_6_1 = fields.Boolean(string="Registro declarado en 5.1,5.2 y 6.1" , copy=False)
	### CAMPO PARA EVITAR QUE LAS FACTURAS O BOLETAS DECLARADAS EN EL PLE SEAN ELIMINADAS