from . import BasicGlobal
from .General import SimpleText
from .util import Xmleable, default_document
from .AmountTypes import LineExtensionAmount
from .Lines import PricingReference, Item, Price
from .TaxTotal import TaxTotal


class CreditedQuantity(SimpleText):
    def __init__(self, quantity, unit_code="NIU"):
        super(CreditedQuantity, self).__init__(quantity, "cbc:CreditedQuantity", {"unitCode": unit_code})


class CreditNoteLine(Xmleable):
    def __init__(self, ord=0, credit_quantity=None, line_extension_amount=None,
                 pricing_reference=None, tax_total=None, item=None, price=None):
        self.ord = ord
        self.credit_quantity = credit_quantity
        self.line_extension_amount = line_extension_amount
        self.pricing_reference = pricing_reference
        self.tax_total = tax_total
        self.item = item
        self.price = price

    def fix_values(self):
        if type(self.ord) == int:
            self.ord = BasicGlobal.ID(self.ord)
        if type(self.credit_quantity) in [int, str]:
            self.credit_quantity = CreditedQuantity(self.credit_quantity)
        if type(self.line_extension_amount) in [int, float]:
            self.line_extension_amount = LineExtensionAmount(self.line_extension_amount)

    def validate(self, errs, obs):
        assert type(self.ord) == BasicGlobal.ID
        assert type(self.credit_quantity) == CreditedQuantity
        assert type(self.pricing_reference) == PricingReference
        assert type(self.tax_total) == TaxTotal
        assert type(self.item) == Item
        assert type(self.price) == Price
        assert type(self.line_extension_amount) == LineExtensionAmount

    def generate_doc(self):
        self.doc = default_document.createElement("cac:CreditNoteLine")
        self.doc.appendChild(self.ord.get_document())
        self.doc.appendChild(self.credit_quantity.get_document())
        self.doc.appendChild(self.line_extension_amount.get_document())
        self.doc.appendChild(self.pricing_reference.get_document())
        self.doc.appendChild(self.tax_total.get_document())
        self.doc.appendChild(self.item.get_document())
        self.doc.appendChild(self.price.get_document())
