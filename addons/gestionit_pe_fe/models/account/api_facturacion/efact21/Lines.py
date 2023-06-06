from .util import Xmleable, default_document, createCDataContent, createElementContent
from .AmountTypes import PriceAmount
from .BasicGlobal import ID


class PriceTypeCode(Xmleable):
    def __init__(self, code, add_attributes=False):
        self.code = code
        self.listName = "SUNAT:Indicador de Tipo de Precio"
        self.listAgencyName = "PE:SUNAT"
        self.listURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16"
        self.add_attributes = add_attributes

    def generate_doc(self):
        self.doc = createElementContent("cbc:PriceTypeCode", self.code)
        if self.add_attributes:
            self.doc.setAttribute("listName", self.listName)
            self.doc.setAttribute("listAgencyName", self.listAgencyName)
            self.doc.setAttribute("listURI", self.listURI)


class PricingReference(Xmleable):
    def __init__(self, price_amount, price_code):
        self.price_amount = price_amount
        self.price_code = price_code

    def validate(self, errs, obs):
        if type(self.price_amount) in [float, int]:
            self.price_amount = PriceAmount(self.price_amount)
        if type(self.price_amount) != PriceAmount:
            raise Exception("Bad type")
        if type(self.price_code) == str:
            self.price_code = PriceTypeCode(self.price_code)
        if type(self.price_code) != PriceTypeCode:
            raise Exception("Bad type")

    def generate_doc(self):
        self.doc = default_document.createElement("cac:PricingReference")
        acp = default_document.createElement("cac:AlternativeConditionPrice")
        acp.appendChild(self.price_amount.get_document())
        acp.appendChild(self.price_code.get_document())
        self.doc.appendChild(acp)


class Price(Xmleable):
    def __init__(self, price_amount, currency_id="PEN"):
        self.price = price_amount
        self.currencyID = currency_id

    def fix_values(self):
        if type(self.price) in [float, int]:
            self.price = PriceAmount(self.price, self.currencyID)

    def validate(self, errs, obs):
        assert type(self.price) == PriceAmount

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Price")
        self.doc.appendChild(self.price.get_document())


# Item
class Description(Xmleable):
    def __init__(self, description):
        self.description = description

    def generate_doc(self):
        self.doc = createCDataContent("cbc:Description", self.description)


class SellersItemIdentification(Xmleable):
    def __init__(self, sell_id):
        self.sell_id = sell_id

    def fix_values(self):
        if type(self.sell_id) == str:
            self.sell_id = ID(self.sell_id)

    def generate_doc(self):
        self.doc = default_document.createElement(
            "cac:SellersItemIdentification")
        self.doc.appendChild(self.sell_id.get_document())


class ItemClassificationCode(Xmleable):
    def __init__(self, c_code, add_attributes=False):
        self.c_code = c_code
        self.listID = "UNSPSC"
        self.listAgencyName = "GS1 US"
        self.listName = "Item Classification"
        self.add_attributes = add_attributes

    def generate_doc(self):
        self.doc = createElementContent(
            "cbc:ItemClassificationCode", self.c_code)
        if self.add_attributes:
            self.doc.setAttribute("listID", self.listID)
            self.doc.setAttribute("listAgencyName", self.listAgencyName)
            self.doc.setAttribute("listName", self.listName)


class CommodityClassification(Xmleable):
    def __init__(self, item_classification_code):
        self.item_classification_code = item_classification_code

    def fix_values(self):
        if type(self.item_classification_code) == str:
            self.item_classification_code = ItemClassificationCode(
                self.item_classification_code)

    def generate_doc(self):
        self.doc = default_document.createElement(
            "cac:CommodityClassification")
        self.doc.appendChild(self.item_classification_code.get_document())


class Item(Xmleable):
    def __init__(self, description=None, seller_item_identification=None,
                 commodity_classification=None, name=None):
        self.name = name
        self.description = description
        self.seller_item_identification = seller_item_identification
        self.commodity_classification = commodity_classification

    def fix_values(self):
        if type(self.description) == str:
            self.description = Description(self.description)
        if type(self.seller_item_identification) == str:
            self.seller_item_identification = SellersItemIdentification(
                self.seller_item_identification)
        if type(self.commodity_classification) == str:
            self.commodity_classification = CommodityClassification(
                self.commodity_classification)

    def validate(self, errs, obs):
        assert self.description is None or type(
            self.description) == Description
        assert self.seller_item_identification is None or\
            type(self.seller_item_identification) == SellersItemIdentification
        assert self.commodity_classification is None or type(
            self.commodity_classification) == CommodityClassification

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Item")
        if self.name:
            self.doc.appendChild(createCDataContent("cbc:Name", self.name))
        if self.description:
            self.doc.appendChild(self.description.get_document())
        if self.seller_item_identification:
            self.doc.appendChild(
                self.seller_item_identification.get_document())
        if self.commodity_classification:
            self.doc.appendChild(self.commodity_classification.get_document())
