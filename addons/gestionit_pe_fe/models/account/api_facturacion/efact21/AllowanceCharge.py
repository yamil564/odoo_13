from .util import Xmleable, default_document, createCDataContent, createElementContent
from .AmountTypes import Amount, BaseAmount


class ChargeIndicator(Xmleable):
    def __init__(self, charge_indicator):
        self.charge_indicator = charge_indicator

    def validate(self, errs, obs):
        assert type(self.charge_indicator) == str

    def fix_values(self):
        if type(self.charge_indicator) == bool:
            self.charge_indicator = "true" if self.charge_indicator else "false"

    def generate_doc(self):
        self.doc = createElementContent(
            "cbc:ChargeIndicator", self.charge_indicator)


class AllowanceChargeReasonCode(Xmleable):
    def __init__(self, allowance_charge_reason_code):
        self.allowance_charge_reason_code = allowance_charge_reason_code

    def validate(self, errs, obs):
        assert type(self.allowance_charge_reason_code) == str
        assert self.allowance_charge_reason_code in ["00", "01", "02","62"]

    def generate_doc(self):
        self.doc = createElementContent(
            "cbc:AllowanceChargeReasonCode", self.allowance_charge_reason_code)


class MultiplierFactorNumeric(Xmleable):
    def __init__(self, multiplier_factor_numeric):
        self.multiplier_factor_numeric = multiplier_factor_numeric

    def validate(self, errs, obs):
        assert type(self.multiplier_factor_numeric) == float

    def fix_values(self):
        if type(self.multiplier_factor_numeric) == str:
            self.multiplier_factor_numeric = float(
                self.multiplier_factor_numeric)

    def generate_doc(self):
        self.doc = createElementContent(
            "cbc:MultiplierFactorNumeric", self.multiplier_factor_numeric)


class AllowanceCharge(Xmleable):
    def __init__(self, charge_indicator, allowance_charge_reason_code,
                 multiplier_factor_numeric, amount, base_amount, currency_id):
        self.charge_indicator = charge_indicator
        self.allowance_charge_reason_code = allowance_charge_reason_code
        self.multiplier_factor_numeric = multiplier_factor_numeric
        self.amount = amount
        self.base_amount = base_amount
        self.currency_id = currency_id

    def fix_values(self):
        if type(self.charge_indicator) == bool:
            self.charge_indicator = ChargeIndicator(
                "true" if self.charge_indicator else "false")
        if self.allowance_charge_reason_code in ["00", "01", "02","62"]:
            self.allowance_charge_reason_code = AllowanceChargeReasonCode(
                self.allowance_charge_reason_code)
        if type(self.multiplier_factor_numeric) == float:
            self.multiplier_factor_numeric = MultiplierFactorNumeric(
                self.multiplier_factor_numeric)
        if type(self.amount) in [float, int]:
            self.amount = Amount(self.amount, self.currency_id)
        if type(self.base_amount) in [float, int]:
            self.base_amount = BaseAmount(self.base_amount, self.currency_id)

    def validate(self, errs, obs):
        assert type(self.charge_indicator) == ChargeIndicator
        assert type(
            self.allowance_charge_reason_code) == AllowanceChargeReasonCode
        assert type(self.multiplier_factor_numeric) == MultiplierFactorNumeric
        assert type(self.amount) == Amount
        assert type(self.base_amount) == BaseAmount

    def generate_doc(self):
        self.doc = default_document.createElement("cac:AllowanceCharge")
        self.doc.appendChild(self.charge_indicator.get_document())
        self.doc.appendChild(self.allowance_charge_reason_code.get_document())
        self.doc.appendChild(self.multiplier_factor_numeric.get_document())
        self.doc.appendChild(self.amount.get_document())
        self.doc.appendChild(self.base_amount.get_document())
