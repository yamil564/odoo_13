from .AmountTypes import Amount
from .util import Xmleable, default_document, createElementContent
from .TaxScheme import TaxScheme
from .General import SimpleText


class TaxAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(TaxAmount, self).__init__(
            amount, currencyID, element_name="cbc:TaxAmount")


class TaxableAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(TaxableAmount, self).__init__(
            amount, currencyID, element_name="cbc:TaxableAmount")


class PerUnitAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(PerUnitAmount, self).__init__(
            amount, currencyID, element_name="cbc:PerUnitAmount")


# Catalogo 05
class CategoryID(Xmleable):
    def __init__(self, category_id="S", add_attributes=False):
        self.category_id = category_id
        self.schemeID = "UN/ECE 5305"
        self.schemeName = "Tax Category Identifier"
        self.schemeAgencyName = "United Nations Economic Commission for Europe"
        self.add_attributes = add_attributes

    def generate_doc(self):
        self.doc = createElementContent("cbc:ID", self.category_id)
        if self.add_attributes:
            self.doc.setAttribute("schemeID", self.schemeID)
            self.doc.setAttribute("schemeName", self.schemeName)
            self.doc.setAttribute("schemeAgencyName", self.schemeAgencyName)


class TaxExemptionReasonCode(Xmleable):
    def __init__(self, tax_exemption_reason_code="10", add_attributes=False):
        self.tax_exemption_reason_code = tax_exemption_reason_code
        self.listAgencyName = "PE:SUNAT"
        self.listName = "SUNAT:Codigo de Tipo de Afectación del IGV"
        self.listURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07"
        self.add_attribtutes = add_attributes

    def generate_doc(self):
        self.doc = createElementContent(
            "cbc:TaxExemptionReasonCode", self.tax_exemption_reason_code)
        if self.add_attribtutes:
            self.doc.setAttribute("listAgencyName", self.listAgencyName)
            self.doc.setAttribute("listName", self.listName)
            self.doc.setAttribute("listURI", self.listURI)


class TaxSchemeID(Xmleable):
    def __init__(self, tax_scheme_id, add_attributes=False):
        self.tax_scheme_id = tax_scheme_id
        self.schemeID = "UN/ECE 5153"
        self.schemeAgencyID = "6"
        self.add_attibutes = add_attributes

    def generate_doc(self):
        self.doc = createElementContent("cbc:ID", self.tax_scheme_id)
        if self.add_attibutes:
            self.doc.setAttribute("schemeID", self.schemeID)
            self.doc.setAttribute("schemeAgencyID", self.schemeAgencyID)


class Percent(Xmleable):
    def __init__(self, percent):
        self.percent = percent

    def generate_doc(self):
        self.doc = createElementContent("cbc:Percent", self.percent)


class TaxCategory(Xmleable):
    def __init__(self, category_id=None, percent=None, tax_exemption_reason_code=None, tax_scheme=None, per_unit_amount=None):
        self.category_id = category_id
        self.percent = percent
        self.tax_exemption_reason_code = tax_exemption_reason_code
        self.tax_scheme = tax_scheme
        self.per_unit_amount = per_unit_amount

    def fix_values(self):
        if type(self.category_id) == str:
            self.category_id = CategoryID(self.category_id)
        if type(self.percent) in [float, int]:
            self.percent = Percent(self.percent)
        if type(self.per_unit_amount) in [float, int]:
            self.per_unit_amount = PerUnitAmount(self.per_unit_amount)
        if type(self.tax_exemption_reason_code) == str:
            self.tax_exemption_reason_code = TaxExemptionReasonCode(
                self.tax_exemption_reason_code)

    def validate(self, errs, obs):
        assert self.category_id is None or type(self.category_id) == CategoryID
        assert self.percent is None or type(self.percent) == Percent or self.per_unit_amount is None or type(
            self.per_unit_amount) == PerUnitAmount
        assert self.tax_scheme is None or type(self.tax_scheme) == TaxScheme
        assert self.tax_exemption_reason_code is None or type(
            self.tax_exemption_reason_code) == TaxExemptionReasonCode

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TaxCategory")
        if self.category_id:
            self.doc.appendChild(self.category_id.get_document())
        if self.percent:
            self.doc.appendChild(self.percent.get_document())
        if self.per_unit_amount:
            self.doc.appendChild(self.per_unit_amount.get_document())
        if self.tax_exemption_reason_code:
            self.doc.appendChild(self.tax_exemption_reason_code.get_document())
        if self.tax_scheme:
            self.doc.appendChild(self.tax_scheme.get_document())


class BaseUnitMeasure(Xmleable):
    def __init__(self, quantity, unit_code):
        self.quantity = quantity
        self.unitCode = unit_code  # Catalogo 3
        self.unitCodeListID = "UN/ECE rec 20"
        self.unitCodeListAgencyName = "United Nations Economic Commission forEurope"

    def generate_doc(self):
        self.doc = createElementContent("cbc:BaseUnitMeasure", self.quantity)
        self.doc.setAttribute("unitCode", self.unitCode)


class TaxSubtotal(Xmleable):
    def __init__(self, taxable_amount=None, tax_amount=None, tax_category=None, base_unit_measure=None):
        self.taxable_amount = taxable_amount
        self.tax_amount = tax_amount
        self.tax_category = tax_category
        self.base_unit_measure = base_unit_measure

    def fix_values(self):
        if type(self.taxable_amount) in [float, int]:
            self.taxable_amount = TaxableAmount(self.taxable_amount)
        if type(self.tax_amount) in [float, int]:
            self.tax_amount = TaxAmount(self.tax_amount)

    def validate(self, errs, obs):
        assert self.taxable_amount is None or type(self.taxable_amount) == TaxableAmount or self.base_unit_measure is None or type(
            self.base_unit_measure) == BaseUnitMeasure
        assert self.tax_amount is None or type(self.tax_amount) == TaxAmount
        assert self.tax_category is None or type(
            self.tax_category) == TaxCategory

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TaxSubtotal")
        if self.taxable_amount:
            self.doc.appendChild(self.taxable_amount.get_document())

        if self.tax_amount:
            self.doc.appendChild(self.tax_amount.get_document())
        if self.base_unit_measure:
            self.doc.appendChild(self.base_unit_measure.get_document())
        if self.tax_category:
            self.doc.appendChild(self.tax_category.get_document())


class TaxTotal(Xmleable):
    def __init__(self, tax_amount=None):
        self.tax_amount = tax_amount
        self.taxes_subtotal = []

    def fix_values(self):
        if type(self.tax_amount) in [float, int]:
            self.tax_amount = TaxAmount(self.tax_amount)

    def validate(self, errs, obs):
        if type(self.tax_amount) != TaxAmount:
            raise Exception("Bad type")

    def add_tax_subtotal(self, tax_subtotal):
        assert type(tax_subtotal) == TaxSubtotal
        self.taxes_subtotal.append(tax_subtotal)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TaxTotal")
        self.doc.appendChild(self.tax_amount.get_document())
        for tax_subtotal in self.taxes_subtotal:
            self.doc.appendChild(tax_subtotal.get_document())
