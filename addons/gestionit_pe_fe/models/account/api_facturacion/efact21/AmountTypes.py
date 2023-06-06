from .util import Xmleable, createElementContent


class Amount(Xmleable):
    def __init__(self, amount, currencyID="PEN", element_name="cbc:Amount"):
        self.amount = amount
        self.currencyID = currencyID
        self.element_name = element_name

    def generate_doc(self):
        self.doc = createElementContent(self.element_name, self.amount)
        self.doc.setAttribute("currencyID", self.currencyID)


class BaseAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(BaseAmount, self).__init__(amount, currencyID, element_name="cbc:BaseAmount")


class PriceAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(PriceAmount, self).__init__(amount, currencyID, element_name="cbc:PriceAmount")


class TotalAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(TotalAmount, self).__init__(amount, currencyID, "sac:TotalAmount")


class PaidAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(PaidAmount, self).__init__(amount, currencyID, "cbc:PaidAmount")


class PrepaidAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(PrepaidAmount, self).__init__(amount, currencyID, element_name="cbc:PrepaidAmount")


class PayableAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(PayableAmount, self).__init__(amount, currencyID, element_name="cbc:PayableAmount")


class LineExtensionAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(LineExtensionAmount, self).__init__(amount, currencyID, element_name="cbc:LineExtensionAmount")


class TaxInclusiveAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(TaxInclusiveAmount, self).__init__(amount, currencyID, element_name="cbc:TaxInclusiveAmount")


class ChargeTotalAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(ChargeTotalAmount, self).__init__(amount, currencyID, element_name="cbc:ChargeTotalAmount")


class AllowanceTotalAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(AllowanceTotalAmount, self).__init__(amount, currencyID, element_name="cbc:AllowanceTotalAmount")


class PayableRoundingAmount(Amount):
    def __init__(self, amount, currencyID="PEN"):
        super(AllowanceTotalAmount, self).__init__(amount, currencyID, element_name="cbc:PayableRoundingAmount")
