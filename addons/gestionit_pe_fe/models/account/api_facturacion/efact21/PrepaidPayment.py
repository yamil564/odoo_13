from .AmountTypes import PaidAmount
from .util import Xmleable, default_document, createElementContent


class ID(Xmleable):
    def __init__(self, id, tipo_documento="02"):
        self.id = id
        self.schemeID = tipo_documento
        self.schemeName = "Anticipo"
        self.schemeAgencyName = "PE:SUNAT"

    def generate_doc(self):
        self.doc = createElementContent("cbc:ID", self.id)
        self.doc.setAttribute("schemeID", self.schemeID)
        self.doc.setAttribute("schemeName", self.schemeName)
        self.doc.setAttribute("schemeAgencyName", self.schemeAgencyName)


class PaidDate(Xmleable):
    def __init__(self, date):
        self.date = date

    def generate_doc(self):
        self.doc = createElementContent("cbc:PaidDate", self.date)


class PaidTime(Xmleable):
    def __init__(self, time):
        self.time = time

    def generate_doc(self):
        self.doc = createElementContent("cbc:PaidTime", self.time)


class PrepaidPayment(Xmleable):
    def __init__(self, id=None, paid_amount=None, paid_date=None, paid_time=None):
        self.id = id
        self.paid_amount = paid_amount
        self.paid_date = paid_date
        self.paid_time = paid_time

    def fix_values(self):
        if type(self.id) == str:
            self.id = ID(self.id)
        if type(self.paid_date) == str:
            self.paid_date = PaidDate(self.paid_date)
        if type(self.paid_time) == str:
            self.paid_time = PaidTime(self.paid_time)
        if type(self.paid_amount) in [float]:
            self.paid_amount = PaidAmount(self.paid_amount)

    def validate(self, errs, obs):
        if type(self.id) != ID:
            raise Exception("Bad type")
        if type(self.paid_amount) != PaidAmount:
            raise Exception("Bad type")
        if type(self.paid_date) != PaidDate:
            raise Exception("Bad type")
        if self.paid_time:
            if type(self.paid_time) != PaidTime:
                raise Exception("Bad type")

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PrepaidPayment")
        self.doc.appendChild(self.id.get_document())
        self.doc.appendChild(self.paid_amount.get_document())
        self.doc.appendChild(self.paid_date.get_document())
        if self.paid_time:
            self.doc.appendChild(self.paid_time.get_document())
