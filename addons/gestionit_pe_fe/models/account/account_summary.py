#!/usr/bin/env python2

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import datetime
import json
from . import oauth
import requests
from xml.dom.minidom import parse, parseString
import pytz
from pytz import timezone
import os
import time
from datetime import datetime, timedelta
import math
import re
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion import api_models
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion.controllers import main
from odoo.addons.gestionit_pe_fe.models.account.oauth import send_summary_xml
import logging
_logger = logging.getLogger(__name__)


class AccountSummaryLine(models.Model):
    _name = "account.summary.line"
    _description = "Líneas de resumen diario"

    account_summary_id = fields.Many2one(
        "account.summary", string="Resumen Diario", ondelete="set null")
    invoice_id = fields.Many2one("account.move")
    serie = fields.Char(string="Serie")
    correlativo = fields.Char(string="Correlativo")
    tipo_documento = fields.Selection(string="Tipo de Documento", selection=[(
        '03', "Boleta"), ("07", "Nota de Crédito"), ("08", "Nota de Débito")])
    tipo_doc_receptor = fields.Char(string="Tipo documento Receptor")
    numero_doc_receptor = fields.Char(string="Número documento receptor")
    tipo_moneda = fields.Char(string="Tipo de Moneda")

    numero_documento_inicio = fields.Char(string="Número de Documento Inicio")
    numero_documento_fin = fields.Char(string="Número de Documento Fin")

    codigo_afectacion_igv = fields.Char(string="Código de Afectación al IGV")
    monto_igv = fields.Float(string="Monto IGV", digits=(10, 2))
    monto_isc = fields.Float(string="Monto ISC", digits=(10, 2))
    # cod_operacion = fields.Char(string="Código Operación",default="1")

    cod_operacion = fields.Selection(string="Código Operación", selection=[
                                     ("1", "Adicionar"), ("2", "Modificar"), ("3", "Anular")])

    monto_total = fields.Float(string="Monto Total", digits=(10, 2))
    monto_neto = fields.Float(string="Monto Neto", digits=(10, 2))
    monto_exe = fields.Float(string="Monto Inafecto", digits=(10, 2))
    monto_exo = fields.Float(string="Monto Exonerado", digits=(10, 2))
    monto_exp = fields.Float(string="Monto Exportación", digits=(10, 2))
    monto_grat = fields.Float(string="Monto Gratuito", digits=(10, 2))
    monto_otros = fields.Float(string="Monto Otros", digits=(10, 2))
    tipo_doc_referencia = fields.Char(string="Tipo doc. referencia")
    num_doc_referencia = fields.Char(string="Número doc. referencia")


