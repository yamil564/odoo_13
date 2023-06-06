# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError
from datetime import datetime, timedelta

class TemplateGeneralBalanceReport(models.Model):
	_name = 'template.general.balance.report'
	_description = "Plantilla de Configuración del Balance General"


	company_id = fields.Many2one('res.company',
		string="Compañia", 
		default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
		domain = lambda self: [('id', 'in',[i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids] )],readonly=True)

	name=fields.Char(string="Nombre",
		default="PLANTILLA DE CONFIGURACIÓN DEL BALANCE GENERAL")
	observations = fields.Char(string="Observaciones")


	#### Fecha hora
	fecha_hora = fields.Datetime(string="Fecha de Plantilla",default=datetime.now())

	###################### PLANTILLA DE CONFIGURACIÓN DE SUB-ELEMENTOS ######################

	template_activos_corrientes_line_ids = fields.One2many('template.activos.corrientes.line',
		'general_balance_report_id',string="Plantilla de Activos Corrientes",ondelete="cascade")

	template_activos_no_corrientes_line_ids = fields.One2many('template.activos.no.corrientes.line',
		'general_balance_report_id',string="Plantilla de Activos No Corrientes",ondelete="cascade")


	template_pasivos_corrientes_line_ids = fields.One2many('template.pasivos.corrientes.line',
		'general_balance_report_id',string="Plantilla de Pasivos Corrientes",ondelete="cascade")


	template_pasivos_no_corrientes_line_ids = fields.One2many('template.pasivos.no.corrientes.line',
		'general_balance_report_id',string="Plantilla de Pasivos No  Corrientes",ondelete="cascade")


	template_patrimonio_line_ids = fields.One2many('template.patrimonio.line',
		'general_balance_report_id',string="Plantilla de Patrimonio",ondelete="cascade")