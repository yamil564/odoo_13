import json
import requests
import os
from . import factura, nota_credito, nota_debito, firma, resumendiario, comunicacionbaja, guia_remision
from . import xml_validation, sunat_response_handle
from ..efact21.Documents import Factura, CreditNote, DebitNote, ResumenDiario, ComunicacionBaja, DespatchAdvice
import base64
from io import BytesIO
# with open("./pce-credentials.json") as f:
#     creds = json.loads(f.read())

import logging
_logger = logging.getLogger(__name__)

urls = [
    "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService",
    "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService",
    "https://www.sunat.gob.pe/ol-ti-itcpgem-sqa/billService",
    "https://www.sunat.gob.pe/ol-it-wsconscpegem/billConsultService",
]

# Pruebas
urls_test = [
    "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService",  # Fact
    "https://e-beta.sunat.gob.pe/ol-ti-itemision-guia-gem-beta/billService",  # Guia
    "https://e-beta.sunat.gob.pe/ol-ti-itemision-otroscpe-gem-beta/billService",  # REte
]

# Produccion
urls_production = [
    "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService",  # Fact
    "https://e-guiaremision.sunat.gob.pe/ol-ti-itemision-guia-gem/billService",  # Guia
    "https://e-factura.sunat.gob.pe/ol-ti-itemision-otroscpe-gem/billService",  # REte
]

urls_ose_efact = {
    "test": {
        # Enpoint para obtener Token,
        "get_token": "https://ose-gw1.efact.pe/api-efact-ose/oauth/token",
        # Endpoint de envío de documentos
        "document": "https://ose-gw1.efact.pe/api-efact-ose/v1/document"
    },
    "production": {
        # Endpoint para obtener Token
        "get_token": "https://ose.efact.pe/api-efact-ose/oauth/token",
        # Endpoint de envío de documentos
        "document": "https://ose.efact.pe/api-efact-ose/v1/document"
    }
}

urls_ose_nubefact = {
    "test": {
        # Endpoint de envío de documentos
        "document": "https://demo-ose.nubefact.com/ol-ti-itcpe/billService"
    },
    "production": {
        # Endpoint de envío de documentos
        "document": "https://ose.nubefact.com/ol-ti-itcpe/billService"
    }
}

# Validez de xml
url_check_xml = "https://e-factura.sunat.gob.pe/ol-it-wsconsvalidcpe/billValidService"

# Consulta de CRD y estado de envio
url_crd_status = "https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService"


def handle(data, user_credentials, self_signed=False):
    xsd = None

    if data.get("resumen", False):
        document_type = data["tipoResumen"]
        if document_type == "RC":
            document = resumendiario.build_resumen(data)
            if type(document) != ResumenDiario:
                return document

            ruc = data["resumen"]["numDocEmisor"]
            number = str(data["fechaGeneracion"]).replace("-", "") + "-" + str(data["resumen"]["id"])
            file_name = str("{ruc}-{doc_type}-{number}".format(
                ruc=ruc,
                doc_type=document_type,
                number=number
            ))
        elif document_type == "RA":
            document = comunicacionbaja.build_comunicacion_baja(data)
            if type(document) != ComunicacionBaja:
                return document
            ruc = data["resumen"]["numDocEmisor"]
            number = str(data["fechaGeneracion"]).replace(
                "-", "") + "-" + str(data["resumen"]["id"])
            file_name = str("{ruc}-{doc_type}-{number}".format(
                ruc=ruc,
                doc_type=document_type,
                number=number
            ))
        # xsd = "./files/XSD 2.1/maindoc/UBL-Invoice-2.1.xsd"  # Poner el valor correcto
    elif data.get("tipoDocumento") in ["01", "03"]:
        document = factura.build_factura(data)
        if type(document) != Factura:
            return {"success": False, "document": document}
        document_type = data["tipoDocumento"]
        file_name = document.file_name
        # xsd = "./files/XSD 2.1/maindoc/UBL-Invoice-2.1.xsd"
    elif data.get("tipoDocumento") == "07":
        document = nota_credito.build_nota_credito(data)
        if type(document) != CreditNote:
            return {"success": False, "document": document}
        document_type = data["tipoDocumento"]
        file_name = document.file_name
        # xsd = "./files/XSD 2.1/maindoc/UBL-CreditNote-2.1.xsd"
    elif data.get("tipoDocumento") == "08":
        document = nota_debito.build_nota_debito(data)
        if type(document) != DebitNote:
            return {"success": False, "document": document}
        document_type = data["tipoDocumento"]
        file_name = document.file_name
        # xsd = "./files/XSD 2.1/maindoc/UBL-DebitNote-2.1.xsd"
        # return {"success": False, "error": "Not implemented"}
    elif data.get("tipoDocumento") == "09":
        document = guia_remision.build_guia(data)
        document_type = data["tipoDocumento"]
        if type(document) != DespatchAdvice:
            document['success'] = False
            return document
        file_name = document.file_name
        # xsd = "./files/XSD 2.1/maindoc/UBL-DespatchAdvice-2.1.xsd"
    errs, obs = [], []
    document.check_validation(errs, obs)

    # if xsd is not None and xml_validation.validate_xsd(xsd, document.get_document().toxml()):
    #     errs.append({
    #         "error": "XSD validation failed."
    #     })

    if len(errs) > 0:
        return {
            "success": False,
            "api_errors": errs,
            "api_observaciones": obs
        }

    # if self_signed:
    #     signer_credentials = user_credentials
    ruc = user_credentials["ruc"]
    usuario = user_credentials["usuario"]
    password = user_credentials["password"]
    # else:
    #     signer_credentials = creds
    #     usuario = creds["sunat_usuario"]
    #     password = creds["sunat_password"]
    #     ruc = creds["ruc"]

    # print(document.get_document().toxml())
    # _logger.info(document)
    signed = firma.firmar(document, user_credentials,
                          user_credentials['key_private'],
                          user_credentials['key_public'])

    # _logger.info(signed)
    digest_value = firma.get_digest_value(signed)

    doc_zip = firma.zipear(signed, file_name+".xml")
    
    # _logger.info(file_name + ".xml")
    if document_type in ["01", "03", "07", "08", "09"]:
        final_xml = firma.generate_envio_xml(
            str(ruc) + str(usuario or ""),
            password,
            file_name + ".zip", doc_zip.decode()
        )
    elif document_type in ["RC", "RA"]:
        final_xml = firma.generate_envio_resumen_xml(
            str(ruc) + str(usuario or ""),
            password,
            file_name + ".zip", doc_zip.decode()
        )

    return {
        "success": True,
        "api_observaciones": obs,
        "digest_value": digest_value,
        "signed_xml": signed.decode("ISO-8859-1"),
        "final_xml": final_xml,
        "document_type": document_type,
        "signer": user_credentials
    }


def send_consulta(consulta_xml, data, user, consulta=False):
    url = ""
    tipo_envio = data.get("tipoEnvio", 0)
    # if user.ose in ['sunat', '', None]:
    if tipo_envio == 0:  # Beta
        url = "https://e-beta.sunat.gob.pe:443/ol-ti-itcpfegem-beta/billService"
    elif tipo_envio == 1:  # Produccion
        if not consulta:
            url = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService"
        else:
            url = "https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService"

    # elif user.ose == "nubefact":
    #     if tipo_envio == 0:  # Beta
    #         url = urls_ose_nubefact["test"]["document"]
    #     elif tipo_envio == 2:  # Producción
    #         url = urls_ose_nubefact["production"]["document"]
    else:
        raise("URL de envío no configurado")
    # print(url)
    r = requests.post(url=url, data=consulta_xml, headers={
                      "Content-Type": "text/xml"})
    return r.text


# def send_xml_efact(prev_sign, data, user):
#     tipo_envio = data.get("tipoEnvio", 0)

#     if user.ruc in [None, ""]:
#         raise Exception(
#             "Error Parámetros OSE EFACT - La empresa no tiene configurado su RUC")
#     if user.ose_efact_password in [None, ""]:
#         raise Exception(
#             "Error Parámetros OSE EFACT - La empresa no tiene configurado su assword")
#     if user.ose_efact_access_key in [None, ""]:
#         raise Exception(
#             "Error Parámetros OSE EFACT - La empresa no tiene configurado su Access Key")

#     if tipo_envio == 0:
#         url_get_token = urls_ose_efact["test"]["get_token"]
#         url_document = urls_ose_efact["test"]["document"]
#     elif tipo_envio == 2:
#         url_get_token = urls_ose_efact["production"]["get_token"]
#         url_document = urls_ose_efact["production"]["document"]
#     else:
#         raise Exception("bad tipoEnvio")
#     a = "client:"+user.ose_efact_password
#     Authorization = "Basic " + str(base64.b64encode(bytes(a, "utf-8")))
#     headers = {'Content-Type': "application/x-www-form-urlencoded",
#                "Authorization": Authorization}
#     data = {"username": user.ruc,
#             "password": user.ose_efact_access_key, "grant_type": "password"}
#     try:
#         response_token = requests.post(
#             url_get_token, data=data, headers=headers)
#         # print(response_token.status_code)
#         # print(response_token.text)
#     except Timeout as e:
#         return {
#             "success": False,
#             "message": "Error OSE EFACT: Tiempo de consulta Excedido. Endpoint: "+url_get_token
#         }
#     except ConnectionError as e:
#         return {
#             "success": False,
#             "message": "Error OSE EFACT: Error en la conexión. Endpoint: "+url_get_token
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "message": "Error OSE EFACT: "+str(e)+". Endpoint: "+url_get_token
#         }

