from .util import Xmleable, default_document, createElementContent, createCDataContent
from .General import SimpleText
from . import BasicGlobal


class HandlingCode(SimpleText):
    def __init__(self, code):
        super(HandlingCode, self).__init__(code, "cbc:HandlingCode")


class Information(SimpleText):
    def __init__(self, information):
        super(Information, self).__init__(information, "cbc:Information")


class SplitConsignmentIndicator(SimpleText):
    def __init__(self, sci):
        super(SplitConsignmentIndicator, self).__init__(sci, "cbc:SplitConsignmentIndicator")


class GrossWeightMeasure(Xmleable):
    def __init__(self, gross_weight, unit_code=None):
        self.gross_weight = gross_weight
        self.unitCode = unit_code

    def generate_doc(self):
        self.doc = createElementContent("cbc:GrossWeightMeasure", str(self.gross_weight))
        if self.unitCode:
            self.doc.setAttribute("unitCode", self.unitCode)


class TotalTransportHandlingUnitQuantity(SimpleText):
    def __init__(self, quantity):
        super(TotalTransportHandlingUnitQuantity, self).__init__(quantity, "cbc:TotalTransportHandlingUnitQuantity")


# Shipment Stage
class TransportModeCode(SimpleText):
    def __init__(self, mode_code):
        super(TransportModeCode, self).__init__(mode_code, "cbc:TransportModeCode")


class TransitPeriod(Xmleable):
    def __init__(self, start_date):
        self.start_date = start_date

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TransitPeriod")
        self.doc.appendChild(createElementContent("cbc:StartDate", self.start_date))


class CarrierParty(Xmleable):
    def __init__(self, identification, name, scheme_id="1"):
        self.identification = identification
        self.name = name
        self.schemeID = scheme_id

    def generate_identification(self):
        elem = default_document.createElement("cac:PartyIdentification")
        elem_id = createElementContent("cbc:ID", self.identification)
        if self.schemeID:
            elem_id.setAttribute("schemeID", self.schemeID)
        elem.appendChild(elem_id)
        return elem

    def generate_name(self):
        elem = default_document.createElement("cac:PartyName")
        elem_name = default_document.createElement("cbc:Name")
        elem_name.appendChild(default_document.createCDATASection(self.name))
        elem.appendChild(elem_name)
        return elem

    def generate_doc(self):
        self.doc = default_document.createElement("cac:CarrierParty")
        self.doc.appendChild(self.generate_identification())
        self.doc.appendChild(self.generate_name())


class TransportMeans(Xmleable):
    def __init__(self, license_plate_id):
        self.license_plate_id = license_plate_id

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TransportMeans")
        road_transport = default_document.createElement("cac:RoadTransport")
        road_transport.appendChild(createElementContent("cbc:LicensePlateID", self.license_plate_id))
        self.doc.appendChild(road_transport)


class DriverPerson(Xmleable):
    def __init__(self, person_id, scheme_id="1"):
        self.person_id = person_id
        self.schemeID = scheme_id

    def generate_doc(self):
        self.doc = default_document.createElement("cac:DriverPerson")
        elem_id = createElementContent("cbc:ID", self.person_id)
        if self.schemeID:
            elem_id.setAttribute("schemeID", self.schemeID)
        self.doc.appendChild(elem_id)


class ShipmentStage(Xmleable):
    def __init__(self, transport_mode_code=None, transit_period=None, carrier_party=None,
                 transport_means=None, driver_person=None):
        self.id = 0
        self.transport_mode_code = transport_mode_code
        self.transit_period = transit_period
        self.carrier_party = carrier_party
        self.transport_means = transport_means
        self.driver_person = driver_person

    def fix_values(self):
        if type(self.transport_mode_code) == str:
            self.transport_mode_code = TransportModeCode(self.transport_mode_code)
        if type(self.transit_period) == str:
            self.transit_period = TransitPeriod(self.transit_period)
        if type(self.transport_means) == str:
            self.transport_means = TransportMeans(self.transport_means)
        if type(self.driver_person) == str:
            self.driver_person = DriverPerson(self.driver_person)

    def validate(self, erros, observs):
        assert type(self.transport_mode_code) == TransportModeCode
        assert type(self.transit_period) == TransitPeriod
        assert type(self.carrier_party) in [CarrierParty,str] or self.carrier_party == None
        assert type(self.transport_means)  in [TransportMeans,str] or self.transport_means == None
        assert type(self.driver_person) in [DriverPerson,str] or self.driver_person == None

    def generate_doc(self):
        self.doc = default_document.createElement("cac:ShipmentStage")
        self.doc.appendChild(createElementContent("cbc:ID", self.id))
        self.doc.appendChild(self.transport_mode_code.get_document())
        self.doc.appendChild(self.transit_period.get_document())
        if self.carrier_party:
            self.doc.appendChild(self.carrier_party.get_document())
        if self.transport_means:
            self.doc.appendChild(self.transport_means.get_document())
        if self.driver_person:
            self.doc.appendChild(self.driver_person.get_document())
# End Shipment Stage

class DeliveryAddress(Xmleable):
    def __init__(self, address_id, street_name):
        self.address_id = address_id
        self.street_name = street_name

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Delivery")
        da = default_document.createElement("cac:DeliveryAddress")
        da.appendChild(createElementContent("cbc:ID", self.address_id))
        da.appendChild(createElementContent("cbc:StreetName", self.street_name))
        self.doc.appendChild(da)


