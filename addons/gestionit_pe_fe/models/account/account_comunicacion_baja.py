from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from lxml import etree
from datetime import datetime, timedelta
from . import oauth
import json
import requests
import os
import logging
from xml.dom.minidom import parse, parseString
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion import api_models
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion.controllers import main
from odoo.addons.gestionit_pe_fe.models.account.oauth import send_voided_xml
import re
from pytz import timezone
_logger = logging.getLogger(__name__)


class AccountComunicacionBaja(models.Model):
    _name = "account.comunicacion_baja"
    _description = "Documento de baja"
    _rec_name = "identificador_anulacion"

    

    date_invoice = fields.Date(string='Fecha de emisión de factura',
                              required=True,
                               copy=False)

    # issue_date = fields.Date(string='Fecha de Generación',
    #                          copy=False,
    #                          default=)
    
    voided_date = fields.Date(string='Fecha de anulación',required=True,
                             copy=False)

    @api.constrains("date_invoice")
    def _check_date_invoice(self):
        now =  datetime.date(datetime.now(tz=timezone(self.env.user.tz or "America/Lima")))
        if now < self.date_invoice:
            raise ValidationError("* La fecha de la emisión del comprobante debe ser menor o igual a la fecha del día de hoy.")
        elif abs(self.date_invoice - now).days > 7:
            raise ValidationError("No se puede enviar documentos con mas de 7 dias de antiguedad")


    # sent = fields.Boolean(readonly=True, default=False, copy=False,
    #                       help="It indicates that the invoice has been sent.")

    # @api.model
    # def _default_documents(self):
    #     if self._context.get('default_documents', False):
    #         return self.env['account.move'].browse(self._context.get('default_documents'))

    user_id = fields.Many2one('res.users', string='Salesperson',
                              readonly=True, states={'B': [('readonly', False)]}, required=True,
                              default=lambda self: self.env.user)



    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)

    # status_envio = fields.Boolean("Estado del envio del documento", default=False)

    json_comprobante = fields.Text(string="JSON de envio")

    json_respuesta = fields.Text(string="JSON de respuesta")

    json_estado_comunicacion_baja = fields.Text(string="JSON estado de Comunicación de Baja")

    descripcion_estado_com_baja = fields.Text(string="Descripción de estado de Comunicación de Baja")

    ticket = fields.Char(string="Ticket")
    current_log_status_id = fields.Many2one('account.log.status',copy=False)
    account_log_status_ids = fields.One2many("account.log.status", "account_voided_id", string="Registro de Envíos", copy=False)
    voided_ticket = fields.Char(string="Ticket",related="current_log_status_id.voided_ticket",store=True)
    identificador_anulacion = fields.Char(string="Identificador de anulación",default="Anulación",related="current_log_status_id.name")

    state = fields.Selection(
        selection = [
            ('E', 'Enviado a SUNAT'),
            ('A', 'Aceptado'),
            # Rechazado por SUNAT cuando se realiza el envío de la comunicación de baja esto puede ser debido a que sunat esta no disponible o el xml tiene fallos
            ('N', 'Envio Erróneo'),
            ('O', 'Aceptado con Observación'),
            ('R', 'Rechazado'),  # Rechazado por SUNAT cuando se consulta con el ticket
            # SUNAt esta en estado no disponible y su estado pasa a pendiente de envío para enviarse después
            ('P', 'Pendiente de envío a SUNAT'),
        ], string="Estado Emision a SUNAT", copy=False,related="current_log_status_id.status",store="True")


    # contador = fields.Integer(string="Contador", states={'B': [('readonly', False)]})
    voided_sequence = fields.Integer(string="Sec. de envío del día")

    motivo = fields.Text(string="Motivo de Baja",required=True)

    company_id = fields.Many2one('res.company', string='Compañia',required=True, readonly=True)

    # _sql_constraints = [
    #     ('motivo_length_min','LENGTH(motivo)>=4','El tamaño del motivo debe tener por lo menos 4 carácteres.')
    # ]
    @api.constrains("motivo")
    def _check_motivo(self):
        if len(self.motivo) <4:
            raise UserError('El tamaño del motivo debe tener por lo menos 4 carácteres.')
    

    # def invoice_validate(self):
    #     for invoice in self:
    #         if self.search([('id', '!=', invoice.id)]):
    #             raise UserError("Documento Duplicado.")
    #     return self.write({'state': 'E'})

    # def action_summary_cancel(self):
    #     if self.filtered(lambda summ: summ.state not in ['B', 'R', 'N', 'P']):
    #         raise UserError(
    #             "Para cancelar este resumen, su estado debe ser: Borrador, Envío Erróneo, Rechazado o Pendiente de Envío")
    #     return self.write({'state': 'C'})

    # def action_summary_draft(self):
    #     if self.filtered(lambda inv: inv.state != 'C'):
    #         raise UserError(
    #             "Para pasar a estado 'Borrador' el Resumen debe estar en estado 'Cancelado'.")
    #     return self.write({'state': 'B'})

    # def _default_invoice_ids(self):
    #     invoices = []
    #     if self._context.get('default_invoice_ids', False):
    #         for document in self._context.get('default_invoice_ids'):
    #             invoices.append(self.env['account.move'].browse(document))
    #         return invoices

    invoice_ids = fields.One2many('account.move', "documento_baja_id")


    invoice_type_code_id = fields.Selection(string="Tipo de Comprobante",
                                            selection=[('01', 'Factura'),
                                                       ('07', 'Nota de crédito'),
                                                       ('08', 'Nota de débito')],
                                            readonly=True)
    def _generate_voided_json(self):
        voided_sequence = self.env["summary.sequence"].sudo().get_next_number(self.voided_date,"RC",self.company_id.id)
        name = "{}-{}-{}".format("RA",
                        self.voided_date.strftime("%Y%m%d"),
                        str(voided_sequence).zfill(3))
        data = {
            "tipoResumen": "RA",
            "fechaGeneracion": self.voided_date.strftime("%Y-%m-%d"),
            "idTransaccion": name,
            "resumen": {
                "id": voided_sequence,
                "tipoDocEmisor": self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
                "numDocEmisor": self.company_id.partner_id.vat,
                "nombreEmisor": self.company_id.partner_id.name,
                "fechaReferente": self.date_invoice.strftime("%Y-%m-%d"),
            },
            "company":{
                "ruc": self.company_id.partner_id.vat,
                "razon_social": self.company_id.partner_id.name,
                "usuario": self.company_id.sunat_user,
                "password": self.company_id.sunat_pass,
                "key_private": self.company_id.cert_id.key_private,
                "key_public": self.company_id.cert_id.key_public,
            }
        }

        data_detalle = []
        for inv in self.invoice_ids.filtered(lambda inv:re.match("^F\w{3}-\d{1,8}$", inv.name)):
            serie,correlativo = inv.name.split("-")
            data_detalle.append({
                "serie": serie,
                "correlativo": correlativo,
                "tipoDocumento": inv.invoice_type_code,
                "motivo": self.motivo
            })
        data['detalle'] = data_detalle
        return data


    def action_generate_and_signed_xml(self):
        if not self.company_id:
            raise UserError("El campo de compañía es Obligatoria.")
        tipo_envio = self.company_id.tipo_envio
        summary_json = self._generate_voided_json()
        credentials = summary_json.get("company")
        request = main.handle(summary_json,credentials)
        log_status = {
            "company_id":self.company_id.id,
            "account_voided_id":self.id,
            "request_json": json.dumps(summary_json,indent=4),
            "name": summary_json.get("idTransaccion"),
            "date_request": fields.Date.today(),
            "date_issue": self.date_invoice,
            "status":"P",
            "digest_value":request.get("digest_value","-"),
            "signed_xml_data":request.get("signed_xml","-") if request.get("signed_xml",False) else "",
            "signed_xml_with_creds":parseString(request.get("final_xml")).toprettyxml(" ") if request.get("final_xml",False) else "",
        }
        log_status_obj = self.env["account.log.status"].sudo().create(log_status)
        log_status_obj.sudo().action_set_last_log()

    def action_send_voided(self):
        if not self.current_log_status_id:
            self.action_generate_and_signed_xml()
        result = {}
        try:
            if all(self.invoice_ids.mapped(lambda r:r.estado_comprobante_electronico == "1_ACEPTADO")):
                result = send_voided_xml(self)
                self.current_log_status_id.write(result)
        except Exception as e:
            return result


    def post(self):
        if len(self.invoice_ids) == 0:
            raise UserError("Al menos debe existir 1 comprobante para anular. La lista de comprobantes esta vacía")
        self.action_send_voided()
        
    def action_request_status_ticket(self):
        if not self.voided_ticket:
            raise UserError("El campo de ticket esta vacío")
        response = self.current_log_status_id.action_request_status_ticket_voided()
        # _logger.info(response)
        if response.get("status") == "A":
            self.invoice_ids.write({'estado_comprobante_electronico':'2_ANULADO'})
            

    def cron_enviar_comunicacion_baja(self):
        voided_ids = self.env["account.comunicacion_baja"].search([("state", "in", ["P","N",False])])
        for voided in voided_ids:
            if all(voided.invoice_ids.mapped(lambda inv: inv.estado_comprobante_electronico == "1_ACEPTADO")):
                # raise UserError("La comunicación de baja solo se puede aplicar a comprobandetes aceptados. Revise si los comprobantes de esta anulación estan aceptados.")
                try:
                    voided.action_send_voided()
                except Exception as E:
                    pass

    # @api.multi
    def cron_consulta_estado_comunicacion_baja(self):
        voided_ids = self.env["account.comunicacion_baja"].search([("voided_ticket","!=",False),("state","in",["E","N","P",False])])
        for voided in voided_ids:
            try:
                # baja.consulta_estado_comunicacion_baja()
                voided.action_request_status_ticket()
            except Exception as E:
                pass

    def enviar_comunicacion_baja(self):
        data_doc = self.crear_json_baja()
        try:
            response_env = oauth.enviar_doc_baja_url(data_doc, self.company_id.tipo_envio)
        except Exception as e:
            raise UserError(e)
        except NewConnectionError as e:
            raise UserError("Error en la conexión con sunat, pruebe su conexión de internet o inténtelo más tarde.")

        self.json_comprobante = json.dumps(data_doc, indent=4)
        self.json_respuesta = json.dumps(response_env, indent=4)

        if response_env["success"] and response_env['sunat_status'] != 'R':
            self.state = response_env['sunat_status']
            self.ticket = response_env['ticket']
        else:
            recepcionado, state, msg_error = oauth.extraer_error(response_env)

            if recepcionado:
                self.state = state
                return {
                    'name': 'Message',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'custom.pop.message',
                    'target': 'new',
                    'context': {
                        'default_name': msg_error
                    }
                }
            else:
                raise UserError("El servidor de SUNAT no está respondiendo correctamente. Inténtelo nuevamante en unos minutos.")


    # def crear_json_baja(self):
    #     nombreEmisor = self.company_id.partner_id.registration_name.strip()
    #     numDocEmisor = self.company_id.partner_id.vat.strip() if self.company_id.partner_id.vat else ""
    #     data = {
    #         "company": {
    #             "numDocEmisor": numDocEmisor,
    #             "nombreEmisor": nombreEmisor,
    #             "SUNAT_user": self.company_id.sunat_user,
    #             "SUNAT_pass": self.company_id.sunat_pass,
    #             "key_private": self.company_id.cert_id.key_private,
    #             "key_public": self.company_id.cert_id.key_public,
    #         },
    #         "tipoResumen": "RA",
    #         "fechaGeneracion": str(self.date_invoice),
    #         "idTransaccion": str(self.id),
    #         "resumen": {
    #             "id": self.contador,
    #             "tipoDocEmisor": self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
    #             "numDocEmisor": self.company_id.partner_id.vat,
    #             "nombreEmisor": self.company_id.partner_id.registration_name,
    #             "fechaReferente": str(self.date_invoice),
    #             "tipoFormatoRepresentacionImpresa": "GENERAL"
    #         }
    #     }

    #     data_detalle = []
    #     for document in self.invoice_ids:
    #         data_detalle.append({
    #             "serie": document.name[0:4],
    #             "correlativo": int(document.name[5:len(document.name)]),
    #             "tipoDocumento": document.journal_id.invoice_type_code_id,
    #             "motivo": self.motivo
    #         })

    #     data['detalle'] = data_detalle

    #     return data

    def consulta_estado_comunicacion_baja(self):
        if not self.ticket:
            raise UserError("El campo de Ticket esta vacío")

        nombreEmisor = self.company_id.partner_id.registration_name.strip()
        numDocEmisor = self.company_id.partner_id.vat.strip() if self.company_id.partner_id.vat else ""

        data = {
            "company": {
                "numDocEmisor": numDocEmisor,
                "nombreEmisor": nombreEmisor,
                "SUNAT_user": self.company_id.sunat_user,
                "SUNAT_pass": self.company_id.sunat_pass,
                "key_private": self.company_id.cert_id.key_private,
                "key_public": self.company_id.cert_id.key_public,
            },
            "ticket": self.ticket,
            "tipoEnvio": int(self.company_id.tipo_envio)
        }
        try:
            result = api_models.consultaResumen(data)
        except Exception as e:
            raise UserError(e)

        self.json_estado_comunicacion_baja = json.dumps(result, indent=4)


        if result:
            status = result.get("status", False)
            code = result.get("code", False)
            if code == "env:Server":
                raise UserError(result["description"])

            if status:
                self.state = result["status"]
                self.descripcion_estado_com_baja = result["description"]
            else:
                raise UserError(json.dumps(result))
        else:
            raise UserError(json.dumps(result))

    def unlink(self):
        for voided in self:
            if voided.state:
                raise UserError("La anulación no puede ser eliminada.")
        return super(AccountComunicacionBaja, self).unlink()