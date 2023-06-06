from .util import Xmleable, default_document, createElementContent


# Catalogo5
class TaxSchemeID(Xmleable):
    def __init__(self, id, add_attributes=False):
        self.id = id
        self.schemeURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05"
        self.schemeName = "Codigo de tributos"
        self.schemeAgencyName = "PE:SUNAT"
        self.add_attributes = add_attributes

    def generate_doc(self):
        self.doc = createElementContent("cbc:ID", self.id)
        if self.add_attributes:
            self.doc.setAttribute("schemeURI", self.schemeURI)
            self.doc.setAttribute("schemeName", self.schemeName)
            self.doc.setAttribute("schemeAgencyName", self.schemeAgencyName)


class TaxScheme(Xmleable):
    def __init__(self, tax_scheme_id, name=None, code=None):
        self.tax_id = tax_scheme_id
        self.name = name
        self.code = code

    def fix_values(self):
        if type(self.tax_id) == str:
            self.tax_id = TaxSchemeID(self.tax_id)

    def validate(self, errs, obs):
        assert type(self.tax_id) == TaxSchemeID

    def generate_name(self):
        return createElementContent("cbc:Name", self.name)

    def generate_code(self):
        return createElementContent("cbc:TaxTypeCode", self.code)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TaxScheme")
        self.doc.appendChild(self.tax_id.get_document())
        if self.name:
            self.doc.appendChild(self.generate_name())
        if self.code:
            self.doc.appendChild(self.generate_code())
