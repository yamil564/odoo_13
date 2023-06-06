from .BasicGlobal import RegistrationName
from .RegistrationAddress import RegistrationAddress
from .TaxScheme import TaxScheme
from .util import Xmleable, default_document


class CompanyID(Xmleable):
    def __init__(self, id_document, document_type=6):
        self.id_document = id_document
        self.document_type = document_type
        self.schemeName = "SUNAT:Identificador de Documento de Identidad"
        self.schemeAgencyName = "PE:SUNAT"
        self.schemeURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06"

    def generate_doc(self):
        self.doc = default_document.createElement("cbc:CompanyID")
        self.doc.setAttribute("schemeID", self.document_type)
        self.doc.setAttribute("schemeName", self.schemeName)
        self.doc.setAttribute("schemeAgencyName", self.schemeAgencyName)
        self.doc.setAttribute("schemeURI", self.schemeURI)
        text = default_document.createTextNode(self.id_document)
        self.doc.appendChild(text)


class PartyTaxScheme(Xmleable):
    def __init__(self, registration_name=None, company_id=None,
                 registration_address=None, tax_scheme=None):
        self.registration_name = registration_name
        self.company_id = company_id
        self.registration_address = registration_address
        self.tax_scheme = tax_scheme

    def fix_values(self):
        if type(self.registration_name) == str:
            self.registration_name = RegistrationName(self.registration_name)
        if type(self.company_id) == str:
            self.company_id = CompanyID(id_document=self.company_id)
        if type(self.registration_address) == str:
            self.registration_address = RegistrationAddress(
                address_type_code=self.registration_address)
        # if self.tax_scheme is None:
        #     self.tax_scheme = TaxScheme.TaxScheme("-")

    def validate(self, errs, obs):
        assert self.registration_name is None or type(
            self.registration_name) == RegistrationName
        assert self.company_id is None or type(self.company_id) == CompanyID
        assert self.registration_address is None or type(
            self.registration_address) == RegistrationAddress
        assert self.tax_scheme is None or type(self.tax_scheme) == TaxScheme

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PartyTaxScheme")
        self.doc.appendChild(self.registration_name.get_document())
        self.doc.appendChild(self.company_id.get_document())
        if self.registration_address:
            self.doc.appendChild(self.registration_address.get_document())
        if self.tax_scheme:
            self.doc.appendChild(self.tax_scheme.get_document())
