import requests
from odoo.exceptions import UserError, ValidationError
import json
import io
import base64
import datetime
from datetime import datetime
from bs4 import BeautifulSoup
from xml.dom import minidom
import time
import re
from odoo import fields
from xml.dom.minidom import parse, parseString
from requests.exceptions import (
    RequestException, Timeout, URLRequired,
    TooManyRedirects, HTTPError, ConnectionError,
    FileModeWarning, ConnectTimeout, ReadTimeout
)
import zipfile
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion.controllers import xml_validation, sunat_response_handle, main,firma
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion import api_models,lista_errores
from odoo.addons.gestionit_pe_fe.models.account.api_facturacion.efact21.Documents import ResumenDiario,Factura
from pytz import timezone

import logging
_logger = logging.getLogger(__name__)

invoice_type_code = {
    "01":"Factura Electrónica",
    "03":"Boleta Electrónica",
    "07":"Nota de Crédito",
    "08":"Nota de Débito"
}
# Pruebas
urls_test = [
    "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService",  # Fact y Resumenes
    "https://e-beta.sunat.gob.pe/ol-ti-itemision-guia-gem-beta/billService",  # Guia
    "https://e-beta.sunat.gob.pe/ol-ti-itemision-otroscpe-gem-beta/billService",  # REte
]

# Produccion
urls_production = [
    "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService",  # Fact y Resumenes
    "https://e-guiaremision.sunat.gob.pe/ol-ti-itemision-guia-gem/billService",  # Guia
    "https://e-factura.sunat.gob.pe/ol-ti-itemision-otroscpe-gem/billService",  # REte
]

#Producción Efact
urls_production_efact = [
    "https://ose.efact.pe/ol-ti-itcpe/billService?wsdl",
    "https://ose.efact.pe/ol-ti-itcpe/billService?wsdl",
    "https://ose.efact.pe/ol-ti-itcpe/billService?wsdl",
]

#Consulta de tickets


def enviar_doc_url(data_doc, tipoEnvio):
    data_doc["tipoEnvio"] = int(tipoEnvio)

    r = api_models.lamdba(data_doc)

    return r


def generate_and_signed_xml(invoice):
    invoice.invoice_type_code = invoice.journal_id.invoice_type_code_id
    request_json = {}
    # request_json = {"tipoEnvio":int(invoice.company_id.tipo_envio)}

    if invoice.invoice_type_code == "01" or invoice.invoice_type_code == "03":
        request_json.update(crear_json_fac_bol(invoice))
    elif invoice.invoice_type_code == "07" or invoice.invoice_type_code == "08":
        request_json.update(crear_json_not_cred_deb(invoice))
    else:
        raise UserError("Tipo de documento no valido")

    credentials = {
        "ruc": request_json["company"]["numDocEmisor"],
        'razon_social': request_json["company"]["nombreEmisor"],
        'usuario': request_json["company"]["SUNAT_user"],
        'password': request_json["company"]["SUNAT_pass"],
        'key_private': request_json["company"]["key_private"],
        'key_public': request_json["company"]["key_public"],
    }

    result = main.handle(request_json,credentials)
    # _logger.info(result)
    if result.get("success"):
        data = {
            "request_json":json.dumps(request_json,indent=4),
            "signed_xml_data_without_format":result.get("signed_xml"),
            "signed_xml_with_creds":result.get("final_xml"),
            "signed_xml_data":parseString(result.get("signed_xml")).toprettyxml(),
            "name":"{} {}".format(invoice_type_code[request_json.get("tipoDocumento")],invoice.name),
            "date_issue":invoice.invoice_date,
            "account_move_id":invoice.id,
            "digest_value":result.get("digest_value"),
            "status":"P",
            "company_id":invoice.company_id.id,
        }
        return data
    else:
        raise UserError(json.dumps(result,indent=4))



def send_summary_xml(doc):
    signed_xml_with_creds = doc.current_log_status_id.signed_xml_with_creds
    tipo_envio = doc.company_id.tipo_envio

    if doc.company_id.sunat_provider == "sunat":
        if int(tipo_envio) == 0:
            endpoint = urls_test[0]

        elif int(tipo_envio) == 1: 
            endpoint = urls_production[0]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 0 - Pruebas , 1- Producción")

    elif doc.company_id.sunat_provider == "efact":
        if int(tipo_envio) == 1: 
            endpoint = urls_production_efact[0]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 1- Producción")

    try:
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        response = requests.post(endpoint,
                                data=signed_xml_with_creds,
                                headers=headers,
                                timeout=20)
        result = sunat_response_handle.get_response_ticket(response.text)
        # _logger.info(result)
        data = {
            "response_json":json.dumps(result,indent=4),
            "summary_submission_response_xml":parseString(response.text).toprettyxml() if response.text else "" ,
            "date_request":fields.Datetime.now(),
            "status":result.get("status"),
            "log_observation_ids":[],
            "summary_ticket":result.get("ticket")
        }
        return data

    except Timeout as e:
        return {
            'name': 'Tiempo de espera excedido',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* El tiempo de espera de la respuesta ha sido excedida.\n* El comprobante se enviará de forma automática luego"
            }
        }
    except ConnectionError as e:
        return {
            'name': 'Error en la conexión',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* No se ha logrado enviar el comprobante.\n* Se intentará enviar luego de forma automática."
            }
        }
    except Exception as e:
        return {
            'name': 'Error',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* "+str(e)
            }
        }

def send_voided_xml(doc):
    signed_xml_with_creds = doc.current_log_status_id.signed_xml_with_creds
    tipo_envio = doc.company_id.tipo_envio

    if doc.company_id.sunat_provider == "sunat":
        if int(tipo_envio) == 0:
            endpoint = urls_test[0]

        elif int(tipo_envio) == 1: 
            endpoint = urls_production[0]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 0 - Pruebas u 1- Producción")
            
    elif doc.company_id.sunat_provider == "efact":
        if int(tipo_envio) == 1: 
            endpoint = urls_production_efact[0]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 1- Producción")

    try:
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        response = requests.post(endpoint,
                                data=signed_xml_with_creds,
                                headers=headers,
                                timeout=20)
        result = sunat_response_handle.get_response_ticket(response.text)
        # _logger.info(result)
        data = {
            "response_json":json.dumps(result,indent=4),
            "voided_submission_response_xml":parseString(response.text).toprettyxml() if response.text else "" ,
            "date_request":fields.Datetime.now(),
            "status":result.get("status"),
            "log_observation_ids":[],
            "voided_ticket":result.get("ticket")
        }
        return data

    except Timeout as e:
        return {
            'name': 'Tiempo de espera excedido',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* El tiempo de espera de la respuesta ha sido excedida.\n* El comprobante se enviará de forma automática luego"
            }
        }
    except ConnectionError as e:
        return {
            'name': 'Error en la conexión',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* No se ha logrado enviar el comprobante.\n* Se intentará enviar luego de forma automática."
            }
        }
    except Exception as e:
        return {
            'name': 'Error',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* "+str(e)
            }
        }


