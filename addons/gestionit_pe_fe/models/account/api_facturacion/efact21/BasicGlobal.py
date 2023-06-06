from . import Catalogos
from .General import SimpleText
from .util import Xmleable, default_document, createCDataContent, createElementContent


# Datos de factura
class UBLVersion(Xmleable):
    def __init__(self, ubl_version_id="2.1"):
        self.ubl_version_id = ubl_version_id

    def validate(self, errs, obs):
        if self.ubl_version_id not in ["2.0", "2.1"]:
            errs.append({
                "code": 2074,
                "detail": "UBLVersionID - La versión del UBL no es correcta"
            })

    def generate_doc(self):
        self.doc = createElementContent(
            'cbc:UBLVersionID', self.ubl_version_id)


class CustomizationID(Xmleable):
    def __init__(self, customization_id="2.0"):
        self.customization_id = customization_id
        self.schemeAgencyName = "PE:SUNAT"

    def validate(self, errs, obs):
        if self.customization_id not in ["1.0", "1.1", "2.0"]:
            errs.append({
                "code": 2072,
                "detail": "CustomizationID - La versión del documento no es la correcta"
            })

    def generate_doc(self):
        self.doc = createElementContent(
            'cbc:CustomizationID', str(self.customization_id))
        # self.doc.setAttribute("schemeAgencyName", self.schemeAgencyName)


class ID(SimpleText):
    def __init__(self, code_id):
        super(ID, self).__init__(code_id, "cbc:ID")


class SummaryId(Xmleable):
    def __init__(self, summary_id):
        self.summary_id = summary_id

    def generate_doc(self):
        self.doc = createElementContent('cbc:ID', self.summary_id)


class IssueTime(Xmleable):
    def __init__(self, issue_time):
        self.issue_time = issue_time

    def generate_doc(self):
        self.doc = createElementContent('cbc:IssueTime', self.issue_time)


class InvoiceTypeCode(Xmleable):
    def __init__(self, invoice_type_code, listID="0101"):
        self.invoice_type_code = invoice_type_code
        self.listID = listID
        self.listAgencyName = "PE:SUNAT"
        self.listName = "Tipo de Documento"
        self.listURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01"

    def validate(self, errs, obs):
        assert self.invoice_type_code is not None
        if self.invoice_type_code not in Catalogos.catalogo01:
            errs.append({
                "code": 1003,
                "detail": "InvoiceTypeCode - El valor del tipo de documento es invalido"
            })
        if self.listID not in Catalogos.catalogo52:
            errs.append({
                "code": 3206,
                "detail": "El dato ingresado como tipo de operación no corresponde a un valor esperado (catálogo nro. 51)"
            })

    def generate_doc(self):
        self.doc = createElementContent('cbc:InvoiceTypeCode', str(self.invoice_type_code))
        self.doc.setAttribute("listID", self.listID)
        self.doc.setAttribute("listAgencyName", self.listAgencyName)
        self.doc.setAttribute("listName", self.listName)
        self.doc.setAttribute("listURI", self.listURI)


class DocumentCurrencyCode(Xmleable):
    def __init__(self, document_currency_code):
        self.document_currency_code = document_currency_code
        self.listID = "ISO 4217 Alpha"
        self.listName = "Currency"
        self.listAgencyName = "United Nations Economic Commission for Europe"

    def validate(self, errs, obs):
        assert self.document_currency_code is not None
        if self.document_currency_code not in Catalogos.catalogo02_tex:
            errs.append({
                "code": 3088,
                "detail": "El valor ingresado como moneda del comprobante no es valido (catalogo nro 02)."
            })

    def generate_doc(self):
        self.doc = createElementContent(
            'cbc:DocumentCurrencyCode', self.document_currency_code)
        self.doc.setAttribute('listID', self.listID)
        self.doc.setAttribute('listName', self.listName)
        self.doc.setAttribute('listAgencyName', self.listAgencyName)


# End datos de factura

class Note(Xmleable):
    def __init__(self, text, languageLocaleID="1000"):
        self.text = text
        self.languageLocaleID = languageLocaleID  # Catalogo 52

    def generate_doc(self):
        self.doc = createCDataContent('cbc:Note', self.text)
        self.doc.setAttribute("languageLocaleID", self.languageLocaleID)


class LineCountNumeric(Xmleable):
    def __init__(self, count=0):
        self.count = count

    def generate_doc(self):
        self.doc = createElementContent("cbc:LineCountNumeric", self.count)


class UBLExtensions(Xmleable):
    def __init__(self, elem_id="placeholder"):
        self.elem_id = elem_id

    def generate_doc(self):
        self.doc = default_document.createElement("ext:UBLExtensions")
        ublext = default_document.createElement("ext:UBLExtension")
        extcnt = default_document.createElement("ext:ExtensionContent")
        sign = default_document.createElement("ds:Signature")
        sign.setAttribute("Id", self.elem_id)
        extcnt.appendChild(sign)
        ublext.appendChild(extcnt)
        self.doc.appendChild(ublext)


class DocumentNumberID(SimpleText):
    def __init__(self, number_id):
        super(DocumentNumberID, self).__init__(
            number_id, "sac:DocumentNumberID")


class DocumentSerialID(SimpleText):
    def __init__(self, serial_id):
        super(DocumentSerialID, self).__init__(
            serial_id, "sac:DocumentSerialID")


class DocumentTypeCode(SimpleText):
    def __init__(self, type_code):
        super(DocumentTypeCode, self).__init__(
            type_code, "cbc:DocumentTypeCode")


class DespatchAdviceTypeCode(SimpleText):
    def __init__(self, type_code):
        super(DespatchAdviceTypeCode, self).__init__(
            type_code, "cbc:DespatchAdviceTypeCode")


class RegistrationName(Xmleable):
    def __init__(self, registration_name):
        self.registration_name = registration_name

    def generate_doc(self):
        self.doc = createCDataContent(
            "cbc:RegistrationName", self.registration_name)
