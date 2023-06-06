from .util import Xmleable, default_document, createElementContent


class Header(Xmleable):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def generate_doc(self):
        self.doc = default_document.createElement("soapenv:Header")
        security = default_document.createElement("wsse:Security")
        username_token = default_document.createElement("wsse:UsernameToken")
        username_token.appendChild(createElementContent("wsse:Username", self.username))
        username_token.appendChild(createElementContent("wsse:Password", self.password))
        security.appendChild(username_token)
        self.doc.appendChild(security)


class BodyResumen(Xmleable):
    def __init__(self, file_name, content):
        self.file_name = file_name
        self.content = content

    def generate_doc(self):
        self.doc = default_document.createElement("soapenv:Body")
        send_bill = default_document.createElement("ser:sendSummary")
        send_bill.appendChild(createElementContent("fileName", self.file_name))
        send_bill.appendChild(createElementContent("contentFile", self.content))
        self.doc.appendChild(send_bill)


class Body(Xmleable):
    def __init__(self, file_name, content):
        self.file_name = file_name
        self.content = content

    def generate_doc(self):
        self.doc = default_document.createElement("soapenv:Body")
        send_bill = default_document.createElement("ser:sendBill")
        send_bill.appendChild(createElementContent("fileName", self.file_name))
        send_bill.appendChild(createElementContent("contentFile", self.content))
        self.doc.appendChild(send_bill)


class Envelope(Xmleable):
    def __init__(self, header=None, body=None):
        self.header = header
        self.body = body

    def validate(self, errs, obs):
        assert type(self.header) == Header
        assert type(self.body) == Body

    def generate_doc(self):
        self.doc = default_document.createElement("soapenv:Envelope")
        self.doc.setAttribute("xmlns:ser", "http://service.sunat.gob.pe")
        self.doc.setAttribute("xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
        self.doc.setAttribute("xmlns:wsse",
                              "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd")

        self.doc.appendChild(self.header.get_document())
        self.doc.appendChild(self.body.get_document())
