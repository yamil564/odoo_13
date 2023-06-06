from . import General
from . import TaxTotal
from .CustomerParty import AccountingCustomerParty
from .BasicGlobal import DocumentTypeCode
from .General import SimpleText
from .util import Xmleable, default_document, createElementContent
from . import AmountTypes
from .BillingReference import InvoiceDocumentReference, BillingReference


class LineID(SimpleText):
    def __init__(self, id):
        super(LineID, self).__init__(id, "cbc:LineID")


class ID(SimpleText):
    def __init__(self, id):
        super(ID, self).__init__(id, "cbc:ID")


class Status(Xmleable):
    def __init__(self, condition_code):
        self.condition_code = condition_code

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Status")
        self.doc.appendChild(createElementContent(
            "cbc:ConditionCode", self.condition_code))


class InstructionID(SimpleText):
    def __init__(self, id):
        super(InstructionID, self).__init__(id, "cbc:InstructionID")


class BillingPayment(Xmleable):
    def __init__(self, paid_amount, instruction_id,currencyID):
        self.paid_amount = paid_amount
        self.instruction_id = instruction_id
        self.currencyID = currencyID

    def fix_values(self):
        if type(self.paid_amount) in [float, int]:
            self.paid_amount = AmountTypes.PaidAmount(self.paid_amount,self.currencyID)
        if type(self.instruction_id) == str:
            self.instruction_id = InstructionID(self.instruction_id)

    def generate_doc(self):
        self.doc = default_document.createElement("sac:BillingPayment")
        self.doc.appendChild(self.paid_amount.get_document())
        self.doc.appendChild(self.instruction_id.get_document())


class SummaryDocumentsLine(Xmleable):
    def __init__(self, line_id=None, id=None, document_type_code=None,
                 accounting_customer_party=None, status=None, total_amount=None,
                 billing_payments=[], tax_total=None, billing_reference=None):
        self.line_id = line_id
        self.id = id
        self.document_type_code = document_type_code
        self.accounting_customer_party = accounting_customer_party
        self.status = status
        self.total_amount = total_amount
        self.billing_payments = billing_payments
        self.tax_total = tax_total
        self.billing_reference = billing_reference

    def fix_values(self):
        if type(self.line_id) == int:
            self.line_id = LineID(self.line_id)
        if type(self.id) == str:
            self.id = ID(self.id)
        if type(self.document_type_code) == str:
            self.document_type_code = DocumentTypeCode(self.document_type_code)
        if type(self.status) == str:
            self.status = Status(self.status)
        if type(self.total_amount) in [float, int]:
            self.total_amount = AmountTypes.TotalAmount(self.total_amount)

    def validate(self, errs, obs):
        assert type(self.line_id) == LineID
        assert type(self.id) == ID
        assert type(self.document_type_code) == DocumentTypeCode
        assert type(self.accounting_customer_party) in [
            None, AccountingCustomerParty]
        assert type(self.status) == Status
        assert type(self.total_amount) == AmountTypes.TotalAmount
        #assert type(self.billing_payment) == BillingPayment
        assert type(self.tax_total) == TaxTotal.TaxTotal
        #assert type(self.billing_reference) in [None, BillingReference]

    def generate_doc(self):
        self.doc = default_document.createElement("sac:SummaryDocumentsLine")
        self.doc.appendChild(self.line_id.get_document())
        self.doc.appendChild(self.document_type_code.get_document())
        self.doc.appendChild(self.id.get_document())
        if self.accounting_customer_party:
            self.doc.appendChild(self.accounting_customer_party.get_document())
        print(self.billing_reference)
        if self.billing_reference:
            self.doc.appendChild(self.billing_reference.get_document())
        self.doc.appendChild(self.status.get_document())
        self.doc.appendChild(self.total_amount.get_document())
        for billing_payment in self.billing_payments:
            self.doc.appendChild(billing_payment.get_document())
        self.doc.appendChild(self.tax_total.get_document())
