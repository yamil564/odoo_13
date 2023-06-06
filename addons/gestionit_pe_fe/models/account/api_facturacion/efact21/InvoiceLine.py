from .TaxTotal import TaxTotal
from .util import Xmleable, default_document, createElementContent
from .AmountTypes import LineExtensionAmount
from .Lines import PricingReference, Item, Price
from .AllowanceCharge import AllowanceCharge 


class InvoicedQuantity(Xmleable):
    def __init__(self, quantity, unit_code):
        self.quantity = quantity
        self.unitCode = unit_code  # Catalogo 3
        self.unitCodeListID = "UN/ECE rec 20"
        self.unitCodeListAgencyName = "United Nations Economic Commission forEurope"

    def generate_doc(self):
        self.doc = createElementContent("cbc:InvoicedQuantity", self.quantity)
        self.doc.setAttribute("unitCode", self.unitCode)
        # self.doc.setAttribute("unitCodeListID", self.unitCodeListID)
        # self.doc.setAttribute("unitCodeListAgencyName",self.unitCodeListAgencyName)


class InvoiceLine(Xmleable):
    def __init__(self, ord=0, invoice_quantity=None, line_extension_amount=None,
                 pricing_reference=None, tax_total=None, item=None, price=None,descuento=None):
        self.ord = ord
        self.invoice_quantity = invoice_quantity
        self.line_extension_amount = line_extension_amount
        self.pricing_reference = pricing_reference
        self.tax_total = tax_total
        self.item = item
        self.price = price
        self.descuento = descuento


    def validate(self, errs, obs):
        if type(self.invoice_quantity) != InvoicedQuantity:
            raise Exception("Bad type")
        if type(self.line_extension_amount) == float:
            self.line_extension_amount = LineExtensionAmount(
                self.line_extension_amount)
        if type(self.line_extension_amount) != LineExtensionAmount:
            raise Exception("Bad type")
        if type(self.pricing_reference) != PricingReference:
            raise Exception("Bad type")
        if type(self.tax_total) != TaxTotal:
            raise Exception("Bad type")
        if type(self.item) == str:
            self.item = Item(self.item)
        if type(self.item) != Item:
            raise Exception("Bad type")
        if type(self.price) == float:
            self.price = Price(self.price)
        if type(self.price) != Price:
            raise Exception("Bad type")
        if self.descuento:
            if type(self.descuento) != AllowanceCharge:
                raise Exception("Bad type")

    def generate_id(self):
        return createElementContent("cbc:ID", self.ord)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:InvoiceLine")
        self.doc.appendChild(self.generate_id())
        self.doc.appendChild(self.invoice_quantity.get_document())
        self.doc.appendChild(self.line_extension_amount.get_document())
        self.doc.appendChild(self.pricing_reference.get_document())
        if self.descuento:
            self.doc.appendChild(self.descuento.get_document())
        self.doc.appendChild(self.tax_total.get_document())
        self.doc.appendChild(self.item.get_document())
        self.doc.appendChild(self.price.get_document())
