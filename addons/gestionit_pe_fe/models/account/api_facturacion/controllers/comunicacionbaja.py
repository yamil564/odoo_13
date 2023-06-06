from ..efact21 import General
from ..efact21 import TaxTotal
from ..efact21.SupplierParty import AccountingSupplierParty
from ..efact21.Party import PartyLegalEntity, Party
from ..efact21.Documents import ComunicacionBaja
from ..efact21.VoidedDocumentsLine import VoidedDocumentsLine
import logging
_logger = logging.getLogger(__name__)


def build_detalle(detalle):
    serie = detalle.get("serie")
    correlativo = detalle.get("correlativo")
    tipo_documento = detalle.get("tipoDocumento")
    motivo = detalle.get("motivo")

    doc_line = VoidedDocumentsLine(document_type_code=tipo_documento, document_serial_id=serie,
                                   document_number_id=correlativo, void_reason_description=motivo)
    return doc_line


def build_comunicacion_baja(data):
    # print(data)
    # Falta validacion
    fecha_generacion = data.get("fechaGeneracion")

    # Resumen
    resumen = data.get("resumen", {})
    resumen_id = resumen.get("id")
    doc_emisor = resumen.get("numDocEmisor")
    doc_emisor_type = resumen.get('tipoDocEmisor')
    nombre_emisor = resumen.get("nombreEmisor")
    fecha_referente = resumen.get("fechaReferente")

    res_com_baja = ComunicacionBaja(ubl_version="2.0", customization_id="1.0")
    res_com_baja.doc_id = "RA-" + \
        str(fecha_generacion).replace("-", "") + "-" + str(resumen_id)
    res_com_baja.issue_date = str(fecha_generacion)
    res_com_baja.reference_date = str(fecha_referente)

    # SupplierPaty
    party = Party()
    party.party_legal_entity = PartyLegalEntity(nombre_emisor)
    supplier_party = AccountingSupplierParty(party=party,
                                             customer_assigned_account=doc_emisor,
                                             additional_account=doc_emisor_type)
    supplier_party.customer_assigned_accountID = doc_emisor
    supplier_party.additional_accountID = doc_emisor_type
    res_com_baja.accounting_supplier_party = supplier_party

    # Detalle
    for line in data.get('detalle', []):
        res_com_baja.add_voided_document_line(build_detalle(line))

    return res_com_baja
