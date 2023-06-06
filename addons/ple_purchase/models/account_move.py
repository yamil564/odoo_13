# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError

class AccountMove(models.Model):
	_inherit = 'account.move'

	declared_ple_8_1_8_2 = fields.Boolean(string="Registro declarado en PLE 8.1 y 8.2",
		copy=False)
	### CAMPO PARA EVITAR QUE LAS FACTURAS O BOLETAS DECLARADAS EN EL PLE SEAN ELIMINADAS