
from ..efact21.Documents import DespatchAdvice
import yaml
from ..efact21.OrderReference import OrderReference, OrderTypeCode
from ..efact21.DocumentReference import AdditionalDocumentReference
from ..efact21.SupplierParty import DespatchSupplierParty
from ..efact21.Party import Party, PartyLegalEntity
from ..efact21.Accounting import CustomerAssignedAccountID
from ..efact21.CustomerParty import DeliveryCustomerParty
from ..efact21.DespatchLine import DespatchLine, OrderLineReference, DeliveredQuantity, Item
from ..efact21 import Shipment


# def validate_json(data):
#     with open("./files/schemas_json/guia_remision.yaml") as f:
#         spec = yaml.safe_load(f.read())

#     flex.core.validate(spec, data)


def build_guia_line(detalle, ord):
    line = DespatchLine(ord)
    line.order_line_reference = OrderLineReference(ord)

    cantidadItem = detalle['cantidadItem']
    unidadMedidaItem = detalle['unidadMedidaItem']
    line.delivered_quantity = DeliveredQuantity(cantidadItem, unidadMedidaItem)

    codItem = detalle.get("codItem", "-")
    nombreItem = detalle['nombreItem']
    line.item = Item(name=nombreItem, seller_item_identification=codItem)

    return line


def build_guia_shipment(documento):
    shipment = Shipment.Shipment(ship_id=1)
    shipment.handling_code = documento['motivoTraslado']
    shipment.information = documento.get('descripcionMotivoTraslado', None)

    transbordoProgramado = documento.get('transbordoProgramado', None)
    if transbordoProgramado is not None:
        shipment.split_consignment_indicator = "true" if transbordoProgramado else "false"

    gross_weight = documento['pesoTotal']
    uni_weight = documento['pesoUnidadMedida']
    shipment.gross_weight_measure = Shipment.GrossWeightMeasure(
        gross_weight, uni_weight)

    bulltos = documento.get("numeroBulltosPallets", False)
    if bulltos:
        shipment.transport_handling_quantity = bulltos

    shipment.delivery_address = Shipment.DeliveryAddress(documento['entregaUbigeo'],
                                                         documento['entregaDireccion'])

    # numeroContenedor = documento.get("numeroContenedor", None)
    # shipment.transport_handling_unit = Shipment.TransportHandlingUnit(documento['placaVehiculo'],
    #                                                                       numeroContenedor)

    shipment.origin_address = Shipment.OriginAddress(documento['salidaUbigeo'],
                                                     documento['salidaDireccion'])
    shipment.first_arrival_port_location = documento.get('codigoPuerto', None)

    return shipment


def build_transport_tramos(tramos, shipment):
    for i, tramo in enumerate(tramos):
        shipment_stage = Shipment.ShipmentStage()
        shipment_stage.id = i+1
        shipment_stage.transport_mode_code = tramo['modoTraslado']
        shipment_stage.transit_period = tramo['fechaInicioTraslado']

        if tramo['modoTraslado'] == "01":
            shipment_stage.carrier_party = Shipment.CarrierParty(tramo['numDocTransportista'],
                                                                 tramo['nombreTransportista'],
                                                                 tramo['tipoDocTransportista'])
        if 'placaVehiculo' in tramo:
            shipment_stage.transport_means = tramo['placaVehiculo']
        if 'numDocConductor' in tramo and 'tipoDocConductor' in tramo:
            shipment_stage.driver_person = Shipment.DriverPerson(tramo['numDocConductor'],
                                                                 tramo['tipoDocConductor'])
        shipment.add_shipment_stage(shipment_stage)


def build_guia(data):
    # try:
    #     validate_json(data)
    # except Exception as e:
    #     return {"errors": str(e)}

    guia = DespatchAdvice(customization="1.0")

    documento = data['documento']
    guia.doc_id = documento['serie'] + '-' + str(documento['correlativo'])

    guia.issue_date = data['fechaEmision']
    guia.despatch_advice_type_code = data['tipoDocumento']

    if documento.get('docReferenciaNro', False):
        docReferenciaNro = documento['docReferenciaNro']
        docReferenciaTipo = documento['docReferenciaTipo']
        docReferenciaTipoNombre = documento.get(
            'docReferenciaTipoNombre', False)
        order_type_code = OrderTypeCode(docReferenciaTipo)
        if docReferenciaTipoNombre:
            order_type_code.name = docReferenciaTipoNombre
        guia.order_reference = OrderReference(
            docReferenciaNro, order_type_code)

    docRelacionadoNro = documento.get('docRelacionadoNro', False)
    docRelacionadoTipo = documento.get('docRelacionadoTipo', False)
    if docRelacionadoNro:
        guia.additional_document_reference = AdditionalDocumentReference(
            docRelacionadoNro, docRelacionadoTipo)

    supplier_id = CustomerAssignedAccountID(
        documento['numDocEmisor'], documento['tipoDocEmisor'])
    supplier_party = Party(
        party_legal_entity=PartyLegalEntity(documento['nombreEmisor']))
    guia.despatch_supplier_party = DespatchSupplierParty(
        supplier_id, supplier_party)

    tipoDocReceptor = documento['tipoDocReceptor']
    numDocReceptor = documento['numDocReceptor']
    nombreReceptor = documento['nombreReceptor']
    customer_id = CustomerAssignedAccountID(numDocReceptor, tipoDocReceptor)
    customer_party = Party(party_legal_entity=PartyLegalEntity(nombreReceptor))
    guia.delivery_customer_party = DeliveryCustomerParty(
        customer_party, customer_id)

    # Shipment
    guia.shipment = build_guia_shipment(documento)
    build_transport_tramos(data['transportes'], guia.shipment)

    # lines
    for i, detalle in enumerate(data['detalle']):
        guia.add_guia_line(build_guia_line(detalle, i))

    guia.set_file_name("{ruc}-{cod}-{serie}-{corr}".format(
        ruc=documento['numDocEmisor'],
        cod=data['tipoDocumento'],
        serie=documento['serie'],
        corr=documento['correlativo']
    ))

    return guia
