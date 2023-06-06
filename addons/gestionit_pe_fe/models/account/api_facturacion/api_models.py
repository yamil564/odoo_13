from .controllers import main
from .efact21.Documents import ComunicacionBaja
from .lista_errores import errores
import random
from xml.dom import minidom
import logging
import base64
import zipfile
import io
import os
_logger = logging.getLogger(__name__)


def random_string(l):
    def to_char(x):
        if x < 10:
            return chr(48 + x)
        if x < 36:
            return chr(55 + x)
        return chr(61 + x)

    return "".join([to_char(random.randint(0, 61)) for _ in range(l)])


def lamdba(data):
    credentials = {
        "ruc": data["company"]["numDocEmisor"],
        'razon_social': data["company"]["nombreEmisor"],
        'usuario': data["company"]["SUNAT_user"],
        'password': data["company"]["SUNAT_pass"],
        'key_private': data["company"]["key_private"],
        'key_public': data["company"]["key_public"],
    }

    main_xml = main.handle(data, credentials)

    request_id = random_string(20)

    if data["tipoEnvio"] == 0:
        request_id = "test/%s" % (request_id)

    ans = {
        'request_id': request_id
    }
    ans.update(main_xml)

    resp = main.send_xml_sunat(ans, data)

    ans["token"] = resp.get("token")
    ans['sunat_observaciones'] = resp.get('observaciones', [])

    ans['sunat_errors'] = resp.get('errors', [])
    ans['sunat_status'] = resp.get('status', "-")
    if resp.get("ticket", False):
        ans['ticket'] = resp['ticket']

    ans['response_xml'] = resp.get('response_xml')
    if resp.get("xml_content", None):
        ans['response_content_xml'] = resp['xml_content']

    return ans


def consultaResumen(data):
    credentials = {
        "ruc": data["company"]["numDocEmisor"],
        'razon_social': data["company"]["nombreEmisor"],
        'usuario': data["company"]["SUNAT_user"],
        'password': data["company"]["SUNAT_pass"],
        'key_private': data["company"]["key_private"],
        'key_public': data["company"]["key_public"],
    }

    comb = ComunicacionBaja()
    errors = []
    ruc = data["company"]["numDocEmisor"]

    if not ruc:
        errors.append("El ruc es obligatorio")

    ticket = data["ticket"]
    if not ticket:
        errors.append("El ticket es obligatorio")

    user = data["company"]["SUNAT_user"]
    password = data["company"]["SUNAT_pass"]

    username = str(ruc) + user

    if len(errors) > 0:
        return {
            "error": errors,
            "data": data
        }

    tipoEnvio = data["tipoEnvio"]
    status = comb.getStatus(username, password, ticket)

    response = main.send_consulta(
        status.toprettyxml("  "), data=data, user=user)

    doc = minidom.parseString(response.encode("ISO-8859-1"))

    fault = doc.getElementsByTagName("faultcode")
    if fault:
        faultcode = doc.getElementsByTagName(
            "faultcode")[0].firstChild.data
        try:
            faultstring = errores[str(int(faultcode))]
        except Exception as e:
            faultstring = doc.getElementsByTagName(
                "faultstring")[0].firstChild.data

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
        if statusCode in ["0", "99"]:
            content = doc.getElementsByTagName("content")
            zip_data = content[0].firstChild.data
            zip_decode = base64.b64decode(zip_data)
            zip_file = zipfile.ZipFile(io.BytesIO(zip_decode))

            xml_read = zip_file.read(zip_file.namelist()[-1])
            os.system("echo '%s'" % (xml_read))
            doc_xml = minidom.parseString(xml_read)
            DocumentResponse = doc_xml.getElementsByTagName(
                "cac:DocumentResponse")
            if DocumentResponse:
                Description = DocumentResponse[0].getElementsByTagName("cbc:Description")[
                    0].firstChild.data
                ResponseCode = DocumentResponse[0].getElementsByTagName("cbc:ResponseCode")[
                    0].firstChild.data
                ReferenceID = DocumentResponse[0].getElementsByTagName("cbc:ReferenceID")[
                    0].firstChild.data
                Description = ResponseCode+" - " + \
                    (Description if Description else errores.get(
                        str(int(ResponseCode), "")))
            if statusCode == "0":
                cdr = doc_xml.toprettyxml("        ")
                Description = doc_xml.getElementsByTagName("cbc:Description")[
                    0].firstChild.data
                digestValue = doc_xml.getElementsByTagName("DigestValue")[
                    0].firstChild.data
                status = "A"
            elif statusCode == "99":
                status = "R"

        elif statusCode == "98":
            Description = "En Proceso"
            status = "P"
        else:
            status = False
            Description = doc.getElementsByTagName("statusMessage")
            if not Description:
                Description = errores[str(int(statusCode))]
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
