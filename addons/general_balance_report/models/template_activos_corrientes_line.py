# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
from . import arrays_general_balance_report as agbr


class TemplateActivosCorrientesLine(models.Model):
	_name = 'template.activos.corrientes.line'
	_description = "Plantilla de Configuración de Activos Corrientes"

	general_balance_report_id = fields.Many2one("template.general.balance.report", string="Plantilla de Configuración de Balance General",readonly=True)
	
	name=fields.Char(string="Nombre del Rubro",required=True)

	calculation_type = fields.Selection(selection=[('accounts','Por Grupo de Cuentas Asociadas'),('manual','Manual')],
		string="Tipo de Cálculo",default='accounts',required=True)

	account_ids=fields.Many2many('account.account',string="Cuentas Asociadas al Rubro")
	movements_period = fields.Float(string="Movimientos del Ejercicio o Periodo")

	################### CAMPOS DE AGRUPACIÓN DE INFORME #################
	grupo_informe = fields.Selection(selection=agbr.array_report_groups,default='activo')
	grupo_elemento = fields.Selection(selection=agbr.array_element_groups,default='activo')
	sub_grupo_elemento = fields.Selection(selection=agbr.array_element_sub_groups,default='activo_corriente')