def send_doc_xml(doc):
    signed_xml_with_creds = doc.current_log_status_id.signed_xml_with_creds
    tipo_envio = doc.journal_id.tipo_envio
    invoice_type_code = doc.journal_id.invoice_type_code_id

    if doc.company_id.sunat_provider == "sunat":
        if int(tipo_envio) == 0:
            if invoice_type_code in ["01","03","07","08","RC"]:
                endpoint = urls_test[0]
            elif invoice_type_code == "09":
                endpoint = urls_test[1]
        elif int(tipo_envio) == 1: 
            if invoice_type_code in ["01","03","07","08","RC"]:
                endpoint = urls_production[0]
            elif invoice_type_code == "09":
                endpoint = urls_production[1]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 0 - Pruebas u 1- Producción")

    elif doc.company_id.sunat_provider == "efact":
        if int(tipo_envio) == 1: 
            if invoice_type_code in ["01","03","07","08","RC"]:
                endpoint = urls_production_efact[0]
            elif invoice_type_code == "09":
                endpoint = urls_production_efact[1]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 1- Producción")
    
    _logger.info(endpoint)

    try:
        headers = {"Content-Type": 'text/xml; charset=utf-8'}
        response = requests.post(endpoint,
                                data=signed_xml_with_creds,
                                headers=headers,
                                timeout=20)
        _logger.info(response.text)
        result = sunat_response_handle.get_response(response.text)
        data = {
            "response_json":json.dumps(result,indent=4),
            "response_xml_without_format":response.text,
            "response_content_xml": parseString(result.get("xml_content")).toprettyxml() if result.get("xml_content",False) else "",
            "date_request":fields.Datetime.now(),
            "status":result.get("status"),
            "log_observation_ids":[]
        }
        return data

    except Timeout as e:
        return {
            'name': 'Tiempo de espera excedido',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* El tiempo de espera de la respuesta ha sido excedida.\n* El comprobante se enviará de forma automática luego"
            }
        }
    except ConnectionError as e:
        return {
            'name': 'Error en la conexión',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* No se ha logrado enviar el comprobante.\n* Se intentará enviar luego de forma automática."
            }
        }
    except Exception as e:
        return {
            'name': 'Error',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* "+str(e)
            }
        }
    # finally:
    #     doc.current_log_status_id.status = "P"

# def get_tipo_cambio(self, compra_o_venta=2):  # 1 -> compra , 2->venta
#     ratios = self.currency_id.rate_ids
#     tipo_cambio = 1.0
#     ratio_actual = False
#     for ratio in ratios:
#         if str(ratio.name)[0:10] == str(self.invoice_date):
#             tipo_cambio = ratio.rate
#             ratio_actual = True

#     if ratio_actual:
#         return tipo_cambio
#     else:
#         now = datetime.datetime.now()
#         if self.invoice_date > now.strftime("%Y-%m-%d"):
#             raise ValidationError(
#                 "Fecha de factura no valida, no se puede obtener tipo de cambio de esa fecha")
#         url = "https://www.sbs.gob.pe/app/pp/SISTIP_PORTAL/Paginas/Publicacion/TipoCambioPromedio.aspx"
#         r = requests.get(url)
#         if r.ok:
#             soup = BeautifulSoup(r.text, 'html.parser')
#             tipo_cambio = float(soup.find(id="ctl00_cphContent_rgTipoCambio_ctl00__0").find_all(
#                 'td')[compra_o_venta].string)
#             self.env['res.currency.rate'].create({
#                 'name': now.strftime("%Y-%m-%d"),
#                 'currency_id': self.currency_id.id,
#                 'rate': tipo_cambio
#             })
#             return tipo_cambio
#         else:
#             raise ValidationError("Error al obtener tipo de cambio en SBS")


