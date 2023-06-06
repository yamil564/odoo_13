# -*- coding: utf-8 -*-
# Copyright 2017 Jarvis (www.odoomod.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo
from odoo import api, models, _, fields, osv
from odoo.osv import expression
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import os


class AccountPeriod(models.Model):
    _name = "account.period"
    _description = "Account period"
    _order = "date_start, special desc"

    name = fields.Char('Period Name', required=True)
    code = fields.Char('Code', size=12)
    special = fields.Boolean('Opening/Closing Period',
                             help="These periods can overlap.")
    date_start = fields.Date('Start of Period', required=True, states={
                             'done': [('readonly', True)]})
    date_stop = fields.Date('End of Period', required=True, states={
                            'done': [('readonly', True)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Fiscal Year', required=True,
                                    states={'done': [('readonly', True)]}, index=True)
    state = fields.Selection([('draft', 'Open'), ('done', 'Closed')], 'Status', readonly=True, copy=False,
                             default='draft',
                             help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.')
    company_id = fields.Many2one('res.company', related='fiscalyear_id.company_id', string='Company', store=True,
                                 readonly=True)


class invoice_period(models.Model):
    _inherit = "account.move"

    period_id = fields.Many2one('account.period', string='Periodo')
    estado = fields.Char(default='1')

    def action_invoice_open(self):
        obj = False
        if(self.invoice_date):
            self.forzar_periodo()
            self.forzar_estado()
            obj = super(invoice_period, self).action_invoice_open()
            self.forzar_periodo_moveline()
            # self.copiar_moneda()
        else:
            raise UserError("La Fecha de la factura es obligatoria")
        return obj


    def copiar_moneda(self):
        for line in self.move_id.line_ids:
            line.currency_id = self.currency_id

    def forzar_estado_moveline(self, estadolinea):
        for line in self.move_id.line_ids:
            line.estado = estadolinea

    @api.onchange('period_id')
    def forzar_estado(self):
        if self.invoice_date and self.period_id:
            fecha = str(self.invoice_date)
            fecha_anio = int(fecha[0:4])
            fecha_mes = int(fecha[5:7])

            periodo = str(self.period_id.code)
            periodo_anio = int(periodo[3:7])
            periodo_mes = int(periodo[0:2])

            dif_anio = periodo_anio-fecha_anio
            dif_mes = periodo_mes-fecha_mes
            dif = dif_anio*12+dif_mes

            if dif < 0:
                raise UserError("Periodo no puede ser menor a la fecha")
            if self.type == "out_invoice":  # venta
                if dif == 0:
                    self.estado = '1'
                else:
                    self.estado = '8'
                    self.forzar_estado_moveline(8)

            if self.type == "in_invoice":  # compra
                if dif == 0:
                    self.estado = '1'
                elif dif < 13:
                    self.estado = '6'
                    self.forzar_estado_moveline(8)
                else:
                    self.estado = '7'
                    self.forzar_estado_moveline(8)


class moveline_period(models.Model):
    _inherit = "account.move.line"

    period_id = fields.Many2one('account.period', string='Periodo')
    estado = fields.Char(default='1')