class TransportHandlingUnit(Xmleable):
    def __init__(self, t_id=None, transport_equipment=None):
        self.id = t_id
        self.transport_equipment = transport_equipment

    def generate_doc(self):
        self.doc = default_document.createElement("cac:TransportHandlingUnit")
        if self.id:
            self.doc.appendChild(createElementContent("cbc:ID", self.id))
        if self.transport_equipment:
            equipment = default_document.createElement("cac:TransportEquipment")
            equipment.appendChild(createElementContent("cbc:ID", self.transport_equipment))
            self.doc.appendChild(equipment)


class OriginAddress(Xmleable):
    def __init__(self, address_id, street_name):
        self.address_id = address_id
        self.street_name = street_name

    def generate_doc(self):
        self.doc = default_document.createElement("cac:OriginAddress")
        self.doc.appendChild(createElementContent("cbc:ID", self.address_id))
        self.doc.appendChild(createElementContent("cbc:StreetName", self.street_name))


class LoadingPortLocation(Xmleable):
    def __init__(self, address_id, street_name):
        self.address_id = address_id
        self.street_name = street_name

    def generate_doc(self):
        self.doc = default_document.createElement("cac:LoadingPortLocation")
        self.doc.appendChild(createElementContent("cbc:ID", self.address_id))
        self.doc.appendChild(createCDataContent("cbc:Description", self.street_name))


class FirstArrivalPortLocation(Xmleable):
    def __init__(self, port):
        self.port = port

    def generate_doc(self):
        self.doc = default_document.createElement("cac:FirstArrivalPortLocation")
        self.doc.appendChild(createElementContent("cbc:ID", self.port))


class Shipment(Xmleable):
    def __init__(self, ship_id=None, handling_code=None, information=None, split_consignment_indicator=None,
                 gross_weight_measure=None, transport_handling_quantity=None, shipment_stage=None,
                 delivery_address=None, transport_handling_unit=None, origin_address=None,
                 loading_port_location=None, first_arrival_port_location=None):
        self.shipment_stages = []
        self.id = ship_id
        self.handling_code = handling_code
        self.information = information
        self.split_consignment_indicator = split_consignment_indicator
        self.gross_weight_measure = gross_weight_measure
        self.transport_handling_quantity = transport_handling_quantity
        # self.shipment_stage = shipment_stage
        self.delivery_address = delivery_address
        self.transport_handling_unit = transport_handling_unit
        self.origin_address = origin_address
        self.loading_port_location = loading_port_location
        self.first_arrival_port_location = first_arrival_port_location

    def fix_values(self):
        if type(self.id) == int:
            self.id = BasicGlobal.ID(self.id)
        if type(self.handling_code) in [int, str]:
            self.handling_code = HandlingCode(self.handling_code)
        if type(self.information) == str:
            self.information = Information(self.information)
        if type(self.split_consignment_indicator) == str:
            self.split_consignment_indicator = SplitConsignmentIndicator(self.split_consignment_indicator)
        if type(self.gross_weight_measure) == str:
            self.gross_weight_measure = GrossWeightMeasure(self.gross_weight_measure)
        if type(self.transport_handling_quantity) in [int, str]:
            self.transport_handling_quantity = TotalTransportHandlingUnitQuantity(self.transport_handling_quantity)
        if type(self.first_arrival_port_location) == str:
            self.first_arrival_port_location = FirstArrivalPortLocation(self.first_arrival_port_location)

    def validate(self, erros, observs):
        assert self.id is None or type(self.id) == BasicGlobal.ID
        assert type(self.handling_code) == HandlingCode
        assert self.information is None or type(self.information) == Information
        assert self.split_consignment_indicator is None or \
            type(self.split_consignment_indicator) == SplitConsignmentIndicator
        assert type(self.gross_weight_measure) == GrossWeightMeasure
        assert self.transport_handling_quantity is None or \
            type(self.transport_handling_quantity) == TotalTransportHandlingUnitQuantity
        assert type(self.delivery_address) == DeliveryAddress
        assert self.transport_handling_unit is None or \
            type(self.transport_handling_unit) == TransportHandlingUnit
        assert type(self.origin_address) == OriginAddress
        assert self.loading_port_location is None or type(self.loading_port_location) == LoadingPortLocation
        assert self.first_arrival_port_location is None or \
            type(self.first_arrival_port_location) == FirstArrivalPortLocation

    def add_shipment_stage(self, shipment_stage):
        assert type(shipment_stage) == ShipmentStage
        self.shipment_stages.append(shipment_stage)

    def generate_doc(self):
        self.doc = default_document.createElement("cac:Shipment")
        if self.id:
            self.doc.appendChild(self.id.get_document())
        self.doc.appendChild(self.handling_code.get_document())
        if self.information:
            self.doc.appendChild(self.information.get_document())
        self.doc.appendChild(self.gross_weight_measure.get_document())
        if self.transport_handling_quantity:
            self.doc.appendChild(self.transport_handling_quantity.get_document())
        if self.split_consignment_indicator is not None:
            self.doc.appendChild(self.split_consignment_indicator.get_document())
        for shipment_stage in self.shipment_stages:
            self.doc.appendChild(shipment_stage.get_document())
        self.doc.appendChild(self.delivery_address.get_document())
        if self.transport_handling_unit:
            self.doc.appendChild(self.transport_handling_unit.get_document())
        self.doc.appendChild(self.origin_address.get_document())
        if self.loading_port_location:
            self.doc.appendChild(self.loading_port_location.get_document())
        if self.first_arrival_port_location:
            self.doc.appendChild(self.first_arrival_port_location.get_document())
