from .util import Xmleable, default_document, createElementContent
from .BasicGlobal import DocumentTypeCode, DocumentSerialID, DocumentNumberID
from .General import SimpleText


class LineID(SimpleText):
    def __init__(self, id):
        super(LineID, self).__init__(id, "cbc:LineID")


class VoidReasonDescription(SimpleText):
    def __init__(self, void_reason_description):
        super(VoidReasonDescription, self).__init__(
            void_reason_description, "sac:VoidReasonDescription")


class VoidedDocumentsLine(Xmleable):
    def __init__(self, document_type_code=None, document_serial_id=None,
                 document_number_id=None, void_reason_description=None, line_id=None):
        self.line_id = line_id
        self.document_type_code = document_type_code
        self.document_serial_id = document_serial_id
        self.document_number_id = document_number_id
        self.void_reason_description = void_reason_description

    def fix_values(self):
        if type(self.line_id) in [str, int]:
            self.line_id = LineID(self.line_id)
        if type(self.document_type_code) == str:
            self.document_type_code = DocumentTypeCode(self.document_type_code)
        if type(self.document_serial_id) == str:
            self.document_serial_id = DocumentSerialID(self.document_serial_id)
        if type(self.document_number_id) in [int, str]:
            self.document_number_id = DocumentNumberID(self.document_number_id)
        if type(self.void_reason_description) == str:
            self.void_reason_description = VoidReasonDescription(
                self.void_reason_description)

    def validate(self, errs, obs):
        assert type(self.line_id) == LineID
        assert type(self.document_type_code) == DocumentTypeCode
        assert type(self.document_serial_id) == DocumentSerialID
        assert type(self.document_number_id) == DocumentNumberID
        assert type(self.void_reason_description) == VoidReasonDescription

    def generate_doc(self):
        self.doc = default_document.createElement("sac:VoidedDocumentsLine")
        self.doc.appendChild(self.line_id.get_document())
        self.doc.appendChild(self.document_type_code.get_document())
        self.doc.appendChild(self.document_serial_id.get_document())
        self.doc.appendChild(self.document_number_id.get_document())
        self.doc.appendChild(self.void_reason_description.get_document())
