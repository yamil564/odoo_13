# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class account_fiscalyear(models.Model):
    _name = "account.fiscalyear"
    _description = "Año Fiscal"
    _order = "date_start, id"

    name = fields.Char(string='Año Fiscal', required=True)
    code = fields.Char(string='Codigo', size=6, required=True)
    company_id = fields.Many2one('res.company', string='Empresa', required=True, default=lambda self: self.env.user.company_id)
    date_start = fields.Date(string='Fecha inicial', required=True)
    date_stop = fields.Date(string='Fecha final', required=True)
    period_ids = fields.One2many('account.period', 'fiscalyear_id', 'Periodos')
    state = fields.Selection([('draft', 'Abierto'), ('done', 'Cerrado')], string='Estado', readonly=True, copy=False, default='draft')

    
    def create_period3(self):
        self.interval = 3
        return self.create_period()

    
    def create_period(self):
        if not hasattr(self,'interval'):
            self.interval = 1
        period_obj = self.env['account.period']
        for fy in self.browse(self.ids):
            ds = fy.date_start
            period_obj.create({
                    'name':  "%s %s" % (_('Periodo de Apertura'), ds.strftime('%Y')),
                    'code': ds.strftime('00/%Y'),
                    'date_start': ds,
                    'date_stop': ds,
                    'special': True,
                    'fiscalyear_id': fy.id,
                })
            while ds.strftime('%Y-%m-%d') < fy.date_stop.strftime('%Y-%m-%d'):
                de = ds + relativedelta(months=self.interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop.strftime('%Y-%m-%d'):
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')

                period_obj.create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=self.interval)

            #############################
            d_closure = fy.date_stop
            period_obj.create({
                    'name':  "%s %s" % (_('Periodo de Cierre'), d_closure.strftime('%Y')),
                    'code': d_closure.strftime('13/%Y'),
                    'date_start': d_closure,
                    'date_stop': d_closure,
                    'special': True,
                    'fiscalyear_id': fy.id,
                })

        return True

    #Cerrar Año Fiscal
    def action_close_fy(self):
        for rec in self:
            if rec.period_ids:
                for a_period in rec.period_ids:
                    if a_period.state == 'draft':
                        a_period.state = 'done'

            rec.state = "done"

    #Validar fecha de inicio y fin
    
    @api.constrains('date_start', 'date_stop')
    def _check_estimated_times(self):
        if (self.date_start and self.date_stop and self.date_start > self.date_stop):
            raise ValidationError(
                _('La fecha final no puede ser menor a la fecha inicial.'))
