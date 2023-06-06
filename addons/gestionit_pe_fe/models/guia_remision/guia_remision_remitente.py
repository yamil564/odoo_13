from requests.exceptions import (
    RequestException, Timeout, URLRequired,
    TooManyRedirects, HTTPError, ConnectionError,
    FileModeWarning, ConnectTimeout, ReadTimeout
)
from xml.dom.minidom import parse, parseString
from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError, Warning
import requests
import os
import base64
import re
import json
import re
from odoo.addons.gestionit_pe_fe.models.account.oauth import send_doc_xml
# from odoo.addons.gestionit_pe_fe.models.account.api_facturacion import api_models
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion.controllers import xml_validation, sunat_response_handle, main, firma
import logging
from datetime import datetime
_logger = logging.getLogger(__name__)


patron_dni = re.compile("\d{8}$")
patron_ruc = re.compile("[12]\d{10}$")
patron_placa_vehicular = re.compile("[0-9a-zA-Z]{3}[0-9]{3}|[0-9a-zA-Z]{3}-[0-9]{3}|[0-9a-zA-Z]{3}-[0-9]{2}[0-9a-zA-Z]$")

codigo_unidades_de_medida = [
    "DZN",
    "DAY",
    "HUR",
    "LTR",
    "NIU",
    "CMT",
    "GLL",
    "OZI",
    "GRM",
    "GLL",
    "KGM",
    "LBR",
    "MTR",
    "LBR",
    "SMI",
    "ONZ",
    "FOT",
    "INH",
    "LTN",
    "BX"
]

class ModalidadTransporte(models.Model):
    _name = "gestionit.modalidad_transporte"
    _description = "Modalidad de Transporte"
    code = fields.Char("Código")
    name = fields.Char("Descripción")

class MotivoTraslado(models.Model):
    _name = "gestionit.motivo_traslado"
    _description = "Motivo de traslado"
    code = fields.Char("Código")
    name = fields.Char("Descripción")
    active = fields.Boolean("Activo", default=True)

class GuiaRemisionLine(models.Model):
    _name = "gestionit.guia_remision_line"
    _description = "Líneas de guía de remisión"

    product_id = fields.Many2one("product.product", required=True)
    uom_id = fields.Many2one("uom.uom", string="UM", required=True)
    qty = fields.Float(string="Cantidad", digits='Product Unit of Measure')
    guia_remision_id = fields.Many2one(
        "gestionit.guia_remision", ondelete='cascade')
    description = fields.Char(string="Descripción", required=True)
    stock_picking_id = fields.Many2one("stock.picking", "Movimiento de Stock")
    sequence = fields.Integer()

    @api.constrains('uom_id')
    def _check_uom_id(self):
        for record in self:
            if record.uom_id.code not in codigo_unidades_de_medida:
                raise UserError(
                    "La unidad de medida seleccionada no posee un código válido.")

    @api.constrains('description')
    def _check_description(self):
        for record in self:
            if len(record.description) < 4 and len(record.description) > 100:
                raise UserError(
                    "La Descripción del producto debe tener por lo menos 4 carácteres y a lo ás 100 carácteres.")

    @api.onchange('description')
    def _onchange_description(self):
        if self.description:
            self.description = self.description.strip().replace("\n", "")

    @api.onchange('product_id')
    def _onchange_product(self):
        for record in self:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id.id

    @api.constrains('qty')
    def _check_qty(self):
        for record in self:
            if record.qty < 0:
                raise UserError(
                    "La cantidad de las líneas de producto no pueden ser negativas.")

class ResPartner(models.Model):
    _inherit = "res.partner"
    es_conductor = fields.Boolean(string="Es Conductor", default=False)
    es_empresa_transporte_publico = fields.Boolean(
        string="Es empresa de transporte publico", default=False)
    vehiculo_ids = fields.One2many("gestionit.vehiculo", "propietario_id", string="Vehículos")
    licencia = fields.Char("Licencia")


    def action_view_conductores_privados(self):
        dni = self.env["l10n_latam.identification.type"].search([("l10n_pe_vat_code","=",1)],limit=1)
        return {
            'name': 'Conductores Privados',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [[self.env.ref("gestionit_pe_fe.view_tree_partner_conductor").id, "tree"], [self.env.ref("gestionit_pe_fe.view_form_partner_conductor").id, "form"]],
            'res_model': 'res.partner',
            'target': 'self',
            'domain': [('es_conductor', '=', True), ('parent_id', '!=', False), ('parent_id', '=', self.env.company.partner_id.id)],
            'context': {
                "default_es_conductor": True,
                "parent_id": self.env.company.partner_id.id,
                "default_country_id": 173,
                "default_l10n_latam_identification_type_id":dni.id
            }
        }

class Vehiculo(models.Model):
    _name = 'gestionit.vehiculo'
    _rec_name = "numero_placa"
    _description = "Vehículo"
    numero_placa = fields.Char("Número de placa",size=8)
    tipo_transporte = fields.Selection(selection=[("carretera", "Carretera"),
                                                  ("maritimo", "Maritimo"),
                                                  ("ferroviaria", "Ferroviaria"),
                                                  ("area", "Aerea"),
                                                  ("pluvial", "Pluvial"),
                                                  ("lacustre", "Lacustre")], default="carretera")
    marca = fields.Char("Marca")
    modelo = fields.Char("Modelo")
    inscripcion_mtc = fields.Char("N° Inscripción MTC")
    operativo = fields.Selection(string="Operativo",
                                 selection=[("operativo", "Operativo"),
                                            ("fuera_de_servicio", "Fuera de Servicio")],
                                 default="operativo")

    descripcion = fields.Text("Descripción")
    propietario_id = fields.Many2one("res.partner", "Propietario")
    company_id = fields.Many2one("res.company", string="Compañía",
                                 default=lambda self: self.env.company.id)

    def action_view_vehiculos_privados(self):
        return {
            'name': 'Vehículos Privados',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [[self.env.ref("gestionit_pe_fe.view_tree_vehiculo").id, "tree"], [self.env.ref("gestionit_pe_fe.view_form_vehiculo").id, "form"]],
            'res_model': 'gestionit.vehiculo',
            'target': 'self',
            'domain': [('propietario_id', '=', self.env.company.partner_id.id)],
            'context': {
                "default_propietario_id": self.env.company.partner_id.id,
            }
        }

    def validacion_placa_vehicular(self):
        if not bool(patron_placa_vehicular.match(self.numero_placa)):
            return False
        return True

    @api.constrains('numero_placa')
    def restriccion_placa_vehicular(self):
        for record in self:
            if not record.validacion_placa_vehicular():
                raise UserError("El número de placa vehicular es inválido.")

class PopupFormSelectUbigeo(models.TransientModel):
    _name = 'gestionit.popup_form_seleccion_ubigeo'
    _description = 'Selección de Ubigeo'

    departamento_id = fields.Many2one(
        "res.country.state", string="Departamento")
    provincia_id = fields.Many2one("res.country.state", string="Provincia")
    distrito_id = fields.Many2one(
        "res.country.state", string="Distrito", required=True)
    guia_remision_id = fields.Many2one(
        "gestionit.guia_remision", required=True)
    tipo_lugar = fields.Selection(
        selection=[("partida", "Partida"), ("llegada", "Llegada")], required=True)
    ubigeo = fields.Char("Ubigeo")
    ubigeo_code = fields.Many2one("res.country.state", string="Ubigeo Code")

    @api.onchange('distrito_id')
    def _onchange_ubigeo(self):
        for record in self:
            record.ubigeo = record.distrito_id.code if record.distrito_id else ""

    def set_ubigeo(self):
        record = self
        # os.system("echo '{}'".format(record.guia_remision_id.numero))
        if record.tipo_lugar == "partida":
            # os.system("echo '{}'".format("partida"))
            record.guia_remision_id.write(
                {"lugar_partida_ubigeo": record.ubigeo})
            # record.guia_remision_id.write({"lugar_partida_ubigeo":record.ubigeo})
        elif record.tipo_lugar == "llegada":
            # os.system("echo '{}'".format("llegada"))
            record.guia_remision_id.write(
                {"lugar_llegada_ubigeo": record.ubigeo})

