from .util import Xmleable, default_document


class ID(Xmleable):
    def __init__(self, id):
        self.id = id

    def generate_doc(self):
        self.doc = default_document.createElement("cbc:ID")
        text = default_document.createTextNode(str(self.id))
        self.doc.appendChild(text)


class SignatoryParty(Xmleable):
    def __init__(self, identification, name):
        self.identification = identification
        self.name = name

    def generate_identification(self):
        elem = default_document.createElement("cac:PartyIdentification")
        elem_id = default_document.createElement("cbc:ID")
        text = default_document.createTextNode(str(self.identification))
        elem_id.appendChild(text)
        elem.appendChild(elem_id)
        return elem

    def generate_name(self):
        elem = default_document.createElement("cac:PartyName")
        elem_name = default_document.createElement("cbc:Name")
        text = default_document.createCDATASection(self.name)
        elem_name.appendChild(text)
        elem.appendChild(elem_name)
        return elem

    def generate_doc(self):
        self.doc = default_document.createElement("cac:SignatoryParty")
        self.doc.appendChild(self.generate_identification())
        self.doc.appendChild(self.generate_name())


class DigitalSignatureAttachment(Xmleable):
    def __init__(self, element_id="SignatureMT"):
        self.element_id = element_id

    def generate_doc(self):
        self.doc = default_document.createElement(
            "cac:DigitalSignatureAttachment")
        elem_ref = default_document.createElement("cac:ExternalReference")
        elem_uri = default_document.createElement("cbc:URI")
        text = default_document.createTextNode("#" + self.element_id)
        elem_uri.appendChild(text)
        elem_ref.appendChild(elem_uri)
        self.doc.appendChild(elem_ref)


class Signature(Xmleable):
    def __init__(self, id, identification, name, element_id="SignatureMT"):
        self.id = ID(id)
        self.signatory_party = SignatoryParty(identification, name)
        self.digital_signature_attachment = DigitalSignatureAttachment(
            element_id)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Signature")
        self.doc.appendChild(self.id.get_document())
        self.doc.appendChild(self.signatory_party.get_document())
        self.doc.appendChild(self.digital_signature_attachment.get_document())
