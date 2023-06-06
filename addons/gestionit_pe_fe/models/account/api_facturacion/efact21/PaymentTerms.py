# from types import NoneType
from .util import Xmleable, default_document, createElementContent
from .General import SimpleText
from .AmountTypes import Amount
from .General import DateType
import re
patron_cuota = re.compile("Cuota[0-9]{3}$")


class ID(SimpleText):
    def __init__(self, code_id):
        super(ID, self).__init__(code_id, "cbc:ID")

class PaymentMeansID(SimpleText):
    def __init__(self, payment_means):
        super(PaymentMeansID, self).__init__(payment_means, "cbc:PaymentMeansID")

class PaymentDueDate(DateType):
    def __init__(self,date=None,element_name="cbc:PaymentDueDate"):
        super(PaymentDueDate, self).__init__(date,element_name)

class PaymentPercent(SimpleText):
    def __init__(self,payment_percent):
        super(PaymentPercent, self).__init__(payment_percent,"cbc:PaymentPercent") 

class PaymentTerms(Xmleable):
    def __init__(self,id,payment_means_id=None,amount=None,payment_due_date=None,payment_percent=None,detraction=False):
        self.id = id
        self.payment_means_id = payment_means_id
        self.amount = amount
        self.payment_due_date = payment_due_date
        self.payment_percent = payment_percent
        self.detraction = detraction

    def validate(self,errs,obs):
        if type(self.id) != ID:
            raise Exception("Tipo incorrecto: PaymentTerms -> ID")
        if type(self.payment_means_id) != PaymentMeansID:
            raise Exception("Tipo incorrecto: PaymentTerms -> PaymentMeans")
        if type(self.amount) != Amount and self.amount != None:
            raise Exception("Tipo incorrecto: PaymentTerms -> Amount")            
        if type(self.payment_due_date) != PaymentDueDate and self.payment_due_date != None:
            raise Exception("Tipo incorrecto: PaymentTerms -> PaymentDueDate")

        if self.id.text == "FormaPago":
            if not(self.payment_means_id.text in ["Contado","Credito"] or bool(patron_cuota.match(self.payment_means_id.text))):
                raise Exception("La forma de pago solo puede contener los valores de Contado, Credito o Cuota[0-9]{3}")
        
            if bool(patron_cuota.match(self.payment_means_id.text)):
               if self.amount == None or self.payment_due_date == None:
                   raise Exception("La cuota {}, no tiene establecido el monto o la fecha de vencimiento".format(self.payment_means_id.text))
        if self.detraction:
            if type(self.payment_percent) !=  PaymentPercent:
                raise Exception("Tipo incorrecto: PaymentTerms -> PaymentPercent")


    def fix_values(self):
        if type(self.payment_means_id) == str:
            self.payment_means_id = PaymentMeansID(self.payment_means_id)
        if type(self.id) == str:
            self.id = ID(self.id)
        if type(self.payment_due_date) == str:
            self.payment_due_date = PaymentDueDate(self.payment_due_date)
        if type(self.payment_percent) in (int,float) and self.payment_percent > 0 and self.detraction == True:
            self.payment_percent = PaymentPercent(self.payment_percent)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PaymentTerms")
        self.doc.appendChild(self.id.get_document())
        self.doc.appendChild(self.payment_means_id.get_document())
        if self.detraction == True:
            self.doc.appendChild(self.payment_percent.get_document())
        if self.amount != None:
            self.doc.appendChild(self.amount.get_document())
        if self.payment_due_date != None:
            self.doc.appendChild(self.payment_due_date.get_document())
