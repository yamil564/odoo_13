from signxml import XMLSigner, XMLVerifier, methods
import xml.etree.ElementTree as ET
from ..efact21 import Signature
from ..efact21 import Envelope
import sys
import zipfile
import io
import base64
from xml.dom import minidom
import os
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


def firmar(document, signer, key, cert):

    document.signature = Signature.Signature(
        signer["ruc"],
        signer['ruc'],
        signer['razon_social']
    )

    data_document = document.get_document()

    namespaces = {}
    for k, v in data_document.childNodes[0].attributes.items():
        k = k.replace("xmlns", "").split(":")[-1]
        ET.register_namespace(k, v)
        if k:
            namespaces[k] = v
    data_unsigned = ET.fromstring(data_document.toxml(encoding="ISO-8859-1").decode("ISO-8859-1"))

    # try:
    #     XMLSigner(
    #         method=methods.enveloped,
    #         digest_algorithm='sha1',
    #         c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
    #     ).sign(data_unsigned, key=key.encode(), cert=cert.encode())
    # except ValueError as err:
    #     _logger.info("OS error: {0}".format(err))
    # _logger.info(XMLSigner().sign(
    #     data_unsigned, key=key.encode(), cert=cert.encode()))

    signed_root = XMLSigner(
        method=methods.enveloped,
        digest_algorithm='sha1',
        c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
    ).sign(data_unsigned, key=key.encode(), cert=cert.encode())

    for x in signed_root[0]:
        tag = x.tag.split("}")[-1]
        if tag == "UBLExtension":
            x[0][0].set("Id", "SignatureMT")
            break

    return ET.tostring(signed_root, encoding="ISO-8859-1")
    # return ET.tostring(data_unsigned, encoding="ISO-8859-1")


def get_digest_value(xml_binary_content):
    try:
        doc = minidom.parseString(xml_binary_content.decode('ISO-8859-1'))
        digestvaluenode = doc.getElementsByTagName("ds:DigestValue")
        if digestvaluenode:
            digestvalue = digestvaluenode[0].firstChild.data
    except Exception as e:
        digestvalue = False

    return digestvalue


def zipear(xml_binary_content, name_file):
    in_memory_zip = io.BytesIO()
    zf = zipfile.ZipFile(in_memory_zip, "w")
    try:
        zf.writestr(name_file, xml_binary_content)
        zf.close()
    except Exception as e:
        raise e
    # _logger.info("zf.filename")
    # _logger.info(zf.filename)
    in_memory_zip.seek(0)
    data_file = in_memory_zip.read()
    documentoZip = base64.b64encode(data_file)
    return documentoZip


def generate_envio_xml(username, password, file_name, doc_zip):
    header = Envelope.Header(username, password)
    body = Envelope.Body(file_name, doc_zip)
    envelope = Envelope.Envelope(header, body)
    return envelope.get_document().toxml()


def generate_envio_resumen_xml(username, password, file_name, doc_zip):
    header = Envelope.Header(username, password)
    body = Envelope.BodyResumen(file_name, doc_zip)
    envelope = Envelope.Envelope(header, body)
    return envelope.get_document().toxml()