class GuiaRemision(models.Model):
    _name = "gestionit.guia_remision"
    _rec_name = "numero"
    _description = "Guía de Remisión Electrónica"

    company_id = fields.Many2one("res.company", string="Compañía",
                                 default=lambda self: self.env.company.id,
                                 states={'validado': [('readonly', True)]})

    company_partner_id = fields.Many2one(
        "res.partner", related="company_id.partner_id", readonly=True)
    account_log_status_ids = fields.One2many(
        "account.log.status", "guia_remision_id", string="Registro de Envíos", copy=False)

    current_log_status_id = fields.Many2one("account.log.status",copy=False)

    ######################## CODE HASH ###################################################
    digest_value = fields.Char(string="Digest Value",copy=False,default="*",compute="compute_campo_digest_value")
    #    "current_log_status_id.digest_value"
    #######################################################################################
    # SERIE Y CORRELATIVO
    journal_id = fields.Many2one("account.journal", string="Serie", states={
                                 'validado': [('readonly', True)]})
    correlativo = fields.Integer(string="Correlativo", copy=False)
    serie = fields.Char("Prefijo", related="journal_id.code", copy=False)
    numero = fields.Char(
        "Número", default="Guía de Remisión - Borrador", copy=False)
    name = fields.Char("Nombre", index=True, states={
                       'validado': [('readonly', True)]}, copy=False)

    request_json = fields.Text("Petición JSON", states={
                               'validado': [('readonly', True)]}, copy=False)
    response_json = fields.Text("Respuesta JSON", states={
                                'validado': [('readonly', True)]}, copy=False)

    transporte_lines = fields.One2many('gestionit.lineas_transporte', 'guia_id', 'Lineas de Transporte')
    note = fields.Text('Observaciones')
    multiple_tramos = fields.Boolean('Multiples Tramos', default=False)

    ###############################################
    @api.depends('current_log_status_id')
    def compute_campo_digest_value(self):
        for rec in self:
            if rec.current_log_status_id:
                rec.digest_value = rec.current_log_status_id.digest_value
            else:
                rec.digest_value = "*"
    
    ########################################################
    def generate_text_qr_guia_remision(self):
        ruc_emisor = self.destinatario_partner_id.vat
        invoice_ids = self.comprobante_pago_ids
        if invoice_ids:
            invoice_id = invoice_ids[0]
            prefix_code,invoice_number = invoice_id.name.split('-')

            if prefix_code and invoice_number:
                #digest_value = invoice.digest_value if invoice.digest_value else "-"
                s = ruc_emisor+"|"+prefix_code+"|"+invoice_number
                return s
    ########################################################

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                'gestionit_pe_fe', 'mail_template_bo_guia_remision')[1]
        except ValueError:
            template_id = False

        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        attach_ids = []
        xml_fname = self.numero+".xml"
        cdr_fname = self.numero+"_cdr.xml"
        pdf_fname = self.numero+".pdf"

        pdf = self.env.ref(
            'gestionit_pe_fe.report_guia_remision').render_qweb_pdf(self.ids)
        datas = base64.b64encode(pdf[0])
        attach_ids.append(self.env["ir.attachment"].create(
            {"name": pdf_fname, "type": "binary", "datas": datas, "mimetype": "application/x-pdf", "res_model": "gestionit.guia_remision", "res_id": self.id, "res_name": self.numero}).id)

        log_status = self.current_log_status_id
        if log_status:
            # data_signed_xml = log_status.signed_xml_data_without_format
            data_signed_xml = log_status.signed_xml_data

            if data_signed_xml:
                datas = base64.b64encode(data_signed_xml.encode())
                attach_ids.append(self.env["ir.attachment"].create(
                    {"name": xml_fname, "type": "binary", "datas": datas, "mimetype": "text/xml", "res_model": "gestionit.guia_remision", "res_id": self.id, "res_name": self.numero}).id)

            # response_xml = log_status.response_xml_without_format
            response_xml = log_status.response_xml_without_format
            if response_xml:
                datas = base64.b64encode(response_xml.encode())
                attach_ids.append(self.env["ir.attachment"].create(
                    {"name": cdr_fname, "type": "binary", "datas": datas, "mimetype": "text/xml", "res_model": "gestionit.guia_remision", "res_id": self.id, "res_name": self.numero}).id)

        # wizard.attachment_ids = [(4, attach_id)
        #                             for attach_id in attach_ids]
        # _logger.info("Attachments")
        # _logger.info(attach_ids)

        ctx = {
            'default_model': 'gestionit.guia_remision',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_attachment_ids': [(6, 0, attach_ids)],
        }
        return {
            'name': 'Compose Email',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def default_get(self, flds):
        res = super(GuiaRemision, self).default_get(flds)
        journals = self.env["account.journal"].search(
            [("invoice_type_code_id", "=", "09"), ("company_id", "=", self.env.company.id)])
        if len(journals) > 0:
            res.update({
                "journal_id": journals[0].id
            })
            res.update({
                "correlativo": journals[0].sequence_number_next,
                "numero": "Guía de Remisión Electrónica",
                "motivo_traslado": "01",
                # "modalidad_transporte":"02",
                "fecha_emision": fields.Datetime.now()
            })

        return res

    @api.onchange("journal_id")
    def _onchange_numero_guia_remision(self):
        for record in self:
            if record.journal_id:
                record.correlativo = record.journal_id.sequence_number_next

    @api.onchange("modalidad_transporte")
    def _onchange_modalidad_transporte(self):
        for record in self:
            if record.modalidad_transporte == "01":
                record.conductor_privado_partner_id = False
                record.vehiculo_privado_id = False
                record.conductor_publico_id = False
                record.vehiculo_publico_id = False
            elif record.modalidad_transporte == "02":
                record.transporte_partner_id = False

    def default_direccion_llegada_id(self):
        return self.destinatario_partner_id.child_ids[0].id if len(self.destinatario_partner_id.child_ids) else False

    @api.onchange("motivo_traslado")
    def _onchange_motivo_traslado(self):
        for record in self:
            record.numero_bultos = 0
            record.partner_direccion_llegada_id = False
            record.partner_direccion_partida_id = False
            # record.destinatario_partner_id = False
            record.proveedor_partner_id = False
            record.direccion_llegada_id = False
            record.direccion_partida_id = False
            if record.motivo_traslado in ['01', '09', '19', '13', '09']:
                record.partner_direccion_partida_id = record.company_partner_id.id
                record.partner_direccion_llegada_id = record.destinatario_partner_id.id
                record.direccion_partida_id = record.company_partner_id.child_ids[0].id if len(
                    record.company_partner_id.child_ids) else False
                record.direccion_llegada_id = record.default_direccion_llegada_id()
            if record.motivo_traslado in ['04', '18']:
                record.partner_direccion_llegada_id = record.company_partner_id.id
                record.partner_direccion_partida_id = record.company_partner_id.id
                record.destinatario_partner_id == record.company_partner_id.id
            if record.motivo_traslado in ['02']:
                record.destinatario_partner_id = record.company_partner_id.id
                record.partner_direccion_llegada_id = record.company_partner_id.id

    @api.constrains('peso_bruto_total')
    def _check_peso_bruto_total(self):
        for record in self:
            if record.peso_bruto_total < 0:
                raise UserError(
                    "El peso bruto total del envío debe ser mayor a 0.")

    # DESTINATARIO
    motivo_traslado = fields.Selection(selection="_list_motivo_traslado", string="Motivo de Traslado", states={
                                       'validado': [('readonly', True)]})

    def _list_motivo_traslado(self):
        motivo_traslado_objs = self.env["gestionit.motivo_traslado"].search([])
        return [(mt.code, mt.name) for mt in motivo_traslado_objs]

    destinatario_partner_id = fields.Many2one(
        "res.partner", string="Destinatario", states={'validado': [('readonly', True)]})
    destinatario_tipo_documento_identidad = fields.Char(
        string="Tipo de Documento", related="destinatario_partner_id.l10n_latam_identification_type_id.name")
    destinatario_numero_documento_identidad = fields.Char(
        string="Número de Documento", related="destinatario_partner_id.vat")
    destinatario_direccion = fields.Char(
        string="Dirección", related="destinatario_partner_id.street")
    destinatario_ubigeo = fields.Char(
        string="Ubigeo", related="destinatario_partner_id.ubigeo")

    proveedor_partner_id = fields.Many2one("res.partner", string="Proveedor")
    proveedor_tipo_documento_identidad = fields.Char(
        string="Tipo de Documento", related="proveedor_partner_id.l10n_latam_identification_type_id.name")
    proveedor_numero_documento_identidad = fields.Char(
        string="Número de Documento", related="proveedor_partner_id.vat")
    proveedor_direccion = fields.Char(
        string="Dirección", related="proveedor_partner_id.street")
    proveedor_ubigeo = fields.Char(
        string="Ubigeo", related="proveedor_partner_id.ubigeo")

    @api.onchange("destinatario_partner_id")
    def _onchange_destinatario_partner(self):

        for record in self:
            record.proveedor_partner_id = False
            # 01 - VENTA
            # 09 - EXPORTACIÓN
            # 19 - TRASLADO A ZONA PRIMARIA
            # 13 - OTROS
            if record.motivo_traslado in ['01', '09', '19', '13']:
                # record.direccion_llegada_id = False
                record.partner_direccion_llegada_id = record.destinatario_partner_id.id
                record.partner_direccion_partida_id = record.company_partner_id.id
            # 04 - TRASLADO ENTRE ESTABLECIMIENTOS DE LA MISMA EMPRESA
            # 18 - TRASLADO A EMISOR ITINERANTE CP
            if record.motivo_traslado in ['04', '18']:
                record.partner_direccion_llegada_id = record.company_partner_id.id
                record.partner_direccion_partida_id = record.company_partner_id.id
            # 08-EXPORTACIÓN
            if record.motivo_traslado in ['09']:
                record.partner_direccion_partida_id = record.company_partner_id.id
                record.direccion_llegada_id = False
                record.partner_direccion_llegada_id = record.destinatario_partner_id.id
            # 08-IMPORTACIÓN
            if record.motivo_traslado in ['08']:
                record.partner_direccion_partida_id = record.proveedor_partner_id.id
                record.direccion_llegada_id = False
                record.partner_direccion_llegada_id = record.destinatario_partner_id.id

    @api.onchange("proveedor_partner_id")
    def _onchange_proveedor_partner(self):
        for record in self:
            # record.destinatario_partner_id = False
            # 02-COMPRA
            if record.motivo_traslado in ['02']:
                record.direccion_partida_id = False
                record.partner_direccion_llegada_id = record.company_partner_id.id
                record.partner_direccion_partida_id = record.proveedor_partner_id.id
            # 08-IMPORTACIÓN
            if record.motivo_traslado in ['08']:
                record.direccion_partida_id = False
                record.partner_direccion_partida_id = record.proveedor_partner_id.id
                record.partner_direccion_llegada_id = record.destinatario_partner_id.id

    # DOCUMENTOS ASOCIADOS
    documento_asociado = fields.Selection(selection=[("comprobante_pago", "Factura/Boleta"),
                                                     ("orden_venta", "Venta"),
                                                     ("movimiento_stock", "Movimiento de Stock")],
                                          string="Documento Asociado", default="movimiento_stock")

    comprobante_pago_ids = fields.Many2many(
        "account.move", string="Comprobante de Pagos")

    movimiento_stock_ids = fields.Many2many(
        "stock.picking", string="Movimientos", states={'validado': [('readonly', True)]})

    sale_order_ids = fields.Many2many("sale.order", string="Ventas", states={
                                      'validado': [('readonly', True)]})


    @api.onchange("movimiento_stock_ids")
    def _onchange_movimiento_stock(self):
        for record in self:
            guia_remision_lines = []
            guia_remision_lines_temp = {}
            ids = []

            if record.documento_asociado == "movimiento_stock":
                record.guia_remision_line_ids = [(6, 0, [])]
                for movimiento_stock_id in record.movimiento_stock_ids:
                    for move_lines in movimiento_stock_id.move_ids_without_package:
                        guia_remision_lines += [{
                                                "product_id": mls.product_id.id,
                                                "description": mls.product_id.name,
                                                "qty": mls.quantity_done,
                                                "uom_id": mls.product_uom.id,
                                                "stock_picking_id": movimiento_stock_id.id,
                                                } for mls in move_lines]
                index = 0
                for line in guia_remision_lines:
                    if (line["product_id"], line["uom_id"]) not in list(map(lambda x: (guia_remision_lines_temp[x]['product_id'], guia_remision_lines_temp[x]['uom_id']), guia_remision_lines_temp)):
                        guia_remision_lines_temp[index] = line
                    else:
                        product_index = list(filter(lambda x: (guia_remision_lines_temp[x]['product_id'], guia_remision_lines_temp[x]['uom_id']) == (
                            line["product_id"], line["uom_id"]), guia_remision_lines_temp))
                        guia_remision_lines_temp[product_index[0]]["qty"] += line["qty"]
                    index += 1

                guia_remision_lines = list(guia_remision_lines_temp.values())
                record.guia_remision_line_ids = [(0, 0, grl) for grl in guia_remision_lines]

    @api.onchange("comprobante_pago_ids")
    def _onchange_comprobante_pago(self):
        for record in self:
            guia_remision_lines = []
            guia_remision_lines_temp = {}

            if record.documento_asociado == "comprobante_pago":
                record.guia_remision_line_ids = [(6, 0, [])]
                for comprobante_pago in record.comprobante_pago_ids:
                    guia_remision_lines += [{
                                            "product_id": inv_line.product_id.id,
                                            "description": inv_line.name,
                                            "qty": inv_line.quantity,
                                            "uom_id": inv_line.product_uom_id.id,
                                            "stock_picking_id": False,
                                            } for inv_line in comprobante_pago.invoice_line_ids]

                index = 0
                for line in guia_remision_lines:
                    if (line["product_id"], line["uom_id"]) not in list(map(lambda x: (guia_remision_lines_temp[x]['product_id'], guia_remision_lines_temp[x]['uom_id']), guia_remision_lines_temp)):
                        guia_remision_lines_temp[index] = line
                    else:
                        product_index = list(filter(lambda x: (guia_remision_lines_temp[x]['product_id'], guia_remision_lines_temp[x]['uom_id']) == (
                            line["product_id"], line["uom_id"]), guia_remision_lines_temp))
                        guia_remision_lines_temp[product_index[0]]["qty"] += line["qty"]
                    index += 1

                guia_remision_lines = list(guia_remision_lines_temp.values())
                record.guia_remision_line_ids = [(0, 0, grl) for grl in guia_remision_lines]

    @api.onchange("sale_order_ids")
    def _onchange_sale_orders(self):
        for record in self:
            guia_remision_lines = []
            guia_remision_lines_temp = {}
            if record.documento_asociado == "orden_venta":
                record.guia_remision_line_ids = [(6, 0, [])]
                for sale_order in record.sale_order_ids:
                    guia_remision_lines += [{
                        "product_id": line.product_id.id,
                        "description": line.name,
                        "qty": line.product_uom_qty,
                        "uom_id": line.product_uom.id,
                        "stock_picking_id": False
                    } for line in sale_order.order_line]
                index = 0
                for line in guia_remision_lines:
                    if (line["product_id"], line["uom_id"]) not in list(map(lambda x: (guia_remision_lines_temp[x]['product_id'], guia_remision_lines_temp[x]['uom_id']), guia_remision_lines_temp)):
                        guia_remision_lines_temp[index] = line
                    else:
                        product_index = list(filter(lambda x: (guia_remision_lines_temp[x]['product_id'], guia_remision_lines_temp[x]['uom_id']) == (
                            line["product_id"], line["uom_id"]), guia_remision_lines_temp))
                        guia_remision_lines_temp[product_index[0]]["qty"] += line["qty"]
                    index += 1

                guia_remision_lines = list(guia_remision_lines_temp.values())
                record.guia_remision_line_ids = [(0, 0, grl) for grl in guia_remision_lines]

    # @api.depends("guia_remision_line_ids")
    def compute_peso_bruto(self):
        self.peso_bruto_total = sum([line.product_id.weight*line.qty*(line.uom_id.factor_inv /
                                                                      line.product_id.uom_id.factor_inv) for line in self.guia_remision_line_ids])

    # ENVÍO
    fecha_emision = fields.Date(string="Fecha de Emisión", states={
                                'validado': [('readonly', True)]},copy=False,default=lambda r:datetime.today())
    fecha_inicio_traslado = fields.Date(string="Fecha inicio de traslado", states={
                                        'validado': [('readonly', True)]},copy=False,default=lambda r:datetime.today())

    peso_bruto_total = fields.Float(string="Peso Bruto Total (KGM)", states={
                                    'validado': [('readonly', True)]}, default=0.0)
    calc_peso = fields.Boolean(
        string="Calc peso", related="company_id.calc_peso")

    # Campos de Antigua Forma de transporte borrar en el futuro
    modalidad_transporte = fields.Selection(
        selection="_list_modalidad_transporte", string="Modalidad de Transporte")

    def _list_modalidad_transporte(self):
        modalidad_transporte_objs = self.env["gestionit.modalidad_transporte"].search([
        ])
        return [(mt.code, mt.name) for mt in modalidad_transporte_objs]
    # *************************************************************


    numero_bultos = fields.Integer(string="Número de Bultos", states={
                                   'validado': [('readonly', True)]})

    # Campos de Antigua Forma de transporte borrar en el futuro
    partner_direccion_partida_id = fields.Many2one("res.partner")
    direccion_partida_id = fields.Many2one(
        "res.partner", states={'validado': [('readonly', True)]})
    lugar_partida_direccion = fields.Char(
        string="Lugar de Partida - Dirección")
    lugar_partida_ubigeo_code = fields.Many2one(
        "res.country.state", string="Partida Ubigeo Code")
    # *************************************************************

    @api.onchange("direccion_partida_id")
    def _onchange_direccion_partida(self):
        for record in self:
            record.lugar_partida_direccion = record.direccion_partida_id.street
            record.lugar_partida_ubigeo_code = record.direccion_partida_id.district_id.id

    # Campos de Antigua Forma de transporte borrar en el futuro
    partner_direccion_llegada_id = fields.Many2one("res.partner")
    direccion_llegada_id = fields.Many2one(
        "res.partner", states={'validado': [('readonly', True)]})
    lugar_llegada_direccion = fields.Char(
        string="Lugar de llegada - Dirección")
    lugar_llegada_ubigeo_code = fields.Many2one(
        "res.country.state", string="Llegada Ubigeo Code")
    # *************************************************************

    @api.onchange("direccion_llegada_id")
    def _onchange_direccion_llegada(self):
        for record in self:
            record.lugar_llegada_direccion = record.direccion_llegada_id.street
            record.lugar_llegada_ubigeo_code = record.direccion_llegada_id.district_id.id

    # DETALLE DE ENVÍO
    guia_remision_line_ids = fields.One2many("gestionit.guia_remision_line", "guia_remision_id",
                                             string="Detalle de líneas",
                                             ondelete='cascade', states={'validado': [('readonly', True)]})

    # Campos de Antigua Forma de transporte borrar en el futuro
    # TRANSPORTE PRIVADO
    conductor_privado_partner_id = fields.Many2one(
        "res.partner", string="Conductor", states={'validado': [('readonly', True)]})
    vehiculo_privado_id = fields. Many2one(
        "gestionit.vehiculo", string="Vehículo", states={'validado': [('readonly', True)]})

    # TRANSPORTE PÚBLICO
    transporte_partner_id = fields.Many2one(
        "res.partner", string="Empresa Transportista", states={'validado': [('readonly', True)]})
    conductor_publico_id = fields.Many2one("res.partner", string="Conductor", states={
                                           'validado': [('readonly', True)]})
    vehiculo_publico_id = fields.Many2one(
        "gestionit.vehiculo", string="Vehículo", states={'validado': [('readonly', True)]})
    # *************************************************************

    state = fields.Selection(
        selection=[('borrador', 'Borrador'), ('validado', 'Validado')], default="borrador")
    digest_value = fields.Char("DigestValue")
    estado_emision = fields.Selection(
        selection=[
            ('B', 'Borrador'),
            ('A', 'Aceptado'),
            ('E', 'Enviado a SUNAT'),
            ('N', 'Envio Erróneo'),
            ('O', 'Aceptado con Observación'),
            ('R', 'Rechazado'),
            ('P', 'Pendiente de envió a SUNAT'),
        ],
        related="current_log_status_id.status",
        string="Estado Emisión a SUNAT"
    )

    def set_view_lugar_partida_ubigeo(self):

        return {
            'name': 'Lugar de Partida de Ubigeo',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[self.env.ref("gestionit_pe_fe.view_popup_form_seleccion_ubigeo").id, "form"]],
            'res_model': 'gestionit.popup_form_seleccion_ubigeo',
            'target': 'new',
            'context': {
                    "default_guia_remision_id": self.id,
                    "default_tipo_lugar": "partida",
            }
        }

    def set_view_lugar_llegada_ubigeo(self):
        return {
            'name': 'Lugar de llegada de Ubigeo',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[self.env.ref("gestionit_pe_fe.view_popup_form_seleccion_ubigeo").id, "form"]],
            'res_model': 'gestionit.popup_form_seleccion_ubigeo',
            'target': 'new',
            'context': {
                    "default_guia_remision_id": self.id,
                    "default_tipo_lugar": "llegada",
            }
        }


    def validar_datos_compania(self):
        errors = []
        if not self.company_id.partner_id.vat:
            errors.append(
                "* No se tiene configurado el RUC de la empresa emisora.")
        elif not patron_ruc.match(self.company_id.partner_id.vat):
            errors.append(
                "* El RUC de la empresa emisora no tiene el formato de RUC.")

        if not self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
            errors.append(
                "* No se tiene configurado el tipo de documento de la empresa emisora")
        elif self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != '6':
            errors.append(
                "* El Tipo de Documento de la empresa emisora debe ser RUC")
        if not self.company_id.partner_id.ubigeo:
            errors.append(
                "* No se encuentra configurado el Ubigeo de la empresa emisora.")
        if not self.company_id.partner_id.street:
            errors.append(
                "* No se encuentra configurado la dirección de la empresa emisora.")
        if not self.company_id.partner_id.name:
            errors.append(
                "* No se encuentra configurado la Razón Social de la empresa emisora.")
        return errors

    def validar_datos_destinatario(self):
        errors = []
        partner = self.destinatario_partner_id
        if not partner.l10n_latam_identification_type_id.l10n_pe_vat_code:
            errors.append(
                "* El tipo de Documento del destinatario es obligatorio")
        else:
            if partner.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
                if not partner.vat:
                    errors.append(
                        "* El Número de documento del destinatario esta vacío.")
                elif not patron_ruc.match(partner.vat):
                    errors.append(
                        "* El Número de documento del destinatario tiene un RUC inválido.")
            elif partner.l10n_latam_identification_type_id.l10n_pe_vat_code == "1":
                if not partner.vat:
                    errors.append(
                        "* El Número de documento del destinatario esta vacío.")
                elif not patron_dni.match(partner.vat):
                    errors.append(
                        "* El Número de documento del destinatario tiene un DNI inválido.")
            elif partner.l10n_latam_identification_type_id.l10n_pe_vat_code in ("0","4","7"):
                if not partner.vat:
                    errors.append(
                        "* El Número de documento del destinatario esta vacío.")
            else:
                errors.append(
                    "* El tipo de Documento del Destinatario no es válido, seleccion un RUC, DNI ")

        if not partner.name:
            errors.append(
                "* El nombre o razón social del destinatario esta vacío.")
        elif len(partner.name) < 3:
            errors.append(
                "* El nombre o razón social del destinatario debe poseer más de 3 carácteres.")
        return errors

    def validar_motivo_traslado(self):
        errors = []
        motivoTraslado = self.motivo_traslado

        if self.motivo_traslado == "08" and self.numero_bultos == 0:
            errors.append(
                "* El número de bulltos o Pallets es mayor a 0 sólo cuando es Importación.")
        elif self.motivo_traslado == "08" and self.numero_bultos < 0:
            errors.append(
                "* El número de bulltos o Pallets no puede ser negativo.")

        if not motivoTraslado:
            errors.append("* El Motivo de Traslado es Obligatorio.")
        motivo_traslado_activos = self.env["gestionit.motivo_traslado"].sudo().search([
            ("active", "=", True)])

        if motivoTraslado not in [mt.code for mt in motivo_traslado_activos]:
            errors.append(
                "* El Motivo de Traslado seleccionado no existe o no esta habilitado. Consulte con el Administrador")
        return errors

    def validar_datos_envio(self):
        errors = []
        if type(self.peso_bruto_total) != float:
            errors.append(
                "* El tipo de dato del Peso Total es {} y debería ser Flotante".format(type(self.peso_bruto_total)))
        elif self.peso_bruto_total == 0:
            errors.append("* El Peso Total debe ser mayor a 0.")

        return errors

    def validar_guia_remision_lineas(self):
        errors = []
        if len(self.guia_remision_line_ids) == 0:
            errors.append(
                "* La guía debe tener al menos un elemento en el detalle de envío.")

        for guia_remision_line in self.guia_remision_line_ids:
            if not guia_remision_line.product_id:
                errors.append(
                    "* El producto de una de las líneas del detalle está vacío.")

            if not guia_remision_line.description:
                errors.append(
                    "* La descripción de una de las líneas del detalle está vacío.")
            elif len(guia_remision_line.description) < 4 or len(guia_remision_line.description) > 250:
                errors.append(
                    "* La longitud de la descripción de un producto debe poseer una longitud mayor a 4 y menor a 250 carácteres.")

            if not guia_remision_line.uom_id:
                errors.append(
                    "* La unidad de medida del producto [{}] esta vacía".format(guia_remision_line.description))
            elif not guia_remision_line.uom_id.code:
                errors.append(
                    "* La unidad de medida del producto [{}] no tiene un código asociado. Comuníquese con su Administrador del Sistema.".format(guia_remision_line.description))
            elif guia_remision_line.uom_id.code not in codigo_unidades_de_medida:
                errors.append("* La unidad de medida [{}] del producto [{}] no esta permitido. Comuníquese con su Administrador del Sistema.".format(
                    guia_remision_line.uom_id.code, guia_remision_line.description))

            if guia_remision_line.qty == 0:
                errors.append("La cantidad del producto [{}], debe ser mayor a 0".format(
                    guia_remision_line.description))

        return errors

    def convertir_a_borrador(self):
        for record in self:
            if record.estado_emision in ["A", "O"]:
                raise UserError(
                    "La Guía de remisión ya ha sido emitida y tiene estado de Aceptada.")
            if record.estado_emision in ["R"]:
                raise UserError(
                    "La Guía de remisión ya ha sido emitida y tiene estado de Rechazada.")
            # record.estado_emision = "B"
            record.state = "borrador"
            record.numero = "Guía de Remisión Electrónica"

    def generar_comprobante_json(self):
        if not self.name:
            serie = self.journal_id.code
            next_number = self.journal_id.sequence_number_next
            numero = serie + "-" + str(next_number).zfill(8)
            if self.estado_emision in ["A", "O"]:
                raise UserError(
                    "La Guía de Remisión ya ha sido emitida y tiene estado de Aceptada.")
            if self.estado_emision in ["R"]:
                raise UserError(
                    "La Guía de Remisión ya ha sido emitida y tiene estado de Rechazada.")
            if not next_number or not re.match('[T]\d{3}[-]\d{1,8}$', str(numero)):
                raise UserError(
                    "El codigo no tiene el formato correcto: " + str(numero))
        else:
            numero = self.name
            if not re.match('[T]\d{3}[-]\d{1,8}$', str(self.name)):
                raise UserError(
                    "El codigo no tiene el formato correcto: " + str(self.name))
            else:
                serie = self.name.split("-")[0]
                correlativo = self.name.split("-")[1]

        serie, correlativo = numero.split('-')
        correlativo = int(correlativo)
        company = self.company_id.partner_id
        destinatario = self.destinatario_partner_id
        motivo_traslado_id = self.env["gestionit.motivo_traslado"].sudo().search([('code', '=', self.motivo_traslado)])

        if self.multiple_tramos:
            entregaUbigeo = self.transporte_lines[-1].lugar_llegada_ubigeo_code.code
            entregaDireccion = str(self.transporte_lines[-1].lugar_llegada_direccion or "").strip()[:100]
            salidaUbigeo = self.transporte_lines[0].lugar_partida_ubigeo_code.code
            salidaDireccion = str(self.transporte_lines[0].lugar_partida_direccion or "").strip()[:100]
        else:
            entregaUbigeo = self.lugar_llegada_ubigeo_code.code
            entregaDireccion = str(self.lugar_llegada_direccion or "").strip()[:98]
            salidaUbigeo = self.lugar_partida_ubigeo_code.code
            salidaDireccion = str(self.lugar_partida_direccion or "").strip()[:98]

        documento = {
            "serie": serie,
            "correlativo": correlativo,
            "nombreEmisor": company.name.strip(),
            "tipoDocEmisor": company.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "numDocEmisor": company.vat,
            "tipoDocReceptor": destinatario.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "numDocReceptor": destinatario.vat,
            "nombreReceptor": destinatario.name.strip(),
            "motivoTraslado": self.motivo_traslado,
            "descripcionMotivoTraslado": motivo_traslado_id.name.strip(),
            "transbordoProgramado": False,
            "pesoTotal": round(self.peso_bruto_total, 3),
            "pesoUnidadMedida": "KGM",
            "entregaUbigeo": entregaUbigeo,
            "entregaDireccion": entregaDireccion,
            "salidaUbigeo": salidaUbigeo,
            "salidaDireccion": salidaDireccion,
        }
        if self.numero_bultos > 0:
            documento.update({"numeroBulltosPallets": self.numero_bultos})

        detalle = []

        for guia_remision_line in self.guia_remision_line_ids:
            detalle.append(
                {
                    "cantidadItem": guia_remision_line.qty,
                    "nombreItem": guia_remision_line.description.strip(),
                    "unidadMedidaItem": guia_remision_line.uom_id.code,
                    "codItem": str(guia_remision_line.product_id.id)
                }
            )

        transportes = []
        if not self.multiple_tramos:
            if self.modalidad_transporte == '01':
                transporte = {
                    "numDocTransportista": self.transporte_partner_id.vat,
                    "tipoDocTransportista": self.transporte_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
                    "fechaInicioTraslado": str(self.fecha_inicio_traslado),
                    "nombreTransportista": self.transporte_partner_id.name.strip(),
                    "modoTraslado": self.modalidad_transporte
                }
                if self.vehiculo_publico_id:
                    if self.vehiculo_publico_id.numero_placa:
                        transporte.update(
                            {"placaVehiculo": self.vehiculo_publico_id.numero_placa})
                if self.conductor_publico_id:
                    if self.conductor_publico_id.vat:
                        transporte.update(
                            {"numDocConductor": self.conductor_publico_id.vat})
                    if self.conductor_publico_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
                        transporte.update(
                            {"tipoDocConductor": self.conductor_publico_id.l10n_latam_identification_type_id.l10n_pe_vat_code})

                transportes.append(transporte)
            # Transporte Privado
            elif self.modalidad_transporte == "02":
                transportes.append({
                    "numDocConductor": self.conductor_privado_partner_id.vat,
                    "tipoDocConductor": self.conductor_privado_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
                    "fechaInicioTraslado": str(self.fecha_inicio_traslado),
                    "placaVehiculo": self.vehiculo_privado_id.numero_placa,
                    "modoTraslado": self.modalidad_transporte
                })
        else:
            for line in self.transporte_lines:
                # Transporte Público
                if line.modalidad_transporte == '01':
                    transporte = {
                        "numDocTransportista": line.transporte_partner_id.vat,
                        "tipoDocTransportista": line.transporte_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
                        "fechaInicioTraslado": str(line.date),
                        "nombreTransportista": line.transporte_partner_id.name.strip(),
                        "modoTraslado": line.modalidad_transporte
                    }
                    if line.vehiculo_publico_id:
                        if line.vehiculo_publico_id.numero_placa:
                            transporte.update(
                                {"placaVehiculo": line.vehiculo_publico_id.numero_placa})
                    if line.conductor_publico_id:
                        if line.conductor_publico_id.vat:
                            transporte.update(
                                {"numDocConductor": line.conductor_publico_id.vat})
                        if line.conductor_publico_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
                            transporte.update(
                                {"tipoDocConductor": line.conductor_publico_id.l10n_latam_identification_type_id.l10n_pe_vat_code})

                    transportes.append(transporte)
                # Transporte Privado
                elif line.modalidad_transporte == "02":
                    transportes.append({
                        "numDocConductor": line.conductor_privado_partner_id.vat,
                        "tipoDocConductor": line.conductor_privado_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
                        "fechaInicioTraslado": str(line.date),
                        "placaVehiculo": line.vehiculo_privado_id.numero_placa,
                        "modoTraslado": line.modalidad_transporte
                    })

        nombreEmisor = self.company_id.partner_id.registration_name.strip()
        numDocEmisor = self.company_id.partner_id.vat.strip(
        ) if self.company_id.partner_id.vat else ""
        data = {
            "company": {
                "numDocEmisor": numDocEmisor,
                "nombreEmisor": nombreEmisor,
                "SUNAT_user": self.company_id.sunat_user,
                "SUNAT_pass": self.company_id.sunat_pass,
                "key_private": self.company_id.cert_id.key_private,
                "key_public": self.company_id.cert_id.key_public,
            },
            "tipoEnvio": int(self.company_id.tipo_envio),
            "tipoDocumento": "09",
            "transportes": transportes,
            "detalle": detalle,
            "documento": documento,
            "fechaEmision": str(self.fecha_emision)
        }
        return data
    
    def validar_lugar_partida(self):
        errors = []
        if not self.lugar_partida_direccion:
            errors.append(
                "* La dirección del lugar de partida es obligatorio.")
        elif len(self.lugar_partida_direccion) < 6 and len(self.lugar_partida_direccion) >= 100:
            errors.append(
                "* La dirección del lugar de partida tiene como mínimo 6 carácteres.")

        if not self.lugar_partida_ubigeo_code:
            errors.append("* El ubigeo del lugar de partida es obligatorio.")
        elif not self.validar_ubigeo(self.lugar_partida_ubigeo_code.code):
            errors.append("* El ubigeo de la dirección de partida no existe.")

        return errors

    def validar_ubigeo(self, ubigeo):
        ubigeo_objs = self.env["res.country.state"].sudo().search(
            [("code", "=", ubigeo)])
        if ubigeo_objs.exists():
            return True
        else:
            return False

    def validar_lugar_llegada(self):
        errors = []
        if not self.lugar_llegada_direccion:
            errors.append(
                "* La dirección del lugar de llegada es obligatorio.")
        elif len(self.lugar_llegada_direccion) < 6 and len(self.lugar_llegada_direccion) >= 100:
            errors.append(
                "* La dirección del lugar de llegada tiene como mínimo 6 carácteres.")

        if not self.lugar_llegada_ubigeo_code:
            errors.append("* El ubigeo del lugar de llegada es obligatorio.")
        elif not self.validar_ubigeo(self.lugar_llegada_ubigeo_code.code):
            errors.append("* El ubigeo de la dirección de llegada no existe.")

        return errors

    def validar_transporte(self):
        errors = []
        if not self.modalidad_transporte:
            errors.append(
                "* La modalidad de transporte no ha sido seleccionado.")
        elif self.modalidad_transporte not in ["01", "02"]:
            errors.append(
                "* La modalidad de transporte seleccionado es incorrecto. Las modalidades de transporte permitidos son 01 - Transporte Público y 02 - Transporte Privado")

        if self.modalidad_transporte == "01":
            if not self.transporte_partner_id:
                errors.append(
                    "* Debe seleccionar una Empresa de Transporte público.")
            else:
                if not self.transporte_partner_id.name:
                    errors.append(
                        "* La empresa de transporte seleccionado no tiene Nombre o Razón Social.")
                elif len(self.transporte_partner_id.name) < 4:
                    errors.append(
                        "* El nombre de la empresa de transporte seleccionada debe tener como mínimo 4 carácteres.")

                if not self.transporte_partner_id.vat:
                    errors.append(
                        "* La empresa de transporte seleccionado no tiene documento.")
                elif not patron_ruc.match(self.transporte_partner_id.vat):
                    errors.append(
                        "* El RUC de la empresa de transporte seleccionada tiene un formato incorrecto.")

                if not self.transporte_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
                    errors.append(
                        "* La empresa de transporte seleccionado no tiene tipo de documento.")
                elif not self.transporte_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
                    errors.append(
                        "* El tipo de documento de la empresa de transporte seleccionada debe ser de tipo 'RUC'")

                if not self.fecha_inicio_traslado:
                    errors.append(
                        "* La fecha de inicio de traslado es obligatorio.")
                """
                if not self.conductor_publico_id:
                    errors.append("* El Conductor público de la empresa es obligatorio.")
                elif not self.conductor_publico_id.tipo_documento:
                    errors.append("* El Conductor público seleccionado no tiene tipo de documento de identidad.")
                elif not self.conductor_publico_id.vat:
                    errors.append("* El Conductor público seleccionado no tiene número de documento de identidad.")
                """
        elif self.modalidad_transporte == "02":
            if not self.conductor_privado_partner_id:
                errors.append("* Debe seleccionar un conductor privado.")
            else:
                if not self.conductor_privado_partner_id.name:
                    errors.append(
                        "* El conductor privado seleccionado no tiene Nombre.")
                elif len(self.conductor_privado_partner_id.name) < 4:
                    errors.append(
                        "* El nombre del conductor privado seleccionado debe tener más de 4 carácteres")

                if not self.conductor_privado_partner_id.vat:
                    errors.append(
                        "* El conductor privado seleccionado no tiene documento.")
                if not self.conductor_privado_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
                    errors.append(
                        "* La conductor privado seleccionado no tiene tipo de documento.")

                if not self.fecha_inicio_traslado:
                    errors.append(
                        "* La fecha de inicio de traslado es obligatorio")

            if not self.vehiculo_privado_id:
                errors.append("* El Vehículo privado es Obligatorio.")
            elif not self.vehiculo_privado_id.numero_placa:
                errors.append(
                    "* El Vehículo pivado seleccionado no tiene Número de Placa")

        return errors

    def validar_restricciones(self):
        errors = []
        errors += self.validar_datos_compania()
        errors += self.validar_datos_destinatario()
        errors += self.validar_motivo_traslado()
        errors += self.validar_datos_envio()
        errors += self.validar_guia_remision_lineas()

        if self.multiple_tramos:
            if not self.transporte_lines:
                errors.append("* Es Necesario declarar al menos un tramo de transporte.")
            else:
                for line in self.transporte_lines:
                    errors += line.validar_lugar_partida()
                    errors += line.validar_lugar_llegada()
                    errors += line.validar_transporte()
        else:
            errors += self.validar_lugar_partida()
            errors += self.validar_lugar_llegada()
            errors += self.validar_transporte()

        if len(errors) > 0:
            return {
                'error': True,
                'name': 'ERROR: Validación de campos',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'custom.pop.message',
                'target': 'new',
                'context': {
                    'default_name': "Error al validar datos de la compania:",
                    'default_accion': '\n'.join(errors)
                }
            }
        return False

    def validar_comprobante(self):
        if self.name == "" or self.name == False:
            serie = self.journal_id.code
            next_number = self.journal_id.sequence_number_next
            numero = serie + "-" + str(next_number).zfill(8)
            # _logger.info(self.env["gestionit.guia_remision"].search([("numero", "=", numero), ("state", '=', 'validado')]))
            if self.env["gestionit.guia_remision"].search([("numero", "=", numero), ("state", '=', 'validado')]).exists():
                raise UserError(
                    "El documento de guía de remisión ya existe 1.")
            self.state = "validado"
            self.numero = self.journal_id.sequence_id.next_by_id()
            self.name = self.numero
        else:
            if self.env["gestionit.guia_remision"].search([("numero", "=", self.name), ("state", '=', 'validado')]).exists():
                raise UserError(
                    "El documento de guía de remisión ya existe 2.")
            self.numero = self.name
            self.state = "validado"

    def generar_log_envio(self):
        data = self.generar_comprobante_json()
        self.request_json = json.dumps(data, indent=4)
        credentials = {
            "ruc": data["company"]["numDocEmisor"],
            'razon_social': data["company"]["nombreEmisor"],
            'usuario': data["company"]["SUNAT_user"],
            'password': data["company"]["SUNAT_pass"],
            'key_private': data["company"]["key_private"],
            'key_public': data["company"]["key_public"],
        }
        request = main.handle(data, credentials)
        log_status = {
            "guia_remision_id": self.id,
            "request_json": self.request_json,
            "name": self.name,
            "date_request": fields.Datetime.now(),
            "date_issue": self.fecha_emision,
            "status": "P",
            "digest_value": request.get("digest_value", "-"),
            "signed_xml_data": request.get("signed_xml", "-"),
            "signed_xml_with_creds": parseString(request.get("final_xml")).toprettyxml(" ") if request.get("final_xml", False) else "",
            "company_id": self.company_id.id
        }
        log_status_obj = self.env["account.log.status"].sudo().create(
            log_status)
        log_status_obj.sudo().action_set_last_log()

    def send_gr_xml(self):
        if not self.current_log_status_id:
            self.generar_log_envio()
        try:
            result = send_doc_xml(self)
            self.current_log_status_id.write(result)
        except Exception as e:
            return result

    # Valida y registra la guía de remisión

    def post(self):
        errors = self.validar_restricciones()
        if errors:
            return errors
        self.validar_comprobante()
        self.generar_log_envio()
        if self.journal_id.send_async:
            self.send_gr_xml()

    def btn_validar_comprobante(self):
        if self.state == "validado":
            raise UserError("La Guía de remisión ya ha sido validada.")
        doc_json = self.generar_comprobante_json()
        if "error" in doc_json:
            return doc_json
        else:
            # _logger.info(doc_json)
            self.request_json = json.dumps(doc_json, indent=4)
        self.validar_comprobante()
        return self.enviar_comprobante()

    # @api.multi

    def unlink(self):
        l = []
        for record in self:
            if record.state == "validado" or record.name:
                if record.name:
                    l.append(record.name)
                else:
                    l.append("Guía de Remisión Remitente "+str(record.id))

        if len(l) > 0:
            raise UserError(
                "No es posible eliminar una guía de remisión Validada o que tenga un número asignado. [{}]".format(",".join(l)))

        for record in self:
            result = super(GuiaRemision, record).unlink()

        return True

    def cron_enviar_comprobante(self, cantidad):
        guia_remision_ids = self.env["gestionit.guia_remision"].search(
            [("estado_emision", "in", ["P", False]), ("request_json", "!=", False)], limit=cantidad)
        for gr in guia_remision_ids:
            try:
                gr.send_gr_xml()
                self.env.cr.commit()
            except Exception as e:
                pass
        return True

    def btn_enviar_comprobante(self):
        for record in self:
            record.enviar_comprobante()
            if record.estado_emision in ["P", "B", False] and record.request_json:
                if len(self) == 1:
                    return record.enviar_comprobante()
                else:
                    record.enviar_comprobante()

    def enviar_comprobante(self):

        data = json.loads(self.request_json)

        log_status = {
            "request_json": self.request_json,
            "guia_remision_id": self.id,
            "name": self.name,
            "date_request": fields.Datetime.now(),
            "date_issue": self.fecha_emision
        }
        try:
            credentials = {
                "ruc": data["company"]["numDocEmisor"],
                'razon_social': data["company"]["nombreEmisor"],
                'usuario': data["company"]["SUNAT_user"],
                'password': data["company"]["SUNAT_pass"],
                'key_private': data["company"]["key_private"],
                'key_public': data["company"]["key_public"],
            }
            response = main.handle(data, credentials)
            # _logger.info("R json")
            # _logger.info(response)
            # self.response_json = json.dumps(r.json(), indent=4)
            self.response_json = json.dumps(response, indent=4)
            log_status.update({
                "response_json": self.response_json,
            })
            # if response:
            #     if "errors" not in response:
            #         if "signed_xml" in response:
            #             log_status.update(
            #                 {"signed_xml_data": response["signed_xml"]})
            #         if "request_id" in response:
            #             log_status.update(
            #                 {"api_request_id": response["request_id"]})
            #         if "digest_value" in response:
            #             self.digest_value = response["digest_value"]
            #             log_status.update(
            #                 {"digest_value": response["digest_value"]})
            #         if "response_xml" in response:
            #             log_status.update(
            #                 {"response_xml": response["response_xml"]})
            #         if "response_content_xml" in response:
            #             log_status.update(
            #                 {"content_xml": response["response_content_xml"]})
            #         if "sunat_status" in response:
            #             self.estado_emision = response["sunat_status"]
            #             log_status.update(
            #                 {"status": response["sunat_status"]})

        except Timeout as e:
            self.estado_emision = "P"
            return {
                'name': 'Tiempo de espera excedido',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'custom.pop.message',
                'target': 'new',
                'context': {
                        'default_name': "Alerta",
                        'default_accion': "* La guía de remisión ha sido generada de forma exitosa.\n* El tiempo de espera de la respuesta ha sido excedida.\n* El comprobante se enviará de forma automática luego"

                }
            }
        except ConnectionError as e:
            self.estado_emision = "P"
            return {
                'name': 'Error en la conexión',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'custom.pop.message',
                'target': 'new',
                'context': {
                        'default_name': "Alerta",
                        'default_accion': "* La guía de remisión ha sido generada de forma exitosa.\n* No se ha logrado enviar el comprobante.\n* Se intentará enviar luego de forma automática."
                }
            }
        except Exception as e:
            raise
            self.estado_emision = "P"
            return {
                'name': 'Error',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'custom.pop.message',
                'target': 'new',
                'context': {
                        'default_name': "Alerta",
                        'default_accion': "* La guía de remisión ha sido generada de forma exitosa.\n* "+str(e)
                }
            }
        finally:
            self.env["account.log.status"].sudo().create(log_status)

    def btn_view_log_guia_remision(self):
        return {
            'name': "Sunat Log - Guía de Remisión ",
            'type': "ir.actions.act_window",
            'view_mode': 'tree,form',
            'domain': [("guia_remision_id", "=", self.id)],
            'res_model': 'account.log.status',
            'target': 'self'
        }

