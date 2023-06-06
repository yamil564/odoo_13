# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    period_id = fields.Many2one('account.period', string='Periodo', required=False, states={'posted':[('readonly',True)]})

    #Buscar el Periodo contable
    def find_period(self, in_date, in_company):
        s_args = [
            ('date_start', '<=', in_date),
            ('date_stop', '>=', in_date),
            ('company_id', '=', in_company),
        ]
        date_period = self.env['account.period'].search(s_args)
        return date_period

    #Validar al de elegir la fecha de proceso contable
    @api.onchange('date')
    def _onchange_date(self):
        for rec in self:
            if rec.date:
                period = rec.find_period(rec.date, rec.company_id.id)
                if period:
                    if period[0].state == 'draft':
                        rec.period_id = period[0].id
                    else:
                        raise UserError(_('La Fecha seleccionada tiene PERIODO CONTABLE con estado \'Cerrado\'.'))
                else:
                    raise UserError(_('La Fecha seleccionada NO TIENE PERIODO CONTABLE.\n Por favor, validar.'))

    #Registra en el move la fecha de proceso contable y el periodo si esta se grabase en nulo
    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.env.user.company_id.id)
        date = vals.get('date', False)
        period_id = vals.get('period_id', False)
        if date and not period_id:
            periods = self.find_period(date, company_id)
            if periods:
                vals.update({'date': date, 
                    'period_id': periods[0].id})

        return super(AccountMove, self).create(vals)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    period_id = fields.Many2one('account.period', string='Periodo', related='move_id.period_id',required=False, index=True,store=True)

