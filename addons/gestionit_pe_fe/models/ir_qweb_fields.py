from odoo import models,api,fields,_
import logging
_logger = logging.getLogger(__name__)

class MonetaryConverter(models.AbstractModel):
    _inherit = 'ir.qweb.field.monetary'

    @api.model
    def get_available_options(self):
        options = super(MonetaryConverter, self).get_available_options()
        options.update(decimal_places=dict(type='integer',string='Decimales'))
        return options

    @api.model
    def value_to_html(self, value, options):
        display_currency = options['display_currency']
        # _logger.info(options)
        decimal_places = options.get('decimal_places',-1)

        if not isinstance(value, (int, float)):
            raise ValueError(_("The value send to monetary field is not a number."))

        # lang.format mandates a sprintf-style format. These formats are non-
        # minimal (they have a default fixed precision instead), and
        # lang.format will not set one by default. currency.round will not
        # provide one either. So we need to generate a precision value
        # (integer > 0) from the currency's rounding (a float generally < 1.0).
        fmt = "%.{0}f".format(display_currency.decimal_places)

        # _logger.info(decimal_places)
        if decimal_places >= 0:
            fmt = "%.{0}f".format(int(decimal_places))

        if options.get('from_currency'):
            date = options.get('date') or fields.Date.today()
            company_id = options.get('company_id')
            if company_id:
                company = self.env['res.company'].browse(company_id)
            else:
                company = self.env.company
            value = options['from_currency']._convert(value, display_currency, company, date)

        lang = self.user_lang()
        formatted_amount = lang.format(fmt, display_currency.round(value),
                                grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

        pre = post = u''
        if display_currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=display_currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=display_currency.symbol or '')

        return u'{pre}<span class="oe_currency_value">{0}</span>{post}'.format(formatted_amount, pre=pre, post=post)