class AccountInvoiceGuiaRemision(models.Model):
    _inherit = "account.move"

    def btn_crear_guia_remision(self):
        pass

class ResCompany(models.Model):
    _inherit = 'res.company'

    calc_peso = fields.Boolean(string="Calcular peso")

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    calc_peso = fields.Boolean(
        string="Calcular peso automáticamente", related="company_id.calc_peso", readonly=False)

class LineasTransporte(models.Model):
    _name = 'gestionit.lineas_transporte'
    _description = 'Lineas para descripcion de Tramos de envio'


    guia_id = fields.Many2one('gestionit.guia_remision', 'Guia Base')
    secuencia = fields.Integer('Secuencia')
    transporte_partner_id = fields.Many2one("res.partner", string="Empresa Transportista", required=False)
    ruc_trasporte_partner = fields.Char('RUC Transportista', related='transporte_partner_id.vat')
    date = fields.Date('Fecha', required=True, default=fields.Date.context_today)
    modalidad_transporte = fields.Selection(selection="_list_modalidad_transporte", string="Modalidad de Transporte", required=True)
    partner_direccion_partida_id = fields.Many2one("res.partner")
    direccion_partida_id = fields.Many2one("res.partner")
    lugar_partida_direccion = fields.Char(string="Lugar de Partida - Dirección")
    lugar_partida_ubigeo_code = fields.Many2one("res.country.state", string="Partida Ubigeo Code")
    partner_direccion_llegada_id = fields.Many2one("res.partner")
    direccion_llegada_id = fields.Many2one("res.partner")
    lugar_llegada_direccion = fields.Char(string="Lugar de llegada - Dirección")
    lugar_llegada_ubigeo_code = fields.Many2one("res.country.state", string="Llegada Ubigeo Code")
    conductor_privado_partner_id = fields.Many2one("res.partner", string="Conductor")
    vehiculo_privado_id = fields. Many2one("gestionit.vehiculo", string="Vehículo")
    conductor_publico_id = fields.Many2one("res.partner", string="Conductor")
    vehiculo_publico_id = fields.Many2one("gestionit.vehiculo", string="Vehículo")
    licencia = fields.Char('Licencia', compute='_get_licencia', readonly=True)

    @api.onchange("conductor_publico_id", "conductor_privado_partner_id")
    def _get_licencia(self):
        for record in self:
            if record.modalidad_transporte == '01':
                record.licencia = record.conductor_publico_id.licencia
            elif record.modalidad_transporte == '02':
                record.licencia = record.conductor_privado_partner_id.licencia
            else:
                record.licencia = ''

    @api.onchange("partner_direccion_partida_id")
    def _onchange_partner_direccion_partida_id(self):
        self.direccion_partida_id = False
        self.lugar_partida_direccion = ''
        self.lugar_partida_ubigeo_code = False

    @api.onchange("partner_direccion_llegada_id")
    def _onchange_partner_direccion_llegada_id(self):
        self.direccion_llegada_id = False
        self.lugar_llegada_direccion = ''
        self.lugar_llegada_ubigeo_code = False

    @api.onchange("modalidad_transporte")
    def _onchange_modalidad_transporte(self):
        if self.modalidad_transporte == '01':
            if self.transporte_partner_id:
                self.partner_direccion_partida_id = self.transporte_partner_id.id
            else:
                self.partner_direccion_partida_id = False
        elif self.modalidad_transporte == '02':
            self.partner_direccion_partida_id = self.env.company.id
        else:
            self.partner_direccion_partida_id = False


    @api.onchange("direccion_partida_id")
    def _onchange_direccion_partida(self):
        for record in self:
            record.lugar_partida_direccion = record.direccion_partida_id.street
            record.lugar_partida_ubigeo_code = record.direccion_partida_id.district_id.id

    @api.onchange("direccion_llegada_id")
    def _onchange_direccion_llegada(self):
        for record in self:
            record.lugar_llegada_direccion = record.direccion_llegada_id.street
            record.lugar_llegada_ubigeo_code = record.direccion_llegada_id.district_id.id

    def _list_modalidad_transporte(self):
        modalidad_transporte_objs = self.env["gestionit.modalidad_transporte"].search([])
        return [(mt.code, mt.name) for mt in modalidad_transporte_objs]

    def validar_transporte(self):
        errors = []
        if not self.modalidad_transporte:
            errors.append(
                "* La modalidad de transporte no ha sido seleccionado.")
        elif self.modalidad_transporte not in ["01", "02"]:
            errors.append(
                "* La modalidad de transporte seleccionado es incorrecto. Las modalidades de transporte permitidos son 01 - Transporte Público y 02 - Transporte Privado")

        if self.modalidad_transporte == "01":
            if not self.transporte_partner_id:
                errors.append(
                    "* Debe seleccionar una Empresa de Transporte público.")
            else:
                if not self.transporte_partner_id.name:
                    errors.append(
                        "* La empresa de transporte seleccionado no tiene Nombre o Razón Social.")
                elif len(self.transporte_partner_id.name) < 4:
                    errors.append(
                        "* El nombre de la empresa de transporte seleccionada debe tener como mínimo 4 carácteres.")

                if not self.transporte_partner_id.vat:
                    errors.append(
                        "* La empresa de transporte seleccionado no tiene documento.")
                elif not patron_ruc.match(self.transporte_partner_id.vat):
                    errors.append(
                        "* El RUC de la empresa de transporte seleccionada tiene un formato incorrecto.")

                if not self.transporte_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
                    errors.append(
                        "* La empresa de transporte seleccionado no tiene tipo de documento.")
                elif not self.transporte_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code == "6":
                    errors.append(
                        "* El tipo de documento de la empresa de transporte seleccionada debe ser de tipo 'RUC'")

                if not self.date:
                    errors.append(
                        "* La fecha de inicio de traslado es obligatorio.")
                """
                if not self.conductor_publico_id:
                    errors.append("* El Conductor público de la empresa es obligatorio.")
                elif not self.conductor_publico_id.tipo_documento:
                    errors.append("* El Conductor público seleccionado no tiene tipo de documento de identidad.")
                elif not self.conductor_publico_id.vat:
                    errors.append("* El Conductor público seleccionado no tiene número de documento de identidad.")
                """
        elif self.modalidad_transporte == "02":
            if not self.conductor_privado_partner_id:
                errors.append("* Debe seleccionar un conductor privado.")
            else:
                if not self.conductor_privado_partner_id.name:
                    errors.append(
                        "* El conductor privado seleccionado no tiene Nombre.")
                elif len(self.conductor_privado_partner_id.name) < 4:
                    errors.append(
                        "* El nombre del conductor privado seleccionado debe tener más de 4 carácteres")

                if not self.conductor_privado_partner_id.vat:
                    errors.append(
                        "* El conductor privado seleccionado no tiene documento.")
                if not self.conductor_privado_partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code:
                    errors.append(
                        "* La conductor privado seleccionado no tiene tipo de documento.")

                if not self.date:
                    errors.append(
                        "* La fecha de inicio de traslado es obligatorio")

            if not self.vehiculo_privado_id:
                errors.append("* El Vehículo privado es Obligatorio.")
            elif not self.vehiculo_privado_id.numero_placa:
                errors.append(
                    "* El Vehículo pivado seleccionado no tiene Número de Placa")

        return errors

    def validar_lugar_partida(self):
        errors = []
        if not self.lugar_partida_direccion:
            errors.append(
                "* La dirección del lugar de partida es obligatorio.")
        elif len(self.lugar_partida_direccion) < 6 and len(self.lugar_partida_direccion) >= 100:
            errors.append(
                "* La dirección del lugar de partida tiene como mínimo 6 carácteres.")

        if not self.lugar_partida_ubigeo_code:
            errors.append("* El ubigeo del lugar de partida es obligatorio.")
        elif not self.validar_ubigeo(self.lugar_partida_ubigeo_code.code):
            errors.append("* El ubigeo de la dirección de partida no existe.")

        return errors

    def validar_lugar_llegada(self):
        errors = []
        if not self.lugar_llegada_direccion:
            errors.append(
                "* La dirección del lugar de llegada es obligatorio.")
        elif len(self.lugar_llegada_direccion) < 6 and len(self.lugar_llegada_direccion) >= 100:
            errors.append(
                "* La dirección del lugar de llegada tiene como mínimo 6 carácteres.")

        if not self.lugar_llegada_ubigeo_code:
            errors.append("* El ubigeo del lugar de llegada es obligatorio.")
        elif not self.validar_ubigeo(self.lugar_llegada_ubigeo_code.code):
            errors.append("* El ubigeo de la dirección de llegada no existe.")

        return errors

    def validar_ubigeo(self, ubigeo):
        ubigeo_objs = self.env["res.country.state"].sudo().search(
            [("code", "=", ubigeo)])
        if ubigeo_objs.exists():
            return True
        else:
            return False