class AccountSummary(models.Model):
    _name = "account.summary"
    _rec_name = "identificador_resumen"
    _order = "create_date desc"
    _description = "Resumen diario"

    company_id = fields.Many2one("res.company", required=True, string="Compañia",
                                 default=lambda self: self.env.company.id)
    fecha_generacion = fields.Date("Fecha de Generación", default=lambda r:datetime.now(tz=timezone("America/Lima")), required="True")
    fecha_emision_documentos = fields.Date("Fecha de Emisión de Documentos", default=lambda r:datetime.now(tz=timezone("America/Lima")), required="True")
    identificador_resumen = fields.Char("Identificador de Resumen", default="Resumen Diario",related="current_log_status_id.name")
    summary_line_ids = fields.One2many("account.summary.line", "account_summary_id", string="Líneas de Resumen", ondelete='cascade')
    resumen_diario_json = fields.Text("Resumen Diario JSON")

    cod_operacion = fields.Selection(string="Código Operación", selection=[("1", "Adicionar"), ("2", "Modificar"), ("3", "Anular")], required="True", default="1")
        
    account_invoice_ids = fields.One2many("account.move", "account_summary_id", string="Comprobantes")
    
    ticket = fields.Char("Ticket")
    summary_ticket = fields.Char("Ticket", related="current_log_status_id.summary_ticket")

    summary_description_response = fields.Char(related="current_log_status_id.summary_description_response")
    summary_code_response = fields.Char(related="current_log_status_id.summary_code_response")
    # estado = fields.Selection(selection=[("borrador", "Borrador"),
    #                                      ("enviado", "Enviado"),
    #                                      ("resumen_valido", "Resumen Valido"),
    #                                      ("resumen_rechazado", "Resumen Rechazado")], default="borrador")

    estado_emision = fields.Selection([
        ('B', 'Borrador'),
        ('A', 'Aceptado'),
        ('E', 'Enviado a SUNAT'),
        ('N', 'Envio Erroneo'),
        ('O', 'Aceptado con Observacion'),
        ('R', 'Rechazado'),
        ('P', 'Pendiente de envio a SUNAT'),
    ], string="Estado Emision a SUNAT", related="current_log_status_id.status")

    summary_sequence = fields.Integer(string="Sec. de envío del día",related="current_log_status_id.account_summary_sequence")
    json_respuesta = fields.Text(string="JSON de respuesta")
    digestValue = fields.Text(string="JSON Estado de Resumen")

    account_log_status_ids = fields.One2many("account.log.status", "account_summary_id", string="Registro de Envíos", copy=False)
    current_log_status_id = fields.Many2one("account.log.status",copy=False,string="Actual envío")

    # @api.multi
    def unlink(self):
        for record in self:
            if record.estado_emision in ["B",False]:
                result = super(AccountSummary, record).unlink()
            else:
                raise UserError("El resumen debe estar en estado borrador para ser eliminado")

    numero_envio = fields.Integer(string="Número de Envío")
    

    @api.constrains('fecha_generacion')
    def consistencia_fecha_generacion_emision(self):
        if self.fecha_emision_documentos > self.fecha_generacion:
            raise UserError("La fecha de generación del Resumen Diario debe ser mayor o igual a las fecha de emisión de los comprobantes")
        if self.fecha_generacion > fields.Date.today():
            raise UserError("La fecha de generación del Resumen diario no debe ser mayor a la fecha de hoy.")


    def load_summary(self):
        if self.cod_operacion in ["2","3"]:
            account_invoices = self.account_invoice_ids
            # raise UserError("La carga de comprobantes solo esta disponible para el código de operación 1-Adicionar")
        if not self.fecha_emision_documentos:
            raise UserError("La fecha de emisión de los documentos es obligatoria.")
        if not self.company_id:
            raise UserError("Debe seleccionar una compañía")

        if self.cod_operacion == "1":
            # Boletas de Venta
            account_invoices = self.env["account.move"].search([("invoice_date","=",self.fecha_emision_documentos),
                                                                    ("state","in",["posted"]),
                                                                    ("journal_id.invoice_type_code_id","=","03"),
                                                                    ("partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code","in",["0","1","6","7","4"]),
                                                                    ("partner_id.vat","!=",False),
                                                                    ("company_id","=",self.company_id.id),
                                                                    ("estado_comprobante_electronico", "in", ["-", False, "0_NO_EXISTE"])])
            # _logger.info(account_invoices)
            account_invoices = account_invoices.filtered(lambda r:r.account_summary_id.estado_emision in [False,"N","R"] and re.match("^B\w{3}-\d{1,8}$", r.name))

            # Listar las notas de Crédito
            nota_credito_ids = self.env["account.move"].search([("invoice_date","=",self.fecha_emision_documentos),
                                                                        ("state","in",["posted"]),
                                                                        ("journal_id.invoice_type_code_id","=","07"),
                                                                        ("partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code","in",["0","1","6","7","4"]),
                                                                        ("partner_id.vat","!=",False),
                                                                        ("reversed_entry_id","!=",False),
                                                                        ("company_id","=",self.company_id.id),
                                                                        ("estado_comprobante_electronico", "in", ["-", False, "0_NO_EXISTE"])])
            # _logger.info(nota_credito_ids)
            # nota_credito_ids = [nc for nc in nota_credito_ids if nc.reversed_entry_id.invoice_type_code == "03"]
            nota_credito_ids = nota_credito_ids.filtered(lambda nc: nc.reversed_entry_id.invoice_type_code == "03" and \
                                                                    nc.reversed_entry_id.estado_comprobante_electronico == "1_ACEPTADO" and \
                                                                    nc.account_summary_id.estado_emision in [False,"N","R"] and \
                                                                    re.match("^B\w{3}-\d{1,8}$", nc.name))

            # Listar las notas de Débito
            nota_debito_ids = self.env["account.move"].search([("invoice_date","=",self.fecha_emision_documentos),
                                                                        ("state","in",["posted"]),
                                                                        ("journal_id.invoice_type_code_id","=","08"),
                                                                        ("partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code","in",["0","1","6","7","4"]),
                                                                        ("partner_id.vat","!=",False),
                                                                        ("company_id","=",self.company_id.id),
                                                                        ("reversed_entry_id.estado_comprobante_electronico","=","1_ACEPTADO"),
                                                                        ("estado_comprobante_electronico", "in", ["-", False, "0_NO_EXISTE"])])

            # nota_debito_ids = [nd for nd in nota_debito_ids if nd.reversed_entry_id.invoice_type_code == "03"]
            nota_debito_ids = nota_debito_ids.filtered(lambda nd: nd.debit_origin_id.invoice_type_code == "03" and \
                                                                    nd.debit_origin_id.estado_comprobante_electronico == "1_ACEPTADO" and \
                                                                    nd.account_summary_id.estado_emision in [False,"N","R"] and \
                                                                    re.match("^B\w{3}-\d{1,8}$", nd.name))

            # Consolidado Boleta y Notas Asociadas
            account_invoices = account_invoices + nota_credito_ids + nota_debito_ids

        account_summary_lines = [{
            "invoice_id": invoice.id,
            "serie": invoice.name.split("-")[0],
            "correlativo":int(invoice.name.split("-")[1]),
            "tipo_documento":invoice.journal_id.invoice_type_code_id,
            "tipo_doc_receptor":invoice.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "numero_doc_receptor":invoice.partner_id.vat,
            "tipo_moneda":invoice.currency_id.name,
            # "codigo_afectacion_igv":(invoice.tax_line_ids[0].tax_id.tipo_afectacion_igv.code if len(invoice.tax_line_ids) > 0 else "10"),
            "monto_total":invoice.amount_total,
            "monto_neto":invoice.total_venta_gravado,
            "monto_igv":invoice.amount_tax,
            "cod_operacion": self.cod_operacion,
            "monto_isc":0.0,
            "monto_exe":invoice.total_venta_inafecto,
            "monto_exo":invoice.total_venta_exonerada,
            "monto_grat":invoice.total_venta_gratuito,
            "monto_exp":0.0,
            "monto_otros":0.0,
            "tipo_doc_referencia":invoice.reversed_entry_id.invoice_type_code if invoice.reversed_entry_id else "",
            "num_doc_referencia":invoice.reversed_entry_id.name if invoice.reversed_entry_id else "",
            "account_summary_id":self.id
        } for invoice in account_invoices[:200]]

        self.account_invoice_ids = [(6, 0, [account_invoice["invoice_id"] for account_invoice in account_summary_lines])]

        self.summary_line_ids = [(6, 0, [])]
        if len(account_summary_lines) > 0:
            self.summary_line_ids = [(0,0,line) for line in account_summary_lines]

        
    @api.constrains('cod_operacion')
    def _check_cod_operacion(self):
        for record in self:
            if record.estado_emision not in [False,"B"]:
                raise UserError(
                    "Sólo puede cambiar el código de operación cuando el estado del comprobante posee estado 'Borrador v  '")

    @api.onchange("cod_operacion")
    def _onchange_cod_operacion(self):
        for sl in self.summary_line_ids:
            sl.cod_operacion = self.cod_operacion

    def action_draft(self):
        if self.current_log_status_id:
            self.current_log_status_id.action_set_last_log_unlink()


    def _generate_summary_json(self):
        summary_sequence = self.env["summary.sequence"].sudo().get_next_number(self.fecha_generacion,"RC",self.company_id.id)
        name = "{}-{}-{}".format("RC",
                                self.fecha_generacion.strftime("%Y%m%d"),
                                str(summary_sequence).zfill(3))
        
        nombreEmisor = self.company_id.partner_id.registration_name.strip()
        numDocEmisor = self.company_id.partner_id.vat.strip() if self.company_id.partner_id.vat else ""
        resumen_diario_json = {}
        resumen_diario_json["company"] = {
            "ruc": numDocEmisor,
            "razon_social": nombreEmisor,
            "usuario": self.company_id.sunat_user,
            "password": self.company_id.sunat_pass,
            "key_private": self.company_id.cert_id.key_private,
            "key_public": self.company_id.cert_id.key_public,
        }
        resumen_diario_json["resumen"] = {
            "numDocEmisor": self.company_id.partner_id.vat,
            "tipoDocEmisor": self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "fechaReferente": self.fecha_emision_documentos.strftime("%Y-%m-%d"),
            "nombreEmisor": self.company_id.partner_id.name,
            "id":summary_sequence
        }
        resumen_diario_json["fechaGeneracion"] = self.fecha_generacion.strftime("%Y-%m-%d")
        resumen_diario_json["tipoResumen"] = "RC"
        resumen_diario_json["idTransaccion"] = name
        resumen_diario_json["detalle"] = []

        for summary_line in self.summary_line_ids:
            resumen_diario_json["detalle"].append({
                "serie": summary_line.serie,
                "correlativo": summary_line.correlativo,
                "tipoDocumento": summary_line.tipo_documento,
                "tipoDocReceptor": summary_line.tipo_doc_receptor,
                "numDocReceptor": summary_line.numero_doc_receptor,
                "tipoMoneda": summary_line.tipo_moneda,
                "mntIgv": round(summary_line.monto_igv, 2),
                "mntIsc": round(summary_line.monto_isc, 2),
                "codOperacion": summary_line.cod_operacion,
                "mntTotal": round(summary_line.monto_total, 2),
                "mntNeto": round(summary_line.monto_neto, 2),
                "mntExo": round(summary_line.monto_exo, 2),
                "mntExe": round(summary_line.monto_exe, 2),
                "mntExp": round(summary_line.monto_exp, 2),
                "mntGrat": round(summary_line.monto_grat, 2),
                "mntOtros": round(summary_line.monto_otros, 2),
                "tipoDocReferencia": summary_line.tipo_doc_referencia,
                "numDocReferencia": summary_line.num_doc_referencia
            })
        return resumen_diario_json

    def action_generate_and_signed_xml(self):
        if not self.company_id:
            raise UserError("El campo de compañía es Obligatoria.")
        
        # tipo_envio = self.company_id.tipo_envio
        summary_json = self._generate_summary_json()
        credentials = summary_json.get("company")
  
        request = main.handle(summary_json,credentials)
        log_status = {
            "company_id":self.company_id.id,
            "account_summary_id":self.id,
            "request_json": json.dumps(summary_json,indent=4),
            "name": summary_json.get("idTransaccion"),
            "account_summary_sequence":summary_json.get("id"),
            "date_request": self.fecha_generacion,
            "date_issue": self.fecha_emision_documentos,
            "status":"P",
            "digest_value":request.get("digest_value","-"),
            "signed_xml_data":request.get("signed_xml","-") if request.get("signed_xml",False) else "",
            "signed_xml_with_creds":parseString(request.get("final_xml")).toprettyxml() if request.get("final_xml",False) else "",
        }
        log_status_obj = self.env["account.log.status"].sudo().create(log_status)
        log_status_obj.sudo().action_set_last_log()

    def action_send_summary(self):
        if not self.current_log_status_id:
            self.action_generate_and_signed_xml()
        result = {}
        try:
            result = send_summary_xml(self)
            self.current_log_status_id.write(result)
        except Exception as e:
            return result
    
    def cron_action_send_summary_pending(self):
        summarys = self.env["account.summary"].search([("current_log_status_id.status","in",["P","N",False,""])])
        for summ in summarys:
            if summ.cod_operacion == "1":
                summ.action_send_summary()
            elif summ.cod_operacion in ["2","3"]:
                if all(summ.account_invoice_ids.mapped(lambda inv:inv.estado_comprobante_electronico == "1_ACEPTADO")):
                    summ.action_send_summary()

    def post(self):
        self.ensure_one()
        self.load_summary()
        if len(self.account_invoice_ids) == 0:
            raise UserError("Al menos debe existir 1 comprobante a publicar. La lista de comprobantes esta vacía")
        
        if self.cod_operacion == "1":
            if not self.current_log_status_id:
                self.action_send_summary()
        elif self.cod_operacion in ["2","3"]:
            self.action_generate_and_signed_xml()

    def action_request_status_ticket(self):
        if not self.current_log_status_id:
            raise UserError("El campo de ticket esta vacío")
        response = self.current_log_status_id.action_request_status_ticket_summary()

        if response.get("status") == "A" and self.cod_operacion in ["1","2"]:
            self.account_invoice_ids.write({'estado_comprobante_electronico':'1_ACEPTADO'})
        if response.get("status") == "A" and self.cod_operacion == "3":
            self.account_invoice_ids.write({'estado_comprobante_electronico':'2_ANULADO'})
            
    def cron_action_request_status_ticket(self):
        summary_objs = self.env["account.summary"].search([["estado_emision", "in", ["E","N"]]])
        for summary in summary_objs:
            try:
                summary.action_request_status_ticket()
            except Exception as e:
                pass
            self.env.cr.commit()
        return True

    def cron_action_generate_and_signed_xml(self):
        today = fields.Date.today()
        # Boletas de Venta
        account_invoices = self.env["account.move"].search([("invoice_date","<=",today),
                                                                ("state","in",["posted"]),
                                                                ("journal_id.invoice_type_code_id","=","03"),
                                                                ("partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code","in",["0","1","6"]),
                                                                ("partner_id.vat","!=",False),
                                                                ("estado_comprobante_electronico", "in", ["-", False, "0_NO_EXISTE"])])

        account_invoices = account_invoices.filtered(lambda r:r.account_summary_id.estado_emision in [False,"N","R"])

        # Listar las notas de Crédito
        nota_credito_ids = self.env["account.move"].search([("invoice_date","<=",today),
                                                                    ("state","in",["posted"]),
                                                                    ("journal_id.invoice_type_code_id","=","07"),
                                                                    ("partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code","in",["0","1","6"]),
                                                                    ("partner_id.vat","!=",False),
                                                                    ("reversed_entry_id","!=",False),
                                                                    ("account_summary_id.estado_emision","in",[False,"N","R"]),
                                                                    ("estado_comprobante_electronico", "in", ["-", False, "0_NO_EXISTE"])])

        nota_credito_ids = nota_credito_ids.filtered(lambda nc: nc.reversed_entry_id.invoice_type_code == "03" and \
                                                                nc.reversed_entry_id.estado_comprobante_electronico == "1_ACEPTADO" and \
                                                                nc.account_summary_id.estado_emision in [False,"N","R"])

        # Listar las notas de Débito
        nota_debito_ids = self.env["account.move"].search([("invoice_date","<=",today),
                                                                    ("state","in",["posted"]),
                                                                    ("journal_id.invoice_type_code_id","=","08"),
                                                                    ("partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code","in",["0","1","6"]),
                                                                    ("partner_id.vat","!=",False),
                                                                    ("reversed_entry_id.estado_comprobante_electronico","=","1_ACEPTADO"),
                                                                    ("account_summary_id.estado_emision","in",[False,"N","R"]),
                                                                    ("estado_comprobante_electronico", "in", ["-", False, "0_NO_EXISTE"])])

        nota_debito_ids = nota_debito_ids.filtered(lambda nd: nd.debit_origin_id.invoice_type_code == "03" and \
                                                                nd.debit_origin_id.estado_comprobante_electronico == "1_ACEPTADO" and \
                                                                nd.account_summary_id.estado_emision in [False,"N","R"])

        invoices = account_invoices + nota_credito_ids + nota_debito_ids
        try:
            for company in invoices.mapped("company_id"):
                invoices_by_company = invoices.filtered(lambda inv: inv.company_id == company and re.match("^B\w{3}-\d{1,8}$", inv.name))
                invoice_dates = list(set(invoices_by_company.mapped("invoice_date")))

                for invoice_date in invoice_dates:

                    summary = {
                        "fecha_generacion": fields.Date.today(),
                        "fecha_emision_documentos": invoice_date,
                        "cod_operacion": "1",
                        "company_id": company.id
                    }
                    summary_obj = self.env["account.summary"].sudo().create(summary)
                    summary_obj.load_summary()
                    summary_obj.post()
                    self.env.cr.commit()
        except Exception as e:
            _logger.info(e)
        
        return True


class AccountSummaryVoided(models.TransientModel):
    _name = 'account.summary.anulacion'
    _description = 'Anular Comprobante'

    account_invoice_id = fields.Many2one("account.move", string="Comprobante Electrónico",required=True)
    company_id = fields.Many2one("res.company",string="Compañía",required=True)

    def btn_anular_comprobante(self):
        resumen = {
            "fecha_generacion": fields.Date.today(),
            "fecha_emision_documentos": self.account_invoice_id.invoice_date,
            "cod_operacion": "3",
            "account_invoice_ids": [(6, 0, [self.account_invoice_id.id])],
            "company_id":self.company_id.id
        }
        resumen_obj = self.env["account.summary"].create(resumen)
        self.account_invoice_id.resumen_anulacion_id = resumen_obj.id
        resumen_obj.post()
        # resumen_obj.generar_identificador_resumen()
        # resumen_obj.cargar_resumen_lineas()
        # resumen_obj.generar_resumen_diario()
        # resumen_obj.btn_enviar_resumen_diario()