def crear_json_fac_bol(self):

    if hasattr(self,"is_contingencia"):

        if self.is_contingencia:

            if self.invoice_type_code == '01':
                if not re.match("^\d{4}-\d{1,8}$", self.name):
                    raise UserError("El Formato de la Factura es incorrecto.")
            
            elif self.invoice_type_code == '03':
                if not re.match("^\d{4}-\d{1,8}$", self.name):
                    raise UserError("El Formato de la Boleta es Incorrecto.")
            
            elif self.invoice_type_code == '07':
                if self.reversal_move_id.invoice_type_code == '01':
                    if not re.match("^\d{4}-\d{1,8}$", self.name):
                        raise UserError(
                            "El Formato de la Nota de Crédito para la factura es incorrecto. ")
                if self.reversal_move_id.invoice_type_code == '03':
                    if not re.match("^d\d{4}-\d{1,8}$", self.name):
                        raise UserError(
                            "El Formato de la Nota de Crédito para la Boleta es Incorrecto. ")

            elif self.invoice_type_code == '08':
                if self.reversal_move_id.invoice_type_code == '01':
                    if not re.match("^\d{4}-\d{1,8}$", self.name):
                        raise UserError(
                            "El Formato de la Nota de Débito para la factura es incorrecto. ")
                if self.reversal_move_id.invoice_type_code == '03':
                    if not re.match("^\d{4}-\d{1,8}$", self.name):
                        raise UserError(
                            "El Formato de la Nota de Débito para la Boleta es Incorrecto. ")
            else:
                raise UserError("El Tipo de Documento del Comprobante es Obligatorio")


    else:

        if self.invoice_type_code == '01':
            if not re.match("^F\w{3}-\d{1,8}$", self.name):
                raise UserError("El Formato de la Factura es incorrecto.")
        elif self.invoice_type_code == '03':
            if not re.match("^B\w{3}-\d{1,8}$", self.name):
                raise UserError("El Formato de la Boleta es Incorrecto.")
        elif self.invoice_type_code == '07':
            if self.reversal_move_id.invoice_type_code == '01':
                if not re.match("^F\w{3}-\d{1,8}$", self.name):
                    raise UserError(
                        "El Formato de la Nota de Crédito para la factura es incorrecto. ")
            if self.reversal_move_id.invoice_type_code == '03':
                if not re.match("^B\w{3}-\d{1,8}$", self.name):
                    raise UserError(
                        "El Formato de la Nota de Crédito para la Boleta es Incorrecto. ")
        elif self.invoice_type_code == '08':
            if self.reversal_move_id.invoice_type_code == '01':
                if not re.match("^F\w{3}-\d{1,8}$", self.name):
                    raise UserError(
                        "El Formato de la Nota de Débito para la factura es incorrecto. ")
            if self.reversal_move_id.invoice_type_code == '03':
                if not re.match("^B\w{3}-\d{1,8}$", self.name):
                    raise UserError(
                        "El Formato de la Nota de Débito para la Boleta es Incorrecto. ")
        else:
            raise UserError("El Tipo de Documento del Comprobante es Obligatorio")



    nombreEmisor = self.company_id.partner_id.registration_name.strip()
    numDocEmisor = self.company_id.partner_id.vat.strip(
    ) if self.company_id.partner_id.vat else ""

    numDocReceptor = self.partner_id.vat.strip() if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code in [
        "1", "6"] and self.partner_id.vat else "-"
    nombreReceptor = self.partner_id.registration_name if self.partner_id.registration_name not in [
        "-", False, "", " - "] else self.partner_id.name
    nombreReceptor = nombreReceptor.strip()
    tipoDocReceptor = self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code
    direccionReceptor = self.partner_id.street if self.partner_id.street else "-"
    nombreComercialReceptor = replace_false(
        self.partner_id.name if self.partner_id.name else self.partner_id.registration_name)

    correlativo = int(self.name.split("-")[1])
    data = {
        "company": {
            "numDocEmisor": numDocEmisor,
            "nombreEmisor": nombreEmisor,
            "SUNAT_user": self.company_id.sunat_user,
            "SUNAT_pass": self.company_id.sunat_pass,
            "key_private": self.company_id.cert_id.key_private,
            "key_public": self.company_id.cert_id.key_public,
        },
        "tipoDocumento": self.invoice_type_code,
        "fechaEmision": str(self.invoice_date),
        "idTransaccion": self.name,
        "correoReceptor": replace_false(self.partner_id.email if self.partner_id.email else "-"),
        "documento": {
            "serie": self.journal_id.code,
            "correlativo": correlativo,
            "nombreEmisor": nombreEmisor,
            "tipoDocEmisor": self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "numDocEmisor": numDocEmisor,
            "direccionReceptor": direccionReceptor,
            "direccionOrigen": replace_false(self.company_id.partner_id.street),
            "direccionUbigeo": replace_false(self.company_id.partner_id.zip),
            "nombreComercialEmisor": replace_false(self.company_id.partner_id.registration_name),
            "tipoDocReceptor": tipoDocReceptor,
            "numDocReceptor":  numDocReceptor,
            "nombreReceptor": nombreReceptor,
            "nombreComercialReceptor": replace_false(self.partner_id.name if self.partner_id.name else self.partner_id.registration_name),
            # VERIFICAR
            # "tipoDocReceptorAsociado": replace_false(self.partner_id.tipo_documento),
            # "numDocReceptorAsociado": self.partner_id.vat if self.partner_id.tipo_documento in ["1", "6"] and self.partner_id.vat else "-",
            # "nombreReceptorAsociado": replace_false(self.partner_id.registration_name if self.partner_id.registration_name else self.partner_id.name),
            # "direccionDestino" : "",#solo para boletas
            "tipoMoneda": self.currency_id.name,
            "sustento": replace_false(self.sustento_nota),  # solo notas
            "tipoMotivoNotaModificatoria": str(self.tipo_nota_credito if self.invoice_type_code == "07" else "-"),
            "mntExportacion": round(self.total_venta_exportacion, 2),
            "mntNeto": round(self.total_venta_gravado, 2),
            "mntExe": round(self.total_venta_inafecto, 2),
            "mntExo": round(self.total_venta_exonerada, 2),
            "mntTotalIgv": round(self.amount_igv, 2),
            "mntTotal": round(self.amount_total, 2),
            # solo para facturas y boletas
            "mntTotalGrat": round(self.total_venta_gratuito, 2),
            "fechaVencimiento": str(self.invoice_date_due) if self.invoice_date_due else datetime.now().strftime("%Y-%m-%d"),
            "glosaDocumento": "VENTA",  # verificar
            "codContrato": replace_false(self.name),
            # "codCentroCosto" : "",
            # verificar
            "tipoCambioDestino": round(self.tipo_cambio_fecha_factura, 4),
            "mntTotalIsc": 0.0,
            "mntTotalOtros": 0.0,
            "mntTotalOtrosCargos": 0.0,
            # "mntTotalAnticipos" : 0.0, #solo factura y boleta
            "tipoFormatoRepresentacionImpresa": "GENERAL",
            "ordenCompra":self.order_reference if self.order_reference else False,
            "documentosRelacionados":[{
                    "type_code":dr.document_type_code,
                    "number":dr.document_number    
                } for dr in self.document_reference_ids
            ]
            # "mntTotalLetras": to_word(round(self.amount_total, 2), self.currency_id.name),
        },
        "descuento": {
            # "mntDescuentoGlobal": round(self.total_descuento_global, 2),
            "mntTotalDescuentos": round(self.total_descuentos, 2)
        },
        "tipoOperacion":self.invoice_type_code_catalog_51.code
        # solo factura y boleta
        # "servicioHospedaje": { },
        # solo factura y boleta, con expecciones

        # "indicadores": {
            # VERIFICAR ESTOS CAMPOS
            # "indVentaInterna": True if self.tipo_operacion == "0101" else 0,
            # "indExportacion": True if self.tipo_operacion == "02" else 0,
            # "indNoDomiciliados" : False, #valido para notas
            # "indAnticipo": True if self.tipo_operacion == "04" else 0,
            # "indDeduccionAnticipos" : False,
            # "indServiciosHospedaje" : False,
            # "indVentaItinerante": True if self.tipo_operacion == "05" else 0
            # "indTrasladoBienesConRepresentacionImpresa" : False,
            # "indVentaArrozPilado" : False,
            # "indComprobantePercepcion" : False,
            # "indBienesTransferidosAmazonia" : False,
            # "indServiciosPrestadosAmazonia" : False,
            # "indContratosConstruccionEjecutadosAmazonia" : False

        # },

        # solo factura y boleta
        # "percepcion": {
        # "mntBaseImponible" : 0.0,
        # "mntPercepcion" : 0.0,
        # "mntTotalMasPercepcion" : 0.0,
        # "tasaPercepcion" : 1.0
        # },
        # "datosAdicionales": {},
    }

    if self.has_detraction:
        data.update({
            "detraccion":{
                "tasa":self.detraction_rate,
                "codigo":self.detraction_code,
                "monto":self.detraction_amount_pen,
                "numero_cuenta_banco_nacion":self.bank_account_number_national,
                "medio_pago":self.detraction_medio_pago.code
            }
        })

    data_impuesto = []
    data_detalle = []
    data_referencia = []  # solo para notas
    data_anticipo = []  # solo facturas y boletas
    data_anexo = []  # si hay anexos

    # if self.invoice_payment_term_id:
    #     data["documento"]["metodosPago"] = {
    #         "metodo": "Credito",
    #     }
    payment_term = {"formaPago":"Contado"}
    # if self.invoice_payment_term_id:
    if self.invoice_payment_term_type == "Credito":
        payment_term["formaPago"] = "Credito"
        cuota = 1
        creditoCuotas = []
        for line in self.paymentterm_line.sorted(lambda r:r.date_due):
            creditoCuotas.append({"nombre":"Cuota{:03.0f}".format(cuota),
                                        "fechaVencimiento":line.date_due.strftime("%Y-%m-%d"),
                                        "monto":round(line.amount,2)})
            cuota = cuota + 1
        payment_term.update({"creditoCuotas":creditoCuotas})

    data["documento"].update(payment_term)

    if self.descuento_global:
        data["documento"]["descuentoGlobal"] = {
            "factor": round(self.descuento_global/100.00, 4),
            "montoDescuento": round(self.total_descuento_global, 2),
            # El atributo amount_untaxed es el monto del total de ventas sin impuestos
            "montoBase": round(self.total_venta_gravado + self.total_venta_exonerada + self.total_venta_inafecto + self.total_descuento_global, 2)
        }
    if self.apply_retention:
        data["documento"]["retencion"] = {
            "factor": round(self.retention_rate/100.00, 4),
            "montoRetencion": round(self.amount_retention, 2),
            # El atributo amount_untaxed es el monto del total de ventas sin impuestos
            "montoBase": round(round(self.total_venta_gravado,2) + round(self.total_venta_exonerada,2) + round(self.total_venta_inafecto,2) + round(self.amount_igv,2) + round(self.total_descuento_global,2), 2)
        }

    # if self.numero_guia_remision:
    #     data["documento"]["numero_guia"] = self.numero_guia_remision

    # if self.nota_id:
    #     data["nota"] = self.nota_id.descripcion
    ###############
    # self.total_venta_gravado = sum(
    #     [
    #         line.price_subtotal
    #         for line in self.invoice_line_ids
    #         if len([line.price_subtotal for line_tax in line.tax_ids
    #                 if line_tax.tax_group_id.tipo_afectacion in ["10"]])
    #     ])*(1-self.descuento_global/100.0)

    # self.total_venta_inafecto = sum(
    #     [
    #         line.price_subtotal
    #         for line in self.invoice_line_ids
    #         if len(
    #             [line.price_subtotal for line_tax in line.tax_ids
    #                 if line_tax.tax_group_id.tipo_afectacion in ["40", "30"]])
    #     ])*(1-self.descuento_global/100.0)

    # self.total_venta_exonerada = sum(
    #     [
    #         line.price_subtotal
    #         for line in self.invoice_line_ids
    #         if len(
    #             [line.price_subtotal for line_tax in line.tax_ids
    #                 if line_tax.tax_group_id.tipo_afectacion in ["20"]])
    #     ])*(1-self.descuento_global/100.0)

    # self.total_venta_gratuito = sum(
    #     [
    #         line.price_unit*line.quantity
    #         for line in self.invoice_line_ids
    #         if len([1 for line_tax in line.tax_ids
    #                 if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36", "37"]])
    #     ])
    ##########
    # taxlen = 0
    # for line in self.invoice_line_ids:
    #     for tax in line.tax_ids:
    #         data_impuesto.append({
    #             "codImpuesto": str(tax.tax_group_id.codigo),
    #             "montoImpuesto": round(line.tax_base_amount, 2),
    #             "tasaImpuesto": round(tax.amount/100, 2)
    #         })
    #         taxlen += 1

    # if taxlen == 0:
    #     data_impuesto.append({
    #         "codImpuesto": "1000",
    #         "montoImpuesto": 0.0,
    #         "tasaImpuesto": 0.18
    #     })
    # if len(self.tax_ids) == 0:
    #     data_impuesto.append({
    #         "codImpuesto": "1000",
    #         "montoImpuesto": 0.0,
    #         "tasaImpuesto": 0.18
    #     })

    for item in self.invoice_line_ids.filtered(lambda r: not r.is_charge_or_discount and not r.display_type):
        #price_unit = item.price_unit*(1-(item.discount/100)) - item.descuento_unitario
        #descuento = item.price_unit*item.discount/100 + item.descuento_unitario
        """
        price_unit = item.price_unit
        descuento_unitario = item.descuento_unitario
        descuento = 0
        tasaIgv = item.invoice_line_tax_ids[0].amount /100 if len(item.invoice_line_tax_ids) else ""
        if (item.invoice_line_tax_ids.price_include):

            if (item.invoice_line_tax_ids.amount == 0):
                montoImpuestoUni = 0
                base_imponible = price_unit
                descuento = (base_imponible*item.discount /
                             100 + descuento_unitario)
            else:
                base_imponible = price_unit / (1+tasaIgv)
                descuento_unitario = descuento_unitario / (1+tasaIgv)
                descuento = (base_imponible*item.discount /
                             100 + descuento_unitario)
                montoImpuestoUni = price_unit - base_imponible - descuento*tasaIgv
            precioItem = price_unit
        else:
            base_imponible = price_unit
            descuento = (base_imponible*item.discount/100 + descuento_unitario)
            montoImpuestoUni = (price_unit - descuento)*tasaIgv
            precioItem = price_unit + montoImpuestoUni
            base_imponible = price_unit

        montoItem = round((base_imponible) * item.quantity, 2)
        nombreItem = item.name.strip().replace("\n","")
        """
        # if item.tax_ids:
        #     taxes = item.tax_ids.compute_all(item.price_unit)
        # precioItemSinIgv = taxes["total_excluded"]

        tasaIgv = round(item.tax_ids[0].amount/100,2) if len(item.tax_ids) else ""

        montoIgv = round(item.price_total-item.price_subtotal, 3)
        datac = {
            "cantidadItem": round(item.quantity, 3),
            "unidadMedidaItem": item.product_uom_id.code,
            "codItem": str(item.product_id.id),
            "nombreItem": item.name[0:250].strip().replace("\n", " "),
            # Precio unitario con IGV
            "precioItem": round(item.price_total/item.quantity, 10) if len([item for line_tax in item.tax_ids if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"]]) == 0 else 0,
            # Precio unitario sin IGV y sin descuento
            "precioItemSinIgv": round((item.price_subtotal/item.quantity)/(1-item.discount/100), 10) if len([item for line_tax in item.tax_ids if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"]]) == 0 else 0,
            # Monto total de la línea sin IGV
            "montoItem": round(item.price_unit*item.quantity, 2) if item.no_onerosa else round(item.price_subtotal, 2),
            # "descuentoMonto": round((item.price_subtotal*item.discount/100.0)/(1-item.discount/100.0), 2),  # solo factura y boleta
            "codAfectacionIgv": item.tax_ids[0].tax_group_id.tipo_afectacion if len(item.tax_ids) else "",
            "tasaIgv": round(tasaIgv*100, 2),
            # Monto Total del IGV
            "montoIgv": round(montoIgv if montoIgv > 0 else 0.0,2),
            "codSistemaCalculoIsc": "01",  # VERIFICAR
            "montoIsc": 0.0,  # VERIFICAR
            # "tasaIsc" : 0.0, #VERIFICAR
            # VERIFICAR
            "precioItemReferencia": round(item.price_unit, 2),
            "idOperacion": str(self.id),
            "no_onerosa": True if item.no_onerosa else False
        }
        if item.discount:
            datac["descuento"] = {
                "factor": round(item.discount/100.0, 4),
                "montoDescuento": round((item.price_subtotal*item.discount/100.0)/(1-item.discount/100.0), 2),
                "montoBase": round(item.price_subtotal/(1-item.discount/100.0), 2)
            }
            datac.update({
                "montoItem":round(item.price_subtotal,2)
            })
        icbper = item.tax_ids.filtered(lambda r: r.tax_group_id.codigo == "7152")
        
        if icbper.exists():
            datac.update({
                "afectacionICBPER":True,
                "tasa_ICBPER":icbper.amount
            })
        if item.product_id.sunat_code:
            datac.update({"sunatCode":item.product_id.sunat_code})

        data_detalle.append(datac)

    # data["impuesto"] = data_impuesto
    data["detalle"] = data_detalle
    if len(data_anticipo):
        data["anticipos"] = data_anticipo
    if len(data_anexo):
        data["anexos"] = data_anexo

    return data
    # return json.dumps(data,indent=4)


def crear_json_not_cred_deb(self):
    now = fields.Datetime.now()

    nombreEmisor = self.company_id.partner_id.registration_name.strip()
    numDocEmisor = self.company_id.partner_id.vat.strip(
    ) if self.company_id.partner_id.vat else ""

    numDocReceptor = self.partner_id.vat.strip() if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code in [
        "1", "6"] and self.partner_id.vat else "-"
    nombreReceptor = self.partner_id.registration_name if self.partner_id.registration_name not in [
        "", "-", " - ", False] else self.partner_id.name
    nombreReceptor = nombreReceptor.strip()
    correlativo = int(self.name.split("-")[1])

    data = {
        "company": {
            "numDocEmisor": numDocEmisor,
            "nombreEmisor": nombreEmisor,
            "SUNAT_user": self.company_id.sunat_user,
            "SUNAT_pass": self.company_id.sunat_pass,
            "key_private": self.company_id.cert_id.key_private,
            "key_public": self.company_id.cert_id.key_public,
        },
        "tipoDocumento": self.journal_id.invoice_type_code_id,
        "fechaEmision": str(self.invoice_date),
        "idTransaccion": self.name,
        "correoReceptor": replace_false(self.partner_id.email if self.partner_id.email else "-"),
        "documento": {
            "serie": self.journal_id.code,
            "correlativo": correlativo,
            "nombreEmisor": nombreEmisor,
            "tipoDocEmisor": self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "numDocEmisor": numDocEmisor,
            "direccionOrigen": replace_false(self.company_id.partner_id.street),
            "direccionUbigeo": replace_false(self.company_id.partner_id.ubigeo),
            "nombreComercialEmisor": replace_false(self.company_id.partner_id.registration_name),
            "tipoDocReceptor": self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
            "numDocReceptor": numDocReceptor,
            "nombreReceptor": nombreReceptor,
            "nombreComercialReceptor": replace_false(
                self.partner_id.name if self.partner_id.name else self.partner_id.registration_name),
            "direccionReceptor": self.partner_id.street if self.partner_id.street else "-",
            # VERIFICAR
            # "tipoDocReceptorAsociado": replace_false(self.partner_id.l10n_latam_identification_type_id),
            # "numDocReceptorAsociado": replace_false(self.partner_id.vat),
            # "nombreReceptorAsociado": replace_false(
            #     self.partner_id.registration_name if self.partner_id.registration_name else self.partner_id.name),
            # "direccionDestino" : "",#solo para boletas
            "tipoMoneda": self.currency_id.name,
            "sustento": replace_false(self.sustento_nota),  # solo notas
            # solo_notas
            "tipoMotivoNotaModificatoria": str(self.tipo_nota_credito if self.invoice_type_code == "07" else self.tipo_nota_debito),
            "mntNeto": round(self.total_venta_gravado, 2),
            "mntExe": round(self.total_venta_inafecto, 2),
            "mntExo": round(self.total_venta_exonerada, 2),
            "mntTotalIgv": round(self.amount_igv, 2),
            "mntTotal": round(self.amount_total, 2),
            "mntTotalGrat": round(self.total_venta_gratuito, 2), 
            "fechaVencimiento": str(self.invoice_date_due) if self.invoice_date_due else now.strftime("%Y-%m-%d"),
            "glosaDocumento": "VENTA",  # verificar
            "codContrato": replace_false(self.name),
            # "codCentroCosto" : "",
            # verificar
            # "tipoCambioDestino": round(self.tipo_cambio_fecha_factura, 4),
            "mntTotalIsc": 0.0,
            "mntTotalOtros": 0.0,
            "mntTotalOtrosCargos": 0.0,
            # "mntTotalAnticipos" : 0.0, #solo factura y boleta
            "tipoFormatoRepresentacionImpresa": "GENERAL",
            # "mntTotalLetras": to_word(round(self.amount_total, 2), self.currency_id.name)
        },
        "descuento": {
            # "mntDescuentoGlobal": round(self.total_descuento_global, 2),
            "mntTotalDescuentos": round(self.total_descuentos, 2)
        },
        # solo factura y boleta
        # "servicioHospedaje": { },
        # solo factura y boleta, con expecciones

        "indicadores": {
            # VERIFICAR ESTOS CAMPOS
            "indVentaInterna": True if self.tipo_operacion == "01" else 0,
            "indExportacion": True if self.tipo_operacion == "02" else 0,
            # "indNoDomiciliados" : False, #valido para notas
            "indAnticipo": True if self.tipo_operacion == "04" else 0,
            # "indDeduccionAnticipos" : False,
            # "indServiciosHospedaje" : False,
            "indVentaItinerante": True if self.tipo_operacion == "05" else 0
            # "indTrasladoBienesConRepresentacionImpresa" : False,
            # "indVentaArrozPilado" : False,
            # "indComprobantePercepcion" : False,
            # "indBienesTransferidosAmazonia" : False,
            # "indServiciosPrestadosAmazonia" : False,
            # "indContratosConstruccionEjecutadosAmazonia" : False

        },

        # solo factura y boleta
        # "percepcion": {
        # "mntBaseImponible" : 0.0,
        # "mntPercepcion" : 0.0,
        # "mntTotalMasPercepcion" : 0.0,
        # "tasaPercepcion" : 1.0
        # },
        # "datosAdicionales": {},
    }
    data_impuesto = []
    data_detalle = []
    data_referencia = []  # solo para notas
    data_anticipo = []  # solo facturas y boletas
    data_anexo = []  # si hay anexos

    # taxlen = 0
    # for line in self.invoice_line_ids.filtered(lambda r: not r.is_charge_or_discount):
    #     for tax in line.tax_ids:
    #         data_impuesto.append({
    #             "codImpuesto": str(tax.tax_group_id.codigo),
    #             "montoImpuesto": round(line.tax_base_amount, 2),
    #             "tasaImpuesto": round(tax.amount/100, 2)
    #         })
    #         taxlen += 1

    # if taxlen == 0:
    #     data_impuesto.append({
    #         "codImpuesto": "1000",
    #         "montoImpuesto": 0.0,
    #         "tasaImpuesto": 0.18
    #     })

    for item in self.invoice_line_ids.filtered(lambda r: not r.is_charge_or_discount and not r.display_type):
        # price_unit = item.price_unit * \
        #     (1-(item.discount/100)) - item.descuento_unitario
        # if (item.invoice_line_tax_ids.price_include):

        #     if (item.invoice_line_tax_ids.amount == 0):
        #         montoImpuestoUni = 0
        #         base_imponible = price_unit
        #     else:
        #         base_imponible = price_unit / \
        #             (1 + (item.invoice_line_tax_ids.amount / 100))
        #         montoImpuestoUni = price_unit - base_imponible

        #     precioItem = price_unit

        # else:
        #     montoImpuestoUni = price_unit * \
        #         (item.invoice_line_tax_ids.amount / 100)

        #     precioItem = price_unit + montoImpuestoUni
        #     base_imponible = price_unit

        '''
        data_impuesto.append({
            "codImpuesto": str(item.invoice_line_tax_ids.tax_group_id.code),
            "montoImpuesto": round(montoImpuestoUni * item.quantity, 2),
            "tasaImpuesto": round(item.invoice_line_tax_ids.amount / 100, 2)
        })
        
        '''
        # tasaIgv = item.invoice_line_tax_ids[0].amount / \
        #     100 if len(item.invoice_line_tax_ids) else ""
        tasaIgv = round(item.tax_ids[0].amount/100,2) if len(item.tax_ids) else ""
        # montoImpuestoUni = 0
        # montoItem = round((price_unit) * item.quantity, 2)
        nombreItem = item.name.strip().replace("\n", "")
        montoIgv = round(item.price_total-item.price_subtotal, 2)
        datac = {
            "cantidadItem": round(item.quantity, 3),
            "unidadMedidaItem": item.product_uom_id.code,
            "codItem": str(item.product_id.id),
            "nombreItem": nombreItem[0:250].strip().replace("\n", " "),
            # "precioItem": round(item.price_total/item.quantity, 10),
            "precioItem": round(item.price_total/item.quantity, 10) if len([item for line_tax in item.tax_ids if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"]]) == 0 else 0,
            # "precioItemSinIgv": round(price_unit, 2),
            # "montoItem": round(item.product_id.lst_price*item.quantity, 2) if montoItem == 0 else montoItem,
            # "precioItemSinIgv": round(item.price_subtotal/item.quantity, 10),
            "precioItemSinIgv": round((item.price_subtotal/item.quantity), 10) if len([item for line_tax in item.tax_ids if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"]]) == 0 else 0,
            # "montoItem": round(item.price_subtotal, 2),
            "montoItem": round(item.price_unit*item.quantity, 2) if item.no_onerosa else round(item.price_subtotal, 2),
            # "descuentoMonto": item.discount * precioItem / 100,  # solo factura y boleta
            "codAfectacionIgv":  item.tax_ids[0].tax_group_id.tipo_afectacion if len(item.tax_ids) else "",
            "tasaIgv": round(tasaIgv*100, 2),
            # "montoIgv": round(montoImpuestoUni * item.quantity, 2),
            "montoIgv": montoIgv if montoIgv > 0 else 0.0,
            "codSistemaCalculoIsc": "01",  # VERIFICAR
            "montoIsc": 0.0,  # VERIFICAR
            # "tasaIsc" : 0.0, #VERIFICAR
            "precioItemReferencia": round(item.price_unit, 2),
            "idOperacion": str(self.id),
            "no_onerosa": True if item.no_onerosa else False
        }

        # if item.discount > 0:
        #     datac["descuento"] = {
        #         "factor": round(item.discount/100.0, 4),
        #         "montoDescuento": round(((item.price_subtotal*item.discount/100.0)/(1-item.discount/100.0)), 2),
        #         "montoBase": round((item.price_subtotal/(1-item.discount/100.0)), 2)
        #     }
        #     datac.update({
        #         "montoItem":round(item.price_subtotal,2)
        #     })

        data_detalle.append(datac)

    if self.invoice_type_code in ["07", "08"]:
        document_reference = self.reversed_entry_id if self.invoice_type_code == '07' else self.debit_origin_id
        data_referencia.append({
            'tipoDocumentoRef': document_reference.invoice_type_code,
            'serieRef': document_reference.name[0:4],
            'correlativoRef': int(document_reference.name[5:len(document_reference.name)]),
            'fechaEmisionRef': str(document_reference.invoice_date),
            'numero': document_reference.name
        })
        # if self.formato_comprobante_ref not in ["fisico", "electronico"]:
        #     raise ValidationError(
        #         "El formato del comprobante de referencia debe ser Físico o Electrónico")

        # if self.formato_comprobante_ref == "fisico":
        #     if not self.comprobante_fisico_ref and not self.tipo_comprobante_ref:
        #         raise ValidationError(
        #             "Cuando el tipo de comprobante de referencia es físico entonces, debe completar el campo de comprobante físico de referencia y el tipo de documento (Factura o Boleta)")
        #     else:
        #         if not re.match("^\d{4}-\d{1,8}$", self.comprobante_fisico_ref):
        #             raise ValidationError(
        #                 "El Comprobante no posee el formato Requerido")

        #         serieRef = self.comprobante_fisico_ref.split("-")[0]
        #         correlativoRef = self.comprobante_fisico_ref.split("-")[1]
        #         tipoDocumentoRef = self.tipo_comprobante_ref

        #         data_referencia.append({
        #             'tipoDocumentoRef': tipoDocumentoRef,
        #             'serieRef': serieRef,
        #             'correlativoRef': correlativoRef,
        #             'fechaEmisionRef': self.fecha_emision_comprobante_fisico_ref,
        #             'numero': self.comprobante_fisico_ref
        #         })

        # elif self.formato_comprobante_ref == "electronico":
        #     document_reference = self.reversal_move_id
        #     data_referencia.append({
        #         'tipoDocumentoRef': document_reference.invoice_type_code,
        #         'serieRef': document_reference.number[0:4],
        #         'correlativoRef': int(document_reference.number[5:len(document_reference.number)]),
        #         'fechaEmisionRef': document_reference.date_invoice,
        #         'numero': document_reference.number
        #     })
        #     if document_reference.number[0] != self.journal_id.code[0]:
        #         raise UserError(
        #             "Las Notas de Facturas deben iniciar con 'F' y las Notas de Boletas deben iniciar con 'B'")
        # else:
        #     raise ValidationError("El Formato del Comprobante se Obligatorio")
    else:
        raise ValidationError(
            "El código del tipo de comprobante debe ser 07 para Notas de Crédito o 08 para Notas de Débito")

    # data["impuesto"] = data_impuesto
    data["detalle"] = data_detalle
    if len(data_anticipo):
        data["anticipos"] = data_anticipo
    if len(data_anexo):
        data["anexos"] = data_anexo
    data["referencia"] = data_referencia

    return data


def replace_false(dato):
    if dato:
        return dato
    else:
        return ""


def enviar_doc_baja_url(data_doc, tipoEnvio):
    data_doc["tipoEnvio"] = int(tipoEnvio)

    r = api_models.lamdba(data_doc)

    return r


def enviar_doc_resumen_url(data_doc, tipoEnvio):
    data_doc["tipoEnvio"] = int(tipoEnvio)

    r = api_models.lamdba(data_doc)

    return r


# def baja_doc(self):
#     token = generate_token(self.company_id.api_key,
#                            self.company_id.api_secret, 10000)
#     data_doc = crear_json_baja(self)
#     response_env = enviar_doc_resumen_url(
#         self.company_id.endpoint, data_doc, token, self.company_id.tipo_envio)
#     self.json_comprobante = data_doc
#     self.json_respuesta = json.dumps(response_env.json(), indent=4)
#     if response_env.ok:
#         self.status_envio = True
#         self.estado_emision = extaer_estado_emision(response_env.json())
#         return True, ""
#     else:
#         recepcionado, estado_emision, msg_error = extraer_error(response_env)
#         if recepcionado:
#             self.status_envio = True
#             self.estado_emision = estado_emision
#             return True, msg_error
#         else:
#             return False, msg_error


def extaer_estado_emision(response_env):
    result = response_env.get("result", False)
    if result:
        if result.get("data", False):
            data = result["data"]
            return data['estadoEmision']
    return ""


def extraer_error(response_env):
    if not response_env.get("success"):
        raise UserError(json.dumps(response_env))

    if response_env.get("result", False):
        if response_env["result"].get("errors"):
            errors = response_env["result"].get("errors")
        else:
            raise UserError(json.dumps(response_env["result"]))
    else:
        errors = response_env.get("sunat_errors")
        # raise UserError(json.dumps(response_env["request_id"]))

    #errors = response_env["result"]['errors']
    msg_error = ""
    i_error = 1
    estado_emision = ""
    recepcionado = False
    for error in errors:
        if 'meta' in error:
            error_meta = error['meta']
            if 'estadoEmision' in error_meta:
                estado_emision = error_meta['estadoEmision']
                recepcionado = True

            if 'codigoErrorSUNAT' in error_meta:
                msg_error = msg_error + "ERROR N " + \
                    str(i_error) + ": Error en SUNAT " + \
                    error_meta['codigoErrorSUNAT'] + \
                    error_meta['descripcionErrorSUNAT']
            else:
                # + " - " + error['detail'].encode('latin1')
                msg_error = msg_error + "ERROR N " + \
                    str(i_error) + ": " + str(error['code'])
        else:
            # + " - " + error['detail'].encode('latin1')
            msg_error = msg_error + "ERROR N " + \
                str(i_error) + ": " + str(error['code'])

        i_error = i_error + 1

    return recepcionado, estado_emision, msg_error



def request_status_ticket(sunat_provider,username,password,ticket,tipo_envio):
    resumen = ResumenDiario()
    request_status_xml = resumen.getStatus(username or "", password, ticket).toprettyxml("  ")
    _logger.info(request_status_xml)
    endpoint = ""
    if sunat_provider == "sunat":
        if int(tipo_envio) == 0:
            endpoint = urls_test[0]
        if int(tipo_envio) == 1:
            endpoint = urls_production[0]
        
    elif sunat_provider == "efact":
        if int(tipo_envio) == 1: 
            endpoint = urls_production_efact[0]
        else:
            raise Exception("Tipo de envio incorrecto. Tipos de envío posibles: 1- Producción")
    
    response = requests.post(endpoint, data=request_status_xml, headers={"Content-Type": "text/xml; charset=utf-8"})
    # _logger.info(response.text)
    if response.status_code != 200:
        raise UserError(response.text)

    doc = minidom.parseString(response.text.encode("ISO-8859-1"))

    fault = doc.getElementsByTagName("faultcode")
    if fault:
        faultcode = doc.getElementsByTagName("faultcode")[0].firstChild.data
        try:
            faultstring = lista_errores.get_error_by_code(faultcode)
        except Exception as e:
            faultstring = doc.getElementsByTagName("faultstring")[0].firstChild.data

        return {
            "code": faultcode,
            "description": faultstring,
            "status": "N"
        }

    digestValue = False
    cdr = False
    statusCode = doc.getElementsByTagName("statusCode")[0].firstChild.data
    if statusCode:
        Description = ""
        ResponseCode = ""
        ReferenceID = ""
        status = ""
        try:
            statusCode = int(statusCode)
        except Exception as e:
            statusCode = -1

        if statusCode in [0, 99]:
            content = doc.getElementsByTagName("content")
            zip_data = content[0].firstChild.data
            zip_decode = base64.b64decode(zip_data)
            zip_file = zipfile.ZipFile(io.BytesIO(zip_decode))
            xml_read = zip_file.read(zip_file.namelist()[-1])
            _logger.info(xml_read)
            xml_read = sunat_response_handle.set_xml_attributes(xml_read)
            _logger.info(xml_read)
            doc_xml = minidom.parseString(xml_read)
            

            DocumentResponse = doc_xml.getElementsByTagName("cac:DocumentResponse")
            if DocumentResponse:
                Description = DocumentResponse[0].getElementsByTagName("cbc:Description")[0].firstChild.data
                ResponseCode = DocumentResponse[0].getElementsByTagName("cbc:ResponseCode")[0].firstChild.data
                ReferenceID = DocumentResponse[0].getElementsByTagName("cbc:ReferenceID")[0].firstChild.data
                Description = ResponseCode+" - " + (Description if Description else lista_errores.get_error_by_code(ResponseCode) )
            if statusCode == 0:
                cdr = doc_xml.toprettyxml("        ")
                Description = doc_xml.getElementsByTagName("cbc:Description")[0].firstChild.data
                if doc_xml.getElementsByTagName("DigestValue"):
                    digestValue = doc_xml.getElementsByTagName("DigestValue")[0].firstChild.data
                else:
                    digestValue = doc_xml.getElementsByTagName("ds:DigestValue")[0].firstChild.data
                status = "A"
            elif statusCode == 99:
                status = "R"
        elif statusCode == 98:
            Description = "En Proceso de revisión"
            status = "E"
        else:
            status = False
            Description = doc.getElementsByTagName("statusMessage")
            if not Description:
                Description = lista_errores.get_error_by_code(statusCode)
            else:
                Description = Description[0].firstChild.data
            ResponseCode = statusCode

        return {
            "description": Description,
            "code": ResponseCode,
            "status": status,
            "digestValue": digestValue,
            "cdr": cdr
        }
    else:
        content = doc.getElementsByTagName("content")
        content = content[0].firstChild.data
        return {
            "description": content,
            "code": statusCode,
            "status": "N",
            "digestValue": digestValue,
            "cdr": cdr
        }


def request_status_invoice(username,password,ruc_emisior,invoice_type,document_number):
    factura = Factura()
    serie,correlativo = document_number.split("-")
    request_status_cdr = factura.getStatusCdr(username or "",password,ruc_emisior,invoice_type,serie,correlativo).toprettyxml("  ")
    # endpoint = "https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService?wsdl"
    endpoint = "https://ww1.sunat.gob.pe/ol-it-wsconscpegem/billConsultService"
    
    try:
        headers = {
            'Content-Type': "text/xml; charset=utf-8",
            'Cookie': 'f5avraaaaaaaaaaaaaaaa_session_=INMKPNKKIAGOJCILIOEJGGFONADMLGLLFPLFFNCONMMEHKMOHAHFCHKAAHHIDFALMPKDDNOLFDNGJNGKPKPAFOOCFJOMJCHJANAGKCEHOAMFKIJFMNFOFPPGGHOKMPMD'
        }
        # _logger.info(request_status_cdr)
        response = requests.post(endpoint,
                                data=request_status_cdr,
                                headers=headers,
                                timeout=20)
        # _logger.info(response.text)
        result = sunat_response_handle.get_response_status_invoice(response.text)
        # _logger.info(result)
        data = {
            "response_json":json.dumps(result,indent=4),
            "response_xml_without_format":response.text,
            "response_content_xml": parseString(result.get("xml_content")).toprettyxml() if result.get("xml_content",False) else "",
            "date_request":fields.Datetime.now(),
            "status":result.get("status"),
            "log_observation_ids":[]
        }
        return data

    except Timeout as e:
        return {
            'name': 'Tiempo de espera excedido',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* El tiempo de espera de la respuesta ha sido excedida.\n* El comprobante se enviará de forma automática luego"
            }
        }
    except ConnectionError as e:
        return {
            'name': 'Error en la conexión',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* No se ha logrado enviar el comprobante.\n* Se intentará enviar luego de forma automática."
            }
        }
    except Exception as e:
        raise e
        return {
            'name': 'Error',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.pop.message',
            'target': 'new',
            'context': {
                'default_name': "Alerta",
                'default_accion': "* El comprobante ha sido generado de forma exitosa.\n* "+str(e)
            }
        }
