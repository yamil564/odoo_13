# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountPeriod(models.Model):
    _name = "account.period"
    _description = "Periodo contable"
    _order = "date_start, special desc"

    name = fields.Char(string='Nombre del Periodo', required=True)
    code = fields.Char(string='Codigo', size=12)
    special = fields.Boolean(string='Periodo de Apertura/Cierre', help="Estos periodos pueden superponerse.")
    date_start = fields.Date(string='Fecha inicial', help="Fecha inicial del Periodo Contable.", 
        required=True, states={'done': [('readonly', True)]})
    date_stop = fields.Date(string='Fecha final', help="Fecha final del Periodo Contable.",
        required=True, states={'done': [('readonly', True)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Año Fiscal', 
        required=True, states={'done': [('readonly', True)]}, index=True , ondelete="cascade")
    state = fields.Selection([('draft', 'Abierto'), ('done', 'Cerrado')], string='Estado', readonly=True, copy=False, default='draft', 
        help='Cuando se crean periodos mensuales el estado es \'Abierto\'. Al final del periodo mensual el estado es \'Cerrado\'.')
    company_id = fields.Many2one('res.company', related='fiscalyear_id.company_id', string='Empresa', store=True, readonly=True)
    maximum_tax_date = fields.Date(string='Fecha final Tributaria', states={'done': [('readonly', True)]}, 
        help="Indicar la Fecha final tributaria para ser considerado dentro del Periodo Contable.")

    #Cerrar Periodo
    def action_close_period(self):
        for rec in self:
            rec.state = "done"

    #Reabrir Periodo
    def action_open_period(self):
        for rec in self:
            #Valida si el Año Fiscal esta cerrado
            if (rec.fiscalyear_id and rec.fiscalyear_id.state == 'done'):
                raise UserError(_('No se puede \'REABRIR\' un PERIODO que pertenece\n a un AÑO FISCAL \'CERRADO\'.'))
            rec.state = "draft"
