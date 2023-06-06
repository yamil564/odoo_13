# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re
import logging
import requests
import json

_logger = logging.getLogger(__name__)

patron_dni = re.compile("\d{8}$")
patron_ruc = re.compile("[12]\d{10}$")


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    prefix_code_contingencia_id = fields.Many2one('account.journal',
        string="Serie de Contingencia")
    invoice_number_contingencia = fields.Char(string="Número de Documento Contingencia")

    is_contingencia=fields.Boolean(string="Es Contingencia",default=False)
    #######################################################################
    sale_order_enable_ids = fields.Many2many('account.journal',string="Series Permitidas")

    ################################################
    def get_sale_order_enable_ids(self,type_document=False):
        
        self.sale_order_enable_ids = False
        if self.is_contingencia:
            warehouse_id = self.warehouse_id
            if warehouse_id:
                journals = self.env["stock.warehouse"].browse(warehouse_id.id).journal_ids.filtered(
                    lambda r: r.invoice_type_code_id == type_document and r.type == "sale" and r.is_contingencia)

                self.sale_order_enable_ids = journals or False
    #####################################################################################


    def action_view_invoice(self):
        ret = super(SaleOrder,self).action_view_invoice()
        
        if ret['context'] and self.prefix_code_contingencia_id and self.invoice_number_contingencia:
            ret['context']['default_journal_id'] = self.prefix_code_contingencia_id.id or False
            ret['context']['default_name'] = "%s-%s"%(self.prefix_code_contingencia_id.code or '',self.invoice_number_contingencia)
            ret['context']['default_is_contingencia'] = True 
            ret['context']['default_name_contingencia'] = "%s-%s"%(self.prefix_code_contingencia_id.code or '',self.invoice_number_contingencia)
        
        return ret
    
    ###################################################
    def emitir_factura_contingencia(self):
        self.ensure_one()
        if not(self.partner_invoice_id.l10n_latam_identification_type_id.l10n_pe_vat_code == "6" and patron_ruc.match(self.partner_invoice_id.vat or "")):
            raise UserError(
                "Para emitir una Factura entonces la dirección de Facturación debe tener el tipo de documento como RUC y su valor debe ser válido")

        if len(self.invoice_ids) == 0:
            self.get_sale_order_enable_ids("01")
            _logger.info('\n\nLISTA DOMAIN\n\n')
            _logger.info(self.sale_order_enable_ids)
            return self.open_wizard_contingencia("01")


    def emitir_boleta_contingencia(self):
        self.ensure_one()
        if not(self.partner_invoice_id.l10n_latam_identification_type_id.l10n_pe_vat_code in ["0", "1", "4"]):
            raise UserError(
                "Para Emitir una Boleta la dirección de Facturación debe tener alguno de estos tipo de documentos 'DNI', 'DOC.TRIB.NO.DOM.SIN.RUC', 'Carnet de Extranjería' y su valor debe ser válido.")

        if self.partner_invoice_id.l10n_latam_identification_type_id.l10n_pe_vat_code == "0":
            if not patron_dni.match(self.partner_invoice_id.vat or ""):
                raise UserError("El número de dni del cliente es erróneo")

        if len(self.invoice_ids) == 0:
            self.get_sale_order_enable_ids("03")
            _logger.info('\n\nLISTA DOMAIN\n\n')
            _logger.info(self.sale_order_enable_ids)
            return self.open_wizard_contingencia("03")


    def open_wizard_contingencia(self,type_document=False):
        return {
            'name': "Número de Serie-Documento en Documentos Contingencia",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'wizard.sale.order.contingencia',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_type_document': type_document,
                'default_sale_order_id' : self.id,
                'default_sale_order_enable_ids':self.sale_order_enable_ids.ids}}


    #######################################################################


    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()

        if self.is_contingencia and self.prefix_code_contingencia_id and self.invoice_number_contingencia:
            
            paymentterm_lines = []
            for pl in self.paymentterm_line:
                paymentterm_lines.append(self.env['paymentterm.line'].create(
                    {'currency_id': pl.currency_id, 'date_due': pl.date_due, 'amount': pl.amount}).id)

            res.update({
                "invoice_type_code": self.tipo_documento,
                "descuento_global": self.descuento_global,
                "apply_global_discount": True if self.descuento_global > 0 else False,
                "apply_same_discount_on_all_lines": self.apply_same_discount_on_all_lines,
                "discount_on_all_lines": self.discount_on_all_lines,
                "paymentterm_line": [(6, 0, paymentterm_lines)],
            })

            warehouse_id = self.warehouse_id
            if warehouse_id:
                res["warehouse_id"] = warehouse_id.id
                res["journal_id"] = self.prefix_code_contingencia_id.id
                res['name'] = "%s-%s"%(self.prefix_code_contingencia_id.code or '',self.invoice_number_contingencia)

            else:
                raise UserError(
                    "Su usuario no tiene almacenes disponibles. Contacte con su administrador.")

            return res

        else:

            paymentterm_lines = []
            for pl in self.paymentterm_line:
                paymentterm_lines.append(self.env['paymentterm.line'].create(
                    {'currency_id': pl.currency_id, 'date_due': pl.date_due, 'amount': pl.amount}).id)

            res.update({
                "invoice_type_code": self.tipo_documento,
                "descuento_global": self.descuento_global,
                "apply_global_discount": True if self.descuento_global > 0 else False,
                "apply_same_discount_on_all_lines": self.apply_same_discount_on_all_lines,
                "discount_on_all_lines": self.discount_on_all_lines,
                "paymentterm_line": [(6, 0, paymentterm_lines)],
            })

            warehouse_id = self.warehouse_id
            if warehouse_id:
                res["warehouse_id"] = warehouse_id.id
                journals = self.env["stock.warehouse"].browse(warehouse_id.id).journal_ids.filtered(
                    lambda r: r.invoice_type_code_id == self.tipo_documento and r.type == "sale" and not r.is_contingencia)
                if len(journals) > 0:
                    res["journal_id"] = journals[0].id
                else:
                    raise UserError(
                        "Debe configurar Diarios disponibles en sus almacénes. Contacte con su administrador.")
            else:
                raise UserError(
                    "Su usuario no tiene almacenes disponibles. Contacte con su administrador.")

            return res

