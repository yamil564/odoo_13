from .util import Xmleable, default_document, createElementContent, createCDataContent


class ReferenceID(Xmleable):
    def __init__(self, ref_id):
        self.ref_id = ref_id

    def generate_doc(self):
        self.doc = createElementContent("cbc:ReferenceID", self.ref_id)


class ResponseCode(Xmleable):
    def __init__(self, code):
        self.code = code

    def validate(self, errs, obs):
        # Catalogo 09
        assert type(self.code) == str and len(self.code) == 2
        code = int(self.code)
        assert 0 < code <= 10

    def generate_doc(self):
        self.doc = createElementContent("cbc:ResponseCode", self.code)


class Description(Xmleable):
    def __init__(self, desc):
        self.desc = desc

    def fix_values(self):
        self.desc = self.desc.replace("\n", "")

    def validate(self, errs, obs):
        assert len(self.desc) <= 250

    def generate_doc(self):
        self.doc = createCDataContent("cbc:Description", self.desc)


class DiscrepancyResponse(Xmleable):
    def __init__(self, ref_id, resp_code, description):
        self.ref_id = ref_id
        self.resp_code = resp_code
        self.description = description

    def fix_values(self):
        if type(self.ref_id) == str:
            self.ref_id = ReferenceID(self.ref_id)
        if type(self.resp_code) == str:
            self.resp_code = ResponseCode(self.resp_code)
        if type(self.description) == str:
            self.description = Description(self.description)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:DiscrepancyResponse")
        self.doc.appendChild(self.ref_id.get_document())
        self.doc.appendChild(self.resp_code.get_document())
        self.doc.appendChild(self.description.get_document())
