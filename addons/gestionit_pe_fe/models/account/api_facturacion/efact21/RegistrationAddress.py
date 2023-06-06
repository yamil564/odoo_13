from .util import Xmleable, default_document


class RegistrationAddress(Xmleable):
    def __init__(self, address_type_code="0000", address=None, urbanization=None,
                 province_name=None, ubigeo=None, departament=None,
                 district=None, country_code="PE"):
        self.address_type_code = address_type_code
        self.address = address
        self.urbanization = urbanization
        self.province_name = province_name
        self.ubigeo = ubigeo
        self.departament = departament
        self.district = district
        self.country_code = country_code

    def generate_address(self):
        ans = default_document.createElement("cac:AddressLine")
        line = default_document.createElement("cbc:Line")
        text = default_document.createCDATASection(self.address)
        line.appendChild(text)
        ans.appendChild(line)
        return ans

    def generate_urbanization(self):
        ans = default_document.createElement("cbc:CitySubdivisionName")
        text = default_document.createTextNode(self.urbanization)
        ans.appendChild(text)
        return ans

    def generate_province(self):
        ans = default_document.createElement("cbc:CityName")
        text = default_document.createTextNode(self.province_name)
        ans.appendChild(text)
        return ans

    def generate_ubigeo(self):
        ans = default_document.createElement("cbc:ID")
        ans.setAttribute("schemeAgencyName", "PE:INEI")
        ans.setAttribute("schemeName", "Ubigeos")
        text = default_document.createTextNode(self.ubigeo)
        ans.appendChild(text)
        return ans

    def generate_departament(self):
        ans = default_document.createElement("cbc:CountrySubentity")
        text = default_document.createTextNode(self.departament)
        ans.appendChild(text)
        return ans

    def generate_district(self):
        ans = default_document.createElement("cbc:District")
        text = default_document.createTextNode(self.district)
        ans.appendChild(text)
        return ans

    def generate_country(self):
        ans = default_document.createElement("cac:Country")
        elem = default_document.createElement("cbc:IdentificationCode")
        elem.setAttribute("listID", "ISO 3166-1")
        elem.setAttribute("listAgencyName", "United Nations Economic Commission for Europe")
        elem.setAttribute("listName", "Country")
        text = default_document.createTextNode(self.country_code)
        elem.appendChild(text)
        ans.appendChild(elem)
        return ans

    def generate_adress_type(self):
        ans = default_document.createElement("cbc:AddressTypeCode")
        # ans.setAttribute("schemeAgencyName", "PE:SUNAT")
        # ans.setAttribute("schemeName", "Establecimientos anexos")
        text = default_document.createTextNode(self.address_type_code)
        ans.appendChild(text)
        return ans

    def generate_doc(self):
        self.doc = default_document.createElement("cac:RegistrationAddress")
        if self.address:
            self.doc.appendChild(self.generate_address())
        if self.urbanization:
            self.doc.appendChild(self.generate_urbanization())
        if self.province_name:
            self.doc.appendChild(self.generate_province())
        if self.ubigeo:
            self.doc.appendChild(self.ubigeo)
        if self.departament:
            self.doc.appendChild(self.generate_departament())
        if self.district:
            self.doc.appendChild(self.generate_district())
        self.doc.appendChild(self.generate_adress_type())
