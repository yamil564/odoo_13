# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
#_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_special_tc = fields.Boolean(string='Activar Tipo Cambio Manual', help='Activar el Tipo de Cambio personalizado por el usuario')
    currency_tc = fields.Float(string='Tipo de Cambio',digits=(1, 4), default=1.0)
    #is_invoice_in_me  CAMPO EXISTENTE EN GESTIONIT_PE_FE


    @api.onchange('invoice_date','date','currency_id','partner_id')
    def get_currency_tc(self):
        for rec in self:
            
            v_rate = 1

            if rec.currency_id and rec.currency_id != rec.company_id.currency_id:

                pay_date = datetime.now(tz=timezone("America/Lima")) if not rec.date else rec.date

                currency_company = self.env.company.currency_id
                rate = currency_company._convert(1, rec.currency_id , self.env.company, pay_date, round=False)

                v_rate = round(1/(rate if rate > 0 else 1), 4)

            rec.currency_tc = v_rate

    ##########################################################################
    @api.onchange('date','invoice_date','currency_id')
    def _onchange_currency(self):
        for rec in self:
            if not rec.is_special_tc:
                super(AccountMove,self)._onchange_currency()

    ##########################################################################

    @api.onchange('is_special_tc','currency_id','invoice_date','date')
    def onchange_is_special_tc(self):        
        for rec in self:
            if not rec.is_special_tc:
                for line in rec.line_ids:
                    line._onchange_currency()

    @api.onchange('currency_tc')
    def onchange_currency_tc(self):
        for rec in self:
            for line in rec.line_ids:
                #_logger.info('\n\nENTRE : onchange_currency_tc\n\n')
                line._recompute_debit_credit_from_amount_currency()

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        for rec in self:
            for line in rec.line_ids:
                #_logger.info('\n\nENTRE : onchange_currency_id\n\n')
                line._onchange_currency()


    @api.constrains('is_special_tc')
    def contrains_not_zero(self):
        for rec in self:
            if rec.is_special_tc:
                if rec.currency_tc <= 0.00:
                    raise ValidationError(_('El tipo de Cambio no puede ser menor o igual que 0'))



    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for move in self]
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'is_special_tc': True,
                'currency_tc': move.currency_tc,
            })
        reverse_moves = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        reverse_moves.onchange_currency_tc()
        return reverse_moves



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    currency_tc= fields.Float(related='move_id.currency_tc', string='Tipo de Cambio', digits=(1, 4), store=True)
    is_special_tc = fields.Boolean(string='Tipo Cambio Manual', help='Se usó Tipo de Cambio Manual por el usuario',related='move_id.is_special_tc')

    ##################################################################################
     ### SE TOMA EL TC A FECHA EMISION COMPROBANTE
    def _recompute_debit_credit_from_amount_currency(self):
        super(AccountMoveLine,self)._recompute_debit_credit_from_amount_currency()

        for line in self:

            if line.move_id.type in ['in_invoice','in_refund'] and not line.move_id.is_special_tc:
            # Recompute the debit/credit based on amount_currency/currency_id and date.
                company_currency = line.account_id.company_id.currency_id
                balance = line.amount_currency
                if line.currency_id and company_currency and line.currency_id != company_currency and not line.move_id.is_special_tc:
                    #_logger.info('\n\nENTRE IF RECOMPUTE\n\n')
                    #### Calculo de Date de Rate
                    date_rate = ''
                    if line.move_id.type == 'in_refund':
                        date_rate = line.move_id.reversed_entry_id.invoice_date or \
                            line.move_id.reversed_entry_id.date or fields.Date.today()
                    elif line.move_id.type == 'in_invoice':
                        date_rate = line.move_id.invoice_date or \
                            line.move_id.date or fields.Date.today()

                    #balance = line.currency_id._convert(balance, company_currency, line.account_id.company_id,
                    #    line.move_id.invoice_date or line.move_id.date or fields.Date.today())
                    balance = line.currency_id._convert(balance, company_currency, 
                        line.account_id.company_id, date_rate)

                    line.debit = balance > 0 and balance or 0.0
                    line.credit = balance < 0 and -balance or 0.0

            elif line.move_id.is_special_tc:
            # Recompute the debit/credit based on amount_currency/currency_id and date.
                company_currency = line.account_id.company_id.currency_id
                balance = line.amount_currency
                if line.currency_id and company_currency and line.currency_id != company_currency and line.move_id.is_special_tc:
                    #_logger.info('\n\nENTRE IF RECOMPUTE\n\n')
                    #### Calculo de Date de Rate
                    date_rate = ''
                    if line.move_id.type == 'in_refund':
                        date_rate = line.move_id.reversed_entry_id.invoice_date or \
                            line.move_id.reversed_entry_id.date or fields.Date.today()
                    elif line.move_id.type == 'in_invoice':
                        date_rate = line.move_id.invoice_date or \
                            line.move_id.date or fields.Date.today()
                    else:
                        date_rate = line.move_id.date or fields.Date.today()

                    #balance = line.currency_id._convert(balance, company_currency, line.account_id.company_id,
                    #    line.move_id.invoice_date or line.move_id.date or fields.Date.today())
                    balance = line.currency_id.with_context(default_pen_rate=line.currency_tc)._convert(balance, company_currency, 
                        line.account_id.company_id, date_rate)

                    line.debit = balance > 0 and balance or 0.0
                    line.credit = balance < 0 and -balance or 0.0
    #########################################################


    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        
        ret=super(AccountMoveLine,self)._get_fields_onchange_subtotal()
        
        if self.move_id.type in ['in_invoice','in_refund'] and self.currency_id != self.company_id.currency_id and not self.move_id.is_special_tc:

            if self.move_id.type in ['in_invoice']:
                return self._get_fields_onchange_subtotal_model(
                    price_subtotal=price_subtotal or self.price_subtotal,
                    move_type=move_type or self.move_id.type,
                    currency=currency or self.currency_id,
                    company=company or self.move_id.company_id,
                    date=date or self.move_id.invoice_date or self.move_id.date,
                )
            elif self.move_id.type in ['in_refund']:
                return self._get_fields_onchange_subtotal_model(
                    price_subtotal=price_subtotal or self.price_subtotal,
                    move_type=move_type or self.move_id.type,
                    currency=currency or self.currency_id,
                    company=company or self.move_id.company_id,
                    date=date or self.move_id.reversed_entry_id.invoice_date or self.move_id.invoice_date or self.move_id.date,
                )
        
        else:
            return ret