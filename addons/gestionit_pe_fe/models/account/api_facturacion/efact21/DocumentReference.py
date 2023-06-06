from .util import Xmleable, default_document


class ID(Xmleable):
    def __init__(self, id):
        self.id = id

    def generate_doc(self):
        self.doc = default_document.createElement('cbc:ID')
        text = default_document.createTextNode(self.id)
        self.doc.appendChild(text)


# Catalogo 12
class DocumentTypeCode(Xmleable):
    def __init__(self, document_type_code):
        self.document_type_code = document_type_code
        self.listName = "Documento Relacionado"
        self.listAgencyName = "PE:SUNAT"
        self.listURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo12"

    def generate_doc(self):
        self.doc = default_document.createElement("cbc:DocumentTypeCode")
        self.doc.setAttribute('listName', self.listName)
        self.doc.setAttribute('listAgencyName', self.listAgencyName)
        self.doc.setAttribute('listURI', self.listURI)

        text = default_document.createTextNode(self.document_type_code)
        self.doc.appendChild(text)


class AdditionalDocumentReference(Xmleable):
    def __init__(self, id, document_type_code=None):
        self.id = ID(id)
        self.document_type_code = document_type_code

    def fix_values(self):
        if type(self.document_type_code) == str:
            self.document_type_code = DocumentTypeCode(self.document_type_code)

    def validate(self, errs, obs):
        assert self.document_type_code is None or type(self.document_type_code) == DocumentTypeCode

    def generate_doc(self):
        self.doc = default_document.createElement("cac:AdditionalDocumentReference")
        self.doc.appendChild(self.id.get_document())
        if self.document_type_code:
            self.doc.appendChild(self.document_type_code.get_document())
        return self.doc


class DespatchDocumentReference(Xmleable):
    def __init__(self, id, document_type_code=None):
        self.id = ID(id)
        self.document_type_code = document_type_code

    def fix_values(self):
        if type(self.document_type_code) == str:
            self.document_type_code = DocumentTypeCode(self.document_type_code)

    def validate(self, errs, obs):
        assert self.document_type_code is None or type(self.document_type_code) == DocumentTypeCode

    def generate_doc(self):
        self.doc = default_document.createElement("cac:DespatchDocumentReference")
        self.doc.appendChild(self.id.get_document())
        if self.document_type_code:
            self.doc.appendChild(self.document_type_code.get_document())
        return self.doc
