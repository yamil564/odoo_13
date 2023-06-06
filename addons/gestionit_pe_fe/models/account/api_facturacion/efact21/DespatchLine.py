from .util import Xmleable, createElementContent, default_document
from . import BasicGlobal
from .Lines import Item


class DeliveredQuantity(Xmleable):
    def __init__(self, quantity=1, unit_code="KGM"):
        self.quantity = quantity
        self.unitCode = unit_code

    def generate_doc(self):
        self.doc = createElementContent("cbc:DeliveredQuantity", self.quantity)
        if self.unitCode:
            self.doc.setAttribute("unitCode", self.unitCode)


class OrderLineReference(Xmleable):
    def __init__(self, order_line=1):
        self.order_line = order_line

    def generate_doc(self):
        self.doc = default_document.createElement("cac:OrderLineReference")
        self.doc.appendChild(createElementContent("cbc:LineID", self.order_line))


class DespatchLine(Xmleable):
    def __init__(self, ord=0, delivered_quantity=None, order_line_reference=None, item=None):
        self.ord = ord
        self.delivered_quantity = delivered_quantity
        self.order_line_reference = order_line_reference
        self.item = item

    def fix_values(self):
        if type(self.ord) == int:
            self.ord = BasicGlobal.ID(self.ord)

    def validate(self, erros, observs):
        assert type(self.ord) == BasicGlobal.ID
        assert type(self.delivered_quantity) == DeliveredQuantity
        assert type(self.order_line_reference) == OrderLineReference
        assert type(self.item) == Item

    def generate_doc(self):
        self.doc = default_document.createElement("cac:DespatchLine")
        self.doc.appendChild(self.ord.get_document())
        self.doc.appendChild(self.delivered_quantity.get_document())
        self.doc.appendChild(self.order_line_reference.get_document())
        self.doc.appendChild(self.item.get_document())
