from ..efact21 import General
from ..efact21 import SummaryDocumentsLine
from ..efact21 import TaxTotal
from ..efact21.Accounting import CustomerAssignedAccountID, AdditionalAccountID
from ..efact21.CustomerParty import AccountingCustomerParty
from ..efact21.SupplierParty import AccountingSupplierParty
from ..efact21.Documents import ResumenDiario
from ..efact21.Party import PartyLegalEntity, Party
from ..efact21 import AmountTypes
from ..efact21.BillingReference import InvoiceDocumentReference, BillingReference

required_fields = ["fechaGeneracion", "resumen", "detalle"]
resumen_required_fields = ["id", "numDocEmisor", "tipoFormatoRepresentacionImpresa",
                           "tipoDocEmisor", "fechaReferente", "nombreEmisor"]
detalle_required_fields = ["serie", "correlativo", "tipoDocumento", "tipoDocReceptor", "numDocReceptor", "tipoMoneda",
                           "mntIgv", "mntIsc", "codOperacion", "mntTotal", "mntNeto", "mntExe", "mntExo", "mntExp", "mntGrat", "mntOtros"]


def build_detalle(detalle):
    serie = detalle.get("serie")
    correlativo = detalle.get("correlativo")
    tipo_documento = detalle.get("tipoDocumento")
    numDocReceptor = detalle.get("numDocReceptor")
    tipoDocReceptor = detalle.get("tipoDocReceptor")
    mntTotal = detalle.get("mntTotal")
    mntNeto = detalle.get("mntNeto")
    mntExe = detalle.get("mntExe")
    mntExo = detalle.get("mntExo")
    mntIgv = detalle.get("mntIgv")
    moneda = detalle.get("tipoMoneda")
    codOperacion = detalle.get("codOperacion")
    tipoDocReferencia = detalle.get("tipoDocReferencia")
    numDocReferencia = detalle.get("numDocReferencia")

    doc_line = SummaryDocumentsLine.SummaryDocumentsLine()
    doc_line.id = serie + "-" + str(correlativo)
    doc_line.document_type_code = SummaryDocumentsLine.DocumentTypeCode(
        tipo_documento)

    if tipoDocReceptor in ["0", "1", "4", "6", "7", "A", "B", "C", "D", "E"] and numDocReceptor != "-":
        acp = AccountingCustomerParty()
        acp.customer_assigned_accountID = CustomerAssignedAccountID(
            numDocReceptor)
        acp.additional_accountID = AdditionalAccountID(tipoDocReceptor)
        doc_line.accounting_customer_party = acp

    doc_line.status = codOperacion
    doc_line.total_amount = AmountTypes.TotalAmount(mntTotal,currencyID=moneda)

    # Documento de Referencia (Notas asociadas a boletas)
    # print(type(numDocReferencia) == str and type(tipoDocReferencia) == str)
    if tipo_documento in ['07', '08']:
        if type(numDocReferencia) == str and type(tipoDocReferencia) == str:
            # print(numDocReferencia)
            # print(tipoDocReferencia)
            invoice_document_reference = InvoiceDocumentReference(
                numDocReferencia, tipoDocReferencia)
            doc_line.billing_reference = BillingReference(
                invoice_document_reference=invoice_document_reference)
    # Gravado
    doc_line.billing_payments = []
    if mntNeto:
        doc_line.billing_payments.append(
            SummaryDocumentsLine.BillingPayment(mntNeto, "01",currencyID=moneda))
    # Exonerado
    if mntExo:
        doc_line.billing_payments.append(
            SummaryDocumentsLine.BillingPayment(mntExo, "02",currencyID=moneda))
    # Inafecto
    if mntExe:
        doc_line.billing_payments.append(
            SummaryDocumentsLine.BillingPayment(mntExe, "03",currencyID=moneda))

    tax_total = TaxTotal.TaxTotal()
    tax_total.tax_amount = TaxTotal.TaxAmount(mntIgv,currencyID=moneda)

    # IGV
    tax_subtotal = TaxTotal.TaxSubtotal()
    tax_subtotal.tax_amount = TaxTotal.TaxAmount(mntIgv,currencyID=moneda)
    tax_scheme = TaxTotal.TaxScheme("1000", "IGV", "VAT")
    tax_subtotal.tax_category = TaxTotal.TaxCategory(tax_scheme=tax_scheme)
    tax_total.tax_subtotal = tax_subtotal

    doc_line.tax_total = tax_total
    tax_total.add_tax_subtotal(tax_subtotal)

    return doc_line


def build_resumen(data):
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

    res_dia = ResumenDiario(ubl_version="2.0", customization_id="1.1")
    res_dia.doc_id = "RC-" + \
        fecha_generacion.replace("-", "") + "-" + str(resumen_id)
    res_dia.issue_date = fecha_generacion
    res_dia.reference_date = fecha_referente

    # SupplierPaty
    party = Party()
    party.party_legal_entity = PartyLegalEntity(nombre_emisor)
    supplier_party = AccountingSupplierParty(party=party,
                                             customer_assigned_account=doc_emisor,
                                             additional_account=doc_emisor_type)
    supplier_party.customer_assigned_accountID = doc_emisor
    supplier_party.additional_accountID = doc_emisor_type
    res_dia.accounting_supplier_party = supplier_party

    # Detalle
    for line in data.get('detalle', []):
        res_dia.add_summary_document_line(build_detalle(line))

    return res_dia
