# -*- encoding: utf-8 -*-
from odoo import api, fields, models, tools, _


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        currency_rates = (from_currency + to_currency)._get_rates(company, date)
        if self.env.context.get('default_pen_rate'):
            res = currency_rates.get(company.currency_id.id) / (1/self.env.context.get('default_pen_rate'))
        else:
            res = currency_rates.get(to_currency.id) / currency_rates.get(from_currency.id)
        return res