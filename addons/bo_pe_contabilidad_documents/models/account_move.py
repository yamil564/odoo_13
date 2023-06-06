from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning, RedirectWarning
import re
import logging

from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tdc


_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"


    prefix_code=fields.Char(string="Serie del Comprobante")
    invoice_number=fields.Char(string="Correlativo del Comprobante")

    inv_supplier_ref = fields.Char(default="-")

    type_document_id = fields.Selection(string="Tipo de Documento",selection="_selection_invoice_type",
        compute="compute_campo_type_document_id",store=True)
    ### EL TIPO DOC EN ASIENTOWS VIENE DADO bPOR EL TD DEL DIARIO USADO
    exist_in_invoice_document = fields.Boolean(string="Existen Comprobantes Registrados",compute="compute_campo_exist_in_invoice_document",store=True)
    
    #exist_invoice_move_ids = fields.Many2many('account.move','exist_account_move_rel','move_id_1','move_id_2',
    #    string="Comprobante Registrado existente",
    #    compute="compute_campo_exist_in_invoice_document",store=True)

    def get_exist_invoice_documents(self):
        for rec in self:

            if rec and rec.company_id and rec.prefix_code and rec.invoice_number and rec.type and \
                rec.type in ('in_invoice','in_refund') and rec.partner_id and rec.type_document_id:
                
                query = """select id from
                    account_move 
                    where 
                    type in ('in_invoice','in_refund') and 
                    prefix_code='%s' and 
                    invoice_number='%s' and 
                    type_document_id = '%s' and 
                    partner_id = %s and 
                    company_id = %s 
                    """ % (rec.prefix_code or '',
                        rec.invoice_number or '',
                        rec.type_document_id or False,
                        str(rec.partner_id.id),
                        rec.company_id.id
                        )

                self.env.cr.execute(query)
                records = self.env.cr.dictfetchall()

                if records:
                    #move_id_id = records[0]['id']
                    move_id_id = [i['id'] for i in records if i['id'] != rec.id]

                    return move_id_id



    @api.depends('prefix_code','invoice_number','partner_id','type','type_document_id')
    def compute_campo_exist_in_invoice_document(self):
        for rec in self:
            rec.exist_in_invoice_document = False
            #rec.exist_invoice_move_id = False

            if rec and rec.prefix_code and rec.invoice_number and rec.type and rec.type in ('in_invoice','in_refund') and rec.partner_id and rec.type_document_id:
                query = """select id from
                    account_move 
                    where 
                    type in ('in_invoice','in_refund') and 
                    prefix_code='%s' and 
                    invoice_number='%s' and 
                    type_document_id = '%s' and 
                    partner_id = %s and
                    company_id = %s 
                    """ % (rec.prefix_code or '',
                        rec.invoice_number or '',
                        rec.type_document_id or False,
                        str(rec.partner_id.id),
                        rec.company_id.id 
                        )

                self.env.cr.execute(query)
                records = self.env.cr.dictfetchall()

                if records:
                    #move_id_id = records[0]['id']
                    move_id_id = [i['id'] for i in records if i['id'] != rec.id]

                    if move_id_id:
                        rec.exist_in_invoice_document = True
                        #rec.exist_invoice_move_ids = move_id_id



    def open_exist_document_in_invoice(self):
        if self.exist_in_invoice_document:
            move_ids = self.get_exist_invoice_documents()

            diccionario = {
                    'name': 'Documentos existentes',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.move',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', move_ids or [])]
                }
            return diccionario



    def _selection_invoice_type(self):
        tdc_ext = tdc
        flag = False
        for l in tdc_ext:
            if l[0] == "100":
                flag = True
        if not flag:
            tdc_ext.append(("100", "Notas de Venta"))
        return tdc_ext


    @api.depends('journal_id')
    def compute_campo_type_document_id(self):
        for rec in self:
            rec.type_document_id = False
            if rec.journal_id and rec.journal_id.invoice_type_code_id:
                rec.type_document_id = rec.journal_id.invoice_type_code_id


    ###################################################################
    @api.onchange('date','invoice_date','currency_id')
    def _onchange_currency(self):
        super(AccountMove,self)._onchange_currency()
        if self.type in ['in_invoice','in_refund']:

            if not self.currency_id:
                return
            if self.is_invoice(include_receipts=True):

                company_currency = self.company_id.currency_id
                has_foreign_currency = self.currency_id and self.currency_id != company_currency

                for line in self._get_lines_onchange_currency():
                    new_currency = has_foreign_currency and self.currency_id
                    line.currency_id = new_currency
                    line._onchange_currency()
            else:
                self.line_ids._onchange_currency()

            self._recompute_dynamic_lines(recompute_tax_base_amount=True)
    ######################################################################
    

    def _validate_inv_supplier_ref(self):
        if not self.inv_supplier_ref:
            raise UserError("Debe colocar el número de comprobante.")



    def post(self):

        for rec in self:
            if not rec.inv_supplier_ref:
                rec.inv_supplier_ref = '-'


        for rec in self:
            for line in rec.line_ids:
                if not line.prefix_code:
                    line.write({'prefix_code':rec.prefix_code or ''})

        for rec in self:
            for line in rec.line_ids:
                if not line.invoice_number:
                    line.write({'invoice_number':rec.invoice_number or ''})

        for rec in self:
            for line in rec.line_ids:
                if not line.type_document_id:
                    line.write({'type_document_id':rec.type_document_id or False})

            
        super(AccountMove,self).post()

    ##################################################

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountMove,self)._onchange_partner_id()

        self = self.with_context(force_company=self.journal_id.company_id.id)

        warning = {}
        rec_account = ''
        if self.partner_id:
            if self.currency_id and self.currency_id != self.company_id.currency_id:
                if self.journal_id.invoice_type_code_id=='02':
                    pay_account = self.partner_id.property_account_payable_me_fees_id    
                else:
                    rec_account = self.partner_id.property_account_receivable_me_id
                    pay_account = self.partner_id.property_account_payable_me_id
            else:
                if self.journal_id.invoice_type_code_id=='02':
                    pay_account = self.partner_id.property_account_payable_fees_id
                else:
                    rec_account = self.partner_id.property_account_receivable_id
                    pay_account = self.partner_id.property_account_payable_id
            
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            p = self.partner_id
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                }
                if p.invoice_warn == 'block':
                    self.partner_id = False
                    return {'warning': warning}

        if self.is_sale_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_payment_term_id or self.invoice_payment_term_id
            ###################################
            if self.currency_id and self.currency_id != self.company_id.currency_id:
                new_term_account = self.partner_id.commercial_partner_id.property_account_receivable_me_id
            else:
                new_term_account = self.partner_id.commercial_partner_id.property_account_receivable_id
            #######################################
            #new_term_account = self.partner_id.commercial_partner_id.property_account_receivable_id
            self.narration = self.company_id.with_context(lang=self.partner_id.lang).invoice_terms
        elif self.is_purchase_document(include_receipts=True) and self.partner_id:
            self.invoice_payment_term_id = self.partner_id.property_supplier_payment_term_id or self.invoice_payment_term_id
            #######################################
            if self.currency_id and self.currency_id != self.company_id.currency_id:
                if self.journal_id.invoice_type_code_id=='02':
                    new_term_account = self.partner_id.commercial_partner_id.property_account_payable_me_fees_id
                else:
                    new_term_account = self.partner_id.commercial_partner_id.property_account_payable_me_id
            else:
                if self.journal_id.invoice_type_code_id=='02':
                    new_term_account = self.partner_id.commercial_partner_id.property_account_payable_fees_id
                else:
                    new_term_account = self.partner_id.commercial_partner_id.property_account_payable_id
            ############################################
            #new_term_account = self.partner_id.commercial_partner_id.property_account_payable_id
        else:
            new_term_account = None

        for line in self.line_ids:
            line.partner_id = self.partner_id.commercial_partner_id

            if new_term_account and line.account_id.user_type_id.type in ('receivable', 'payable'):
                line.account_id = new_term_account

        self._compute_bank_partner_id()
        self.invoice_partner_bank_id = self.bank_partner_id.bank_ids and self.bank_partner_id.bank_ids[0]

        # Find the new fiscal position.
        delivery_partner_id = self._get_invoice_delivery_partner_id()
        new_fiscal_position_id = self.env['account.fiscal.position'].with_context(force_company=self.company_id.id).get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)
        self.fiscal_position_id = self.env['account.fiscal.position'].browse(new_fiscal_position_id)
        self._recompute_dynamic_lines()
        if warning:
            return {'warning': warning}


    @api.onchange('journal_id','currency_id')
    def _onchange_journal_id_currency_id(self):
        self._onchange_partner_id()

#####################################################################3
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"



#################################
    ### SE TOMA EL TC A FECHA EMISION COMPROBANTE
    def _recompute_debit_credit_from_amount_currency(self):
        super(AccountMoveLine,self)._recompute_debit_credit_from_amount_currency()
        _logger.info('\n\nENTRE RECOMPUTE AHORA\n\n')
        for line in self:
            if line.move_id.type in ['in_invoice','in_refund']:
            # Recompute the debit/credit based on amount_currency/currency_id and date.
                company_currency = line.account_id.company_id.currency_id
                balance = line.amount_currency
                if line.currency_id and company_currency and line.currency_id != company_currency:
                    _logger.info('\n\nENTRE IF RECOMPUTE\n\n')

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
    ##########################################################

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        
        ret=super(AccountMoveLine,self)._get_fields_onchange_subtotal()
        
        if self.move_id.type in ['in_invoice','in_refund']:

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
    ##########################################################