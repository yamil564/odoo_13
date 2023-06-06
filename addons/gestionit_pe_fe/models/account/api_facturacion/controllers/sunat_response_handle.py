import requests
import base64
from xml.dom import minidom
import zipfile
import io
from ..lista_errores import errores, error_list,get_error_by_code
import logging
import xml.etree.ElementTree as ET
_logger = logging.getLogger(__name__)


#data_document: minidom xml
def set_xml_attributes(data_document):
    data_document = minidom.parseString(data_document)
    namespaces = {"":"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                    "ar":"urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2",
                    "cac":"urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                    "cbc":"urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                    "date":"http://exslt.org/dates-and-times",
                    "ds":"http://www.w3.org/2000/09/xmldsig#",
                    "ext":"urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
                    "regexp":"http://exslt.org/regular-expressions",
                    "sac":"urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
                    "soap":"http://schemas.xmlsoap.org/soap/envelope/",
                    "xs":"http://www.w3.org/2001/XMLSchema"}
    
    for k in namespaces:
        v = namespaces[k]
        ET.register_namespace(k,v)

    data_document = ET.fromstring(data_document.toxml(encoding="ISO-8859-1"))
    result = ET.tostring(data_document, encoding="ISO-8859-1")

    return result.decode("ISO-8859-1")


def get_response_status_invoice(xml_response):
    _logger.info(xml_response)
    xml_response = set_xml_attributes(xml_response)
    doc = minidom.parseString(xml_response.encode("ISO-8859-1"))
    faultcodes = doc.getElementsByTagName("soap-env:Fault")
    applicationResponse = doc.getElementsByTagName("content")
    faults = doc.getElementsByTagName("ns0:Fault")

    errors = []
    observaciones = []
    success = False
    status = ""
    xml_content = False

    if faultcodes:
        for faultcode in faultcodes:
            stringFault = faultcode.childNodes[0].firstChild.data
            code = faultcode.childNodes[1].firstChild.data
            errors.append({
                "status": 400,
                "code": code,
                "detail": get_error_by_code(code),
                "meta": {
                    "reenvioHabilitado": True,
                    "codigoErrorSUNAT": code,
                    "descripcionErrorSUNAT": stringFault
                }
            })
        status = "N"
    elif applicationResponse:
        zip_data = applicationResponse[0].firstChild.data
        if zip_data:
            zip_decode = base64.b64decode(zip_data)
            zip_file = zipfile.ZipFile(io.BytesIO(zip_decode))
            name = zip_file.infolist()[-1].filename
            xml_read = zip_file.read(name)
            xml_content = xml_read.decode("ISO-8859-1")
            doc_xml = minidom.parseString(xml_content)

            if doc_xml.getElementsByTagName("cac:Response"):
                # referenceID = doc_xml.getElementsByTagName("cbc:ReferenceID")[0].firstChild.data
                responseCode = int(doc_xml.getElementsByTagName(
                    "cbc:ResponseCode")[0].firstChild.data)
                description = doc_xml.getElementsByTagName("cbc:Description")[
                    0].firstChild.data

                notes = []
                if doc_xml.getElementsByTagName("cbc:Note"):
                    for note in doc_xml.getElementsByTagName("cbc:Note"):
                        notes.append(note.firstChild.data)

                if responseCode == 0:
                    success = True
                    status = "A"
                    observaciones = notes
                elif 100 <= responseCode <= 2010:
                    errors.append({
                        "status": 400,
                        "code": "72",
                        "detail": error_list["72"],
                        "meta": {
                            "reenvioHabilitado": True,
                            "estadoEmision": "R",
                            "codigoErrorSUNAT": str(responseCode),
                            "descripcionErrorSUNAT": description,
                            "notas": notes
                        }
                    })
                    status = "R"
                elif responseCode < 4000:
                    errors.append({
                        "status": 400,
                        "code": "72",
                        "detail": error_list["72"],
                        "meta": {
                            "reenvioHabilitado": False,
                            "estadoEmision": "N",
                            "codigoErrorSUNAT": str(responseCode),
                            "descripcionErrorSUNAT": description,
                            "notas": notes
                        }
                    })
                    status = "N"
                else:
                    observaciones.append({
                        "codigo": str(responseCode),
                        "mensaje": description
                    })
                    status = "O"
            else:
                errors.append({
                    "status": 400,
                    "code": "90",
                    "detail": error_list["90"],
                    "XML": xml_response
                })
        else:
            errors.append({
                "status": 400,
                "code": "90",
                "detail": error_list["90"],
                "XML": xml_response
            })
    elif faults:
        for i in range(faults.length):
            code = faults.item(i).getElementsByTagName("faultcode")[0].firstChild.data
            code = int(code.split(":")[1])
            if code == 402:
                errors.append({
                    "status": 400,
                    "code": code,
                    "detail": errores[str(code)],
                    "meta": {
                        "reenvioHabilitado": False,
                        "estadoEmision": "R",
                        "descripcionErrorSUNAT": errores[str(code)],
                        "XML": xml_response
                    }
                })
            elif 100 <= code < 2010:
                errors.append({
                    "status": 400,
                    "code": code,
                    "detail": errores[str(code)],
                    "meta": {
                        "reenvioHabilitado": True,
                        "estadoEmision": "R",
                        "descripcionErrorSUNAT": errores[str(code)],
                        "XML": xml_response
                    }
                })
            elif code >= 2010:
                errors.append({
                    "status": 400,
                    "code": code,
                    "detail": errores[str(code)],
                    "meta": {
                        "reenvioHabilitado": False,
                        "estadoEmision": "R",
                        "descripcionErrorSUNAT": errores[str(code)],
                        "XML": xml_response
                    }
                })
        status = "R"
    else:
        errors.append({
            "status": 400,
            "code": "90",
            "detail": error_list["90"],
            "XML": xml_response
        })

    return {
        "success": success,
        "errors": errors,
        "observaciones": observaciones,
        "status": status,
        "xml_content": xml_content
    }


def get_response(xml_response):
    xml_response = set_xml_attributes(xml_response)
    doc = minidom.parseString(xml_response.encode("ISO-8859-1"))
    faultcodes = doc.getElementsByTagName("soap-env:Fault")
    applicationResponse = doc.getElementsByTagName("applicationResponse")
    faults = doc.getElementsByTagName("soap:Fault")
    # _logger.info("faults")
    # _logger.info(doc)
    # _logger.info(doc.toxml())
    # _logger.info(faults)

    errors = []
    observaciones = []
    success = False
    status = ""
    xml_content = False

    if faultcodes:
        for faultcode in faultcodes:
            stringFault = faultcode.childNodes[0].firstChild.data
            code = faultcode.childNodes[1].firstChild.data
            errors.append({
                "status": 400,
                "code": code,
                "detail": get_error_by_code(code),
                "meta": {
                    "reenvioHabilitado": True,
                    "codigoErrorSUNAT": code,
                    "descripcionErrorSUNAT": stringFault
                }
            })
        status = "N"
    elif applicationResponse:
        zip_data = applicationResponse[0].firstChild.data
        if zip_data:
            zip_decode = base64.b64decode(zip_data)
            zip_file = zipfile.ZipFile(io.BytesIO(zip_decode))
            name = zip_file.infolist()[-1].filename
            xml_read = zip_file.read(name)

            xml_content = set_xml_attributes(xml_read)
            # xml_content = xml_read
            doc_xml = minidom.parseString(xml_content)
            

            if doc_xml.getElementsByTagName("cac:Response"):
                # referenceID = doc_xml.getElementsByTagName("cbc:ReferenceID")[0].firstChild.data
                responseCode = int(doc_xml.getElementsByTagName(
                    "cbc:ResponseCode")[0].firstChild.data)
                description = doc_xml.getElementsByTagName("cbc:Description")[
                    0].firstChild.data

                notes = []
                if doc_xml.getElementsByTagName("cbc:Note"):
                    for note in doc_xml.getElementsByTagName("cbc:Note"):
                        notes.append(note.firstChild.data)

                if responseCode == 0:
                    success = True
                    status = "A"
                    observaciones = notes
                elif 100 <= responseCode <= 2010:
                    errors.append({
                        "status": 400,
                        "code": "72",
                        "detail": error_list["72"],
                        "meta": {
                            "reenvioHabilitado": True,
                            "estadoEmision": "R",
                            "codigoErrorSUNAT": str(responseCode),
                            "descripcionErrorSUNAT": description,
                            "notas": notes
                        }
                    })
                    status = "R"
                elif responseCode < 4000:
                    errors.append({
                        "status": 400,
                        "code": "72",
                        "detail": error_list["72"],
                        "meta": {
                            "reenvioHabilitado": False,
                            "estadoEmision": "N",
                            "codigoErrorSUNAT": str(responseCode),
                            "descripcionErrorSUNAT": description,
                            "notas": notes
                        }
                    })
                    status = "N"
                else:
                    observaciones.append({
                        "codigo": str(responseCode),
                        "mensaje": description
                    })
                    status = "O"
            else:
                errors.append({
                    "status": 400,
                    "code": "90",
                    "detail": error_list["90"],
                    "XML": xml_response
                })
        else:
            errors.append({
                "status": 400,
                "code": "90",
                "detail": error_list["90"],
                "XML": xml_response
            })
    elif faults:
        for i in range(faults.length):
            code = faults.item(i).getElementsByTagName("faultcode")[0].firstChild.data
            if code ==  "S:Server":
                code = faults.item(i).getElementsByTagName("faultstring")[0].firstChild.data
                code = int(code)
            elif "soap-env:Client." in code:
                code = int(code.replace("soap-env:Client.",""))
            elif "soap-env:Server." in code:
                code = int(code.replace("soap-env:Server.",""))
            else:
                code = int(code.split(":")[1])

            if code == 402:
                errors.append({
                    "status": 400,
                    "code": code,
                    "detail": errores[str(code)],
                    "meta": {
                        "reenvioHabilitado": False,
                        "estadoEmision": "R",
                        "descripcionErrorSUNAT": errores[str(code)],
                        "XML": xml_response
                    }
                })
            elif 100 <= code < 2010:
                errors.append({
                    "status": 400,
                    "code": code,
                    "detail": errores[str(code)],
                    "meta": {
                        "reenvioHabilitado": True,
                        "estadoEmision": "R",
                        "descripcionErrorSUNAT": errores[str(code)],
                        "XML": xml_response
                    }
                })
            elif code >= 2010:
                errors.append({
                    "status": 400,
                    "code": code,
                    "detail": errores[str(code)],
                    "meta": {
                        "reenvioHabilitado": False,
                        "estadoEmision": "R",
                        "descripcionErrorSUNAT": errores[str(code)],
                        "XML": xml_response
                    }
                })
        status = "R"
    else:
        errors.append({
            "status": 400,
            "code": "90",
            "detail": error_list["90"],
            "XML": xml_response
        })

    return {
        "success": success,
        "errors": errors,
        "observaciones": observaciones,
        "status": status,
        "xml_content": xml_content
    }


def get_response_ticket(xml_response):
    xml_response = set_xml_attributes(xml_response)
    doc = minidom.parseString(xml_response)
    faultcodes = doc.getElementsByTagName("soap-env:Fault")
    errors = []
    observaciones = []
    dato_ticket = ""
    success = False
    status = ""

    if faultcodes:
        for faultcode in faultcodes:
            code = faultcode.childNodes[0].firstChild.data
            stringFault = faultcode.childNodes[1].firstChild.data
            errors.append({
                "status": 400,
                "code": "72",
                "detail": error_list["72"],
                "meta": {
                    "reenvioHabilitado": True,
                    "codigoErrorSUNAT": code,
                    "descripcionErrorSUNAT": stringFault
                }
            })

        status = "N"
    else:
        ticket = doc.getElementsByTagName("ticket")
        if ticket:
            dato_ticket = ticket[0].firstChild.data
            success = True
            status = "E"
        else:
            errors.append({
                "status": 400,
                "code": "90",
                "detail": error_list["90"],
                "XML": xml_response
            })
            status = "R"

    return {
        "success": success,
        "errors": errors,
        "observaciones": observaciones,
        "status": status,
        "ticket": dato_ticket
    }
