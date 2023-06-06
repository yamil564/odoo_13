from .AmountTypes import LineExtensionAmount, TaxInclusiveAmount, PrepaidAmount
from .AmountTypes import PayableAmount, AllowanceTotalAmount, ChargeTotalAmount
from .AmountTypes import PayableRoundingAmount
from .util import Xmleable, default_document


class LegalMonetaryTotal(Xmleable):
    def __init__(self, line_extension_amount=None, prepaid_amount=None,
                 payable_amount=None, allowance_total_amount=None,
                 charge_total_amount=None, tax_inclusive_amount=None):
        self.line_extension_amount = line_extension_amount
        self.tax_inclusive_amount = tax_inclusive_amount
        self.allowance_total_amount = allowance_total_amount
        self.charge_total_amount = charge_total_amount
        self.prepaid_amount = prepaid_amount
        self.payable_amount = payable_amount

    def fix_values(self):
        if type(self.line_extension_amount) in [float, int]:
            self.line_extension_amount = LineExtensionAmount(
                self.line_extension_amount)
        if type(self.tax_inclusive_amount) in [float, int]:
            self.tax_inclusive_amount = TaxInclusiveAmount(
                self.tax_inclusive_amount)
        if type(self.prepaid_amount) in [float, int]:
            self.prepaid_amount = PrepaidAmount(self.prepaid_amount)
        if type(self.payable_amount) in [float, int]:
            self.payable_amount = PayableAmount(self.payable_amount)
        if type(self.allowance_total_amount) in [float, int]:
            self.allowance_total_amount = AllowanceTotalAmount(
                self.allowance_total_amount)
        if type(self.charge_total_amount) in [float, int]:
            self.charge_total_amount = AllowanceTotalAmount(
                self.charge_total_amount)

    def validate(self, errs, obs):
        assert self.prepaid_amount is None or type(
            self.prepaid_amount) == PrepaidAmount
        assert self.payable_amount is None or type(
            self.payable_amount) == PayableAmount
        assert self.line_extension_amount is None or type(
            self.line_extension_amount) == LineExtensionAmount
        assert self.tax_inclusive_amount is None or type(
            self.tax_inclusive_amount) == TaxInclusiveAmount
        assert self.allowance_total_amount is None or type(
            self.allowance_total_amount) == AllowanceTotalAmount
        assert self.charge_total_amount is None or type(
            self.charge_total_amount) == ChargeTotalAmount

    def generate_doc(self):
        self.doc = default_document.createElement("cac:LegalMonetaryTotal")
        if self.line_extension_amount:
            self.doc.appendChild(self.line_extension_amount.get_document())
        if self.tax_inclusive_amount:
            self.doc.appendChild(self.tax_inclusive_amount.get_document())
        if self.allowance_total_amount:
            self.doc.appendChild(self.allowance_total_amount.get_document())
        if self.charge_total_amount:
            self.doc.appendChild(self.charge_total_amount.get_document())
        if self.prepaid_amount:
            self.doc.appendChild(self.prepaid_amount.get_document())
        if self.payable_amount:
            self.doc.appendChild(self.payable_amount.get_document())


class RequestedMonetaryTotal(Xmleable):
    def __init__(self, line_extension_amount=None, prepaid_amount=None,
                 payable_amount=None, allowance_total_amount=None,
                 charge_total_amount=None, tax_inclusive_amount=None,
                 payable_rounding_amount=None):
        self.line_extension_amount = line_extension_amount
        self.tax_inclusive_amount = tax_inclusive_amount
        self.allowance_total_amount = allowance_total_amount
        self.charge_total_amount = charge_total_amount
        self.prepaid_amount = prepaid_amount
        self.payable_amount = payable_amount
        self.payable_rounding_amount = payable_rounding_amount

    def fix_values(self):
        if type(self.line_extension_amount) in [float, int]:
            self.line_extension_amount = LineExtensionAmount(
                self.line_extension_amount)
        if type(self.tax_inclusive_amount) in [float, int]:
            self.tax_inclusive_amount = TaxInclusiveAmount(
                self.tax_inclusive_amount)
        if type(self.prepaid_amount) in [float, int]:
            self.prepaid_amount = PrepaidAmount(self.prepaid_amount)
        if type(self.payable_amount) in [float, int]:
            self.payable_amount = PayableAmount(self.payable_amount)
        if type(self.allowance_total_amount) in [float, int]:
            self.allowance_total_amount = AllowanceTotalAmount(
                self.allowance_total_amount)
        if type(self.charge_total_amount) in [float, int]:
            self.charge_total_amount = AllowanceTotalAmount(
                self.charge_total_amount)
        if type(self.payable_rounding_amount) in [float, int]:
            self.payable_rounding_amount = PayableRoundingAmount(
                self.payable_rounding_amount)

    def validate(self, errs, obs):
        assert self.prepaid_amount is None or type(
            self.prepaid_amount) == PrepaidAmount
        assert self.payable_amount is None or type(
            self.payable_amount) == PayableAmount
        assert self.line_extension_amount is None or type(
            self.line_extension_amount) == LineExtensionAmount
        assert self.tax_inclusive_amount is None or type(
            self.tax_inclusive_amount) == TaxInclusiveAmount
        assert self.allowance_total_amount is None or type(
            self.allowance_total_amount) == AllowanceTotalAmount
        assert self.charge_total_amount is None or type(
            self.charge_total_amount) == ChargeTotalAmount
        assert self.payable_rounding_amount is None or type(
            self.payable_rounding_amount) == PayableRoundingAmount

    def generate_doc(self):
        self.doc = default_document.createElement("cac:RequestedMonetaryTotal")
        if self.line_extension_amount:
            self.doc.appendChild(self.line_extension_amount.get_document())
        if self.tax_inclusive_amount:
            self.doc.appendChild(self.tax_inclusive_amount.get_document())
        if self.allowance_total_amount:
            self.doc.appendChild(self.allowance_total_amount.get_document())
        if self.charge_total_amount:
            self.doc.appendChild(self.charge_total_amount.get_document())
        if self.prepaid_amount:
            self.doc.appendChild(self.prepaid_amount.get_document())
        if self.payable_amount:
            self.doc.appendChild(self.payable_amount.get_document())
        if self.payable_rounding_amount:
            self.doc.appendChild(self.payable_rounding_amount.get_document())