#     if response_token.status_code != 200:
#         return {
#             "success": False,
#             "message": "Error OSE EFACT: "+response_token.text
#         }

#     response_json_token = response_token.json()
#     token = response_json_token.get("access_token")
#     return {"token": response_json_token}
#     document_type = prev_sign['document_type']
#     if document_type in ['01', '03', '07', '08', '09', 'RA', 'RC']:
#         Authorization = "Basic " + token
#         files = prev_sign['final_xml']
#         try:
#             response_document = requests.post(url_document,
#                                               file=BytesIO(
#                                                   base64.b64encode(files)),
#                                               headers={'Content-Type': "multipart/form-data", "Authorization": Authorization})
#             resp['response_xml'] = response_document.text
#         except Timeout as e:
#             return {
#                 "success": False,
#                 "message": "Error OSE EFACT: Tiempo de consulta Excedido. Endpoint: "+url_get_token
#             }
#         except ConnectionError as e:
#             return {
#                 "success": False,
#                 "message": "Error OSE EFACT: Error en la conexión. Endpoint: "+url_get_token
#             }
#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": "Error OSE EFACT: "+str(e)+". Endpoint: "+url_get_token
#             }
#         if response_document.status_code != 200:
#             return {
#                 "success": False,
#                 "message": "Error OSE EFACT: "+response_token.text
#             }
#     else:
#         resp = {
#             "success": False,
#             "message": "Tipo de documento invalido"
#         }

#     resp["ose_efact_cdr"] = response_document.text

#     return resp

    """
    resp = requests.post(
        url,
        data=prev_sign['final_xml'],
        headers=headers,
        timeout=20)
    response_xml = resp.text

    document_type = prev_sign['document_type']
    if document_type in ['01', '03', '07', '08', '09']:
        resp = sunat_response_handle.get_response(response_xml)
    elif document_type in ['RA', 'RC']:
        resp = sunat_response_handle.get_response_ticket(response_xml)
        # Send queue
    else:
        resp = {
            "success": False,
            "message": "Invalid document type."
        }
    resp['response_xml'] = response_xml
    return resp
    """


def send_xml_sunat(prev_sign, data):
    # _logger.info("PREV SIGN")
    # _logger.info(prev_sign)
    tipo_envio = data.get("tipoEnvio", 0)

    if tipo_envio in [1, 3]:
        url = urls[tipo_envio]
    elif tipo_envio == 0:
        if prev_sign['document_type'] in ["09"]:
            url = urls_test[1]
        else:
            url = urls_test[0]
    elif tipo_envio == 2:
        if prev_sign['document_type'] in ["09"]:
            url = urls_production[1]
        else:
            url = urls_production[0]
    elif tipo_envio == 4:
        url = url_check_xml
    else:
        raise Exception("bad tipoEnvio")
    headers = {"Content-Type": "application/xml"}

    # _logger.info(url)
    resp = requests.post(
        url,
        data=prev_sign['final_xml'],
        headers=headers,
        timeout=20)
    response_xml = resp.text

    document_type = prev_sign['document_type']
    if document_type in ['01', '03', '07', '08', '09']:
        resp = sunat_response_handle.get_response(response_xml)
    elif document_type in ['RA', 'RC']:
        resp = sunat_response_handle.get_response_ticket(response_xml)
        # Send queue
    else:
        resp = {
            "success": False,
            "message": "Invalid document type."
        }
    resp['response_xml'] = response_xml
    return resp


# def send_xml_nubefact(prev_sign, data, user):
#     tipo_envio = data.get("tipoEnvio", 0)

#     if tipo_envio == 0:
#         url = urls_ose_nubefact["test"]["document"]
#     elif tipo_envio == 2:
#         url = urls_ose_nubefact["production"]["document"]
#     elif tipo_envio == 4:
#         url = url_check_xml
#     else:
#         raise Exception("bad tipoEnvio")

#     headers = {"Content-Type": "application/xml"}
#     print(url)
#     resp = requests.post(
#         url,
#         data=prev_sign['final_xml'],
#         headers=headers,
#         timeout=20)
#     response_xml = resp.text

#     document_type = prev_sign['document_type']
#     if document_type in ['01', '03', '07', '08', '09']:
#         resp = sunat_response_handle.get_response(response_xml)
#     elif document_type in ['RA', 'RC']:
#         resp = sunat_response_handle.get_response_ticket(response_xml)
#         # Send queue
#     else:
#         resp = {
#             "success": False,
#             "message": "Invalid document type."
#         }
#     resp['response_xml'] = response_xml
#     return resp


# def send_xml(prev_sign, data, user):
#     if user.ose in ['sunat', '', None]:
#         return send_xml_sunat(prev_sign, data, user)
#     elif user.ose == 'efact':
#         return send_xml_efact(prev_sign, data, user)
#     elif user.ose == 'nubefact':
#         return send_xml_nubefact(prev_sign, data, user)
