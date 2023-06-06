from . import BasicGlobal
from .util import Xmleable, default_document


class InvoiceDocumentReference(Xmleable):
    def __init__(self, cod_id=None, document_type_code=None):
        self.code_id = cod_id
        self.document_type_code = document_type_code

    def fix_values(self):
        if type(self.code_id) == str:
            self.code_id = BasicGlobal.ID(self.code_id)
        if type(self.document_type_code) == str:
            self.document_type_code = BasicGlobal.DocumentTypeCode(
                self.document_type_code)

    def generate_doc(self):
        self.doc = default_document.createElement(
            "cac:InvoiceDocumentReference")
        self.doc.appendChild(self.code_id.get_document())
        self.doc.appendChild(self.document_type_code.get_document())


class BillingReference(Xmleable):
    def __init__(self, invoice_document_reference=None):
        self.invoice_document_reference = invoice_document_reference

    def validate(self, errs, obs):
        assert type(self.invoice_document_reference) == InvoiceDocumentReference

    def generate_doc(self):
        self.doc = default_document.createElement("cac:BillingReference")
        self.doc.appendChild(self.invoice_document_reference.get_document())
