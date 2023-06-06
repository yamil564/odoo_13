from .BasicGlobal import RegistrationName
from .PartyTaxScheme import PartyTaxScheme
from .RegistrationAddress import RegistrationAddress
from .util import Xmleable, default_document


class PartyName(Xmleable):
    def __init__(self, name):
        self.name = name

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PartyName")
        elem_name = default_document.createElement("cbc:Name")
        text = default_document.createCDATASection(self.name)
        elem_name.appendChild(text)
        self.doc.appendChild(elem_name)


class PartyIdentification(Xmleable):
    def __init__(self, id_document, document_type="6", add_attributes=False):
        self.id_document = id_document
        self.document_type = document_type
        self.schemeName = "SUNAT:Identificador de Documento de Identidad"
        self.schemeAgencyName = "PE:SUNAT"
        self.schemeURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06"
        self.add_attributes = add_attributes

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PartyIdentification")
        elem_id = default_document.createElement("cbc:ID")
        elem_id.setAttribute("schemeID", self.document_type)
        if self.add_attributes:
            elem_id.setAttribute("schemeName", self.schemeName)
            elem_id.setAttribute("schemeAgencyName", self.schemeAgencyName)
            elem_id.setAttribute("schemeURI", self.schemeURI)
        text = default_document.createTextNode(self.id_document)
        elem_id.appendChild(text)
        self.doc.appendChild(elem_id)


class PartyLegalEntity(Xmleable):
    def __init__(self, registration_name=None, registration_address=None):
        self.registration_name = registration_name
        self.registration_address = registration_address

    def fix_values(self):
        if type(self.registration_name) == str:
            self.registration_name = RegistrationName(self.registration_name)

    def validate(self, errs, obs):
        assert self.registration_name is None or type(
            self.registration_name) == RegistrationName
        assert self.registration_address is None or type(
            self.registration_address) == RegistrationAddress

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PartyLegalEntity")
        if self.registration_name:
            self.doc.appendChild(self.registration_name.get_document())
        if self.registration_address:
            self.doc.appendChild(self.registration_address.get_document())


class Party(Xmleable):
    def __init__(self, party_name=None, party_legal_entity=None, party_identification=None, party_tax_schema=None):
        self.party_identification = party_identification
        self.party_name = party_name
        self.party_legal_entity = party_legal_entity
        self.party_tax_schema = party_tax_schema

    def fix_values(self):
        if type(self.party_name) == str:
            self.party_name = PartyName(self.party_name)
        if type(self.party_identification) == str:
            self.party_identification = PartyIdentification(self.party_name)

    def validate(self, errs, obs):
        assert self.party_identification is None or type(
            self.party_identification) == PartyIdentification
        assert self.party_name is None or type(self.party_name) == PartyName
        assert self.party_legal_entity is None or type(
            self.party_legal_entity) == PartyLegalEntity
        assert self.party_tax_schema is None or type(
            self.party_tax_schema) is PartyTaxScheme

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Party")
        if self.party_identification:
            self.doc.appendChild(self.party_identification.get_document())
        if self.party_name:
            self.doc.appendChild(self.party_name.get_document())
        if self.party_legal_entity:
            self.doc.appendChild(self.party_legal_entity.get_document())
        if self.party_tax_schema:
            self.doc.appendChild(self.party_tax_schema.get_document())
