# from types import NoneType
from .util import Xmleable, default_document, createElementContent
from .General import SimpleText
from .AmountTypes import Amount
from .General import DateType
import re
import logging
_logger = logging.getLogger(__name__)

class ID(SimpleText):
    def __init__(self, code_id):
        super(ID, self).__init__(code_id, "cbc:ID")


class PaymentMeansCode(SimpleText):
    def __init__(self, payment_means_code,listName="Medio de pago",listAgencyName="PE:SUNAT",listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo59"):
        # attrs={"@listName":listName,
        #         "@listAgencyName":listAgencyName,
        #         "@listURI":listURI}
        super(PaymentMeansCode, self).__init__(payment_means_code, "cbc:PaymentMeansCode")
    

class PayeeFinancialAccount(Xmleable):
    def __init__(self,id):
        self.id = id
    
    def fix_values(self):
        if type(self.id) == str:
            self.id = ID(self.id)
            
    def generate_doc(self):
        self.doc = default_document.createElement("cac:PayeeFinancialAccount")
        self.doc.appendChild(self.id.get_document())
    

class PaymentMeans(Xmleable):
    def __init__(self,id = None,payment_means_code = None,payee_financial_account = None):
        self.id = id
        self.payment_means_code = payment_means_code
        self.payee_financial_account = payee_financial_account
    
    def validate(self,errs, obs):
        if type(self.id) != ID:
            raise Exception("Tipo Incorrecto: PaymentMeans -> ID")
        if type(self.payment_means_code) != PaymentMeansCode:
            raise Exception("Tipo Incorrecto: PaymentMeans -> PaymentMeansCode")
        if type(self.payee_financial_account) != PayeeFinancialAccount:
            raise Exception("Tipo Incorrecto: PaymentMeans -> PayeeFinancialAccount")

    def fix_values(self):
        if type(self.id) == str:
            self.id = ID(self.id)
        if type(self.payment_means_code) == str:
            self.payment_means_code = PaymentMeansCode(self.payment_means_code)
        if type(self.payee_financial_account) == str:
            self.payee_financial_account = PayeeFinancialAccount(self.payee_financial_account)


    def generate_doc(self):
        self.doc = default_document.createElement("cac:PaymentMeans")
        self.doc.appendChild(self.id.get_document())
        self.doc.appendChild(self.payment_means_code.get_document())
        self.doc.appendChild(self.payee_financial_account.get_document())