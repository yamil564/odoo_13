from .BasicGlobal import ID
from .util import Xmleable, default_document, createElementContent


class OrderTypeCode(Xmleable):
    def __init__(self, code=None, name="Guía de Remisión"):
        self.code = code
        self.name = name

    def generate_doc(self):
        self.doc = createElementContent("cbc:OrderTypeCode", self.code)
        self.doc.setAttribute("name", self.name)


class OrderReference(Xmleable):
    def __init__(self, order_reference_id=None, order_type_code=None,order_type_code_required=True):
        self.order_reference_id = order_reference_id
        self.order_type_code = order_type_code
        self.order_type_code_required = order_type_code_required

    def fix_values(self):
        if type(self.order_reference_id) == str:
            self.order_reference_id = ID(self.order_reference_id)
        if type(self.order_type_code) == str and self.order_type_code_required:
            self.order_type_code = OrderTypeCode(self.order_type_code)

    def validate(self, erros, observs):
        assert type(self.order_reference_id) == ID
        if self.order_type_code_required:
            assert type(self.order_type_code) == OrderTypeCode 

    def generate_doc(self):
        self.doc = default_document.createElement("cac:OrderReference")
        self.doc.appendChild(self.order_reference_id.get_document())
        if self.order_type_code_required:
            self.doc.appendChild(self.order_type_code.get_document())


