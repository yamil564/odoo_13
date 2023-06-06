# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo.exceptions import UserError,ValidationError
from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tdc
import re
import logging
import ast
import json
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = "account.journal"
    tipo_envio = fields.Selection(selection=[("0","0 - Pruebas"),("1","1 - Producción")],default="0")
    send_async = fields.Boolean("Envío asíncrono",default=False)
    electronic_invoice = fields.Boolean("Documento de emisión electrónica",default=False)

    invoice_type_code_id=fields.Selection(
        string="Tipo de Documento",
        selection="_selection_invoice_type")

    def _selection_invoice_type(self):
        return tdc
    
    tipo_comprobante_a_rectificar = fields.Selection(selection=[("00","Otros"),("01","Factura"),("03","Boleta"),("91","Comprobante de No Domiciliado")])

    @api.onchange("invoice_type_code_id","tipo_envio","code")
    def onchange_name(self):
        name = ""
        d = {"01":"Factura de venta","03":"Boleta de venta","07":"Nota de crédito","08":"Nota de débito","09":"Guía de Remisión"}
        if self.invoice_type_code_id in ["01","03","07","08","09"] and self.electronic_invoice:
            self.name = "{} {}{}".format(d[self.invoice_type_code_id],self.code or "*"," [test]" if self.tipo_envio == "0" else "")
        
    @api.constrains("code")
    def constrains_code(self):
        for record in self:
            if record.electronic_invoice and record.type == "sale":
                if record.code and record.invoice_type_code_id in ["07","08"]:
                    if re.match("^B\w{3}$", record.code) and record.tipo_comprobante_a_rectificar == "03":
                        return 
                    if re.match("^F\w{3}$", record.code) and record.tipo_comprobante_a_rectificar == "01":
                        return 
                    raise ValidationError("Error: El campo 'Serie' o 'Comprobante a rectificar' son incorrectos.")
                
                if re.match("^B\w{3}$", record.code) and record.invoice_type_code_id == "03":
                    return
                if re.match("^F\w{3}$", record.code) and record.invoice_type_code_id == "01":
                    return
                
                if re.match("^T\w{3}$", record.code) and record.invoice_type_code_id == "09":
                    return
                
                raise ValidationError("Error: El campo 'Serie' o el 'Tipo de comprobante' son incorrectos. ")

    @api.model
    def default_get(self,fields):
        res = super(AccountJournal, self).default_get(fields)
        res.update({"refund_sequence":False})
        return res
    
    
    @api.model
    def create(self, values):
        result = super(AccountJournal, self).create(values)
        code = values.get("code",False)
        if code:
            values["code"] = values.get("code").upper()

        return result
    

    @api.model
    def _get_sequence_prefix(self, code, refund=False):
        prefix = code.upper()
        if refund and self.electronic_invoice:
            prefix=prefix[0]+'R'+prefix[2:]
        elif refund:
            prefix="R"+prefix
        return prefix + '-'
         
    @api.model
    def _create_sequence(self, vals, refund=False):
        """ Create new no_gap entry sequence for every new Journal"""
        prefix = self._get_sequence_prefix(vals['code'], refund)
        seq_name = refund and vals['code'] + _(': Refund') or vals['code']
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 8,
            'number_increment': 1,
            'use_date_range': False,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)


    def action_create_new(self):
        res = super(AccountJournal,self).action_create_new()
        context = res.get("context",{})
        if self.type in ["sale","purchase"]:
            context.update({"default_journal_type":self.type,"default_invoice_type_code":self.invoice_type_code_id})
        
        res.update({"context":context})

        return res