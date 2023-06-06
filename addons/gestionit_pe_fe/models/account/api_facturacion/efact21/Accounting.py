from .util import Xmleable, createElementContent


class CustomerAssignedAccountID(Xmleable):
    def __init__(self, acc_id, scheme_id=None):
        self.id = acc_id
        self.schemeID = scheme_id

    def generate_doc(self):
        self.doc = createElementContent(
            "cbc:CustomerAssignedAccountID", self.id)
        if self.schemeID:
            self.doc.setAttribute("schemeID", self.schemeID)


class AdditionalAccountID(Xmleable):
    def __init__(self, acc_id):
        self.id = acc_id

    def generate_doc(self):
        self.doc = createElementContent("cbc:AdditionalAccountID", self.id)
