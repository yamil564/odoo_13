# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
from . import arrays_general_balance_report as agbr


class TemplatePatrimonioLine(models.Model):
	_name = 'template.patrimonio.line'
	_description = "Plantilla de Configuración de Patrimonio"

	general_balance_report_id = fields.Many2one("template.general.balance.report", string="Plantilla de Configuración de Balance General",readonly=True)
	
	name=fields.Char(string="Nombre del Rubro",required=True)

	calculation_type = fields.Selection(selection=[('accounts','Por Grupo de Cuentas Asociadas'),('variation','Cuadre'),('manual','Manual')],
		string="Tipo de Cálculo",default='accounts',required=True)

	account_ids=fields.Many2many('account.account',string="Cuentas Asociadas al Rubro")
	movements_period = fields.Float(string="Movimientos del Ejercicio o Periodo")

	################### CAMPOS DE AGRUPACIÓN DE INFORME #################
	grupo_informe = fields.Selection(selection=agbr.array_report_groups,default='pasivo_patrimonio')
	grupo_elemento = fields.Selection(selection=agbr.array_element_groups,default='patrimonio')
	sub_grupo_elemento = fields.Selection(selection=agbr.array_element_sub_groups,default='patrimonio')