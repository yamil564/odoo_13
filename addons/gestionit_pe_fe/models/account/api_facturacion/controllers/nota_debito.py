
from . import validacion
# from api import lista_errores
from ..efact21.Documents import DebitNote
from ..efact21 import CustomerParty
from ..efact21 import SupplierParty
from ..efact21 import BasicGlobal
from ..efact21 import MonetaryTotal
from ..efact21 import General
from ..efact21.Party import PartyIdentification, PartyLegalEntity, PartyName
from ..efact21 import Party
from ..efact21.RegistrationAddress import RegistrationAddress
from ..efact21.TaxTotal import TaxTotal, TaxSubtotal, TaxCategory, TaxScheme, CategoryID, TaxableAmount, TaxAmount
from ..efact21 import DiscrepancyResponse
from ..efact21 import BillingReference
from ..efact21.AmountTypes import PriceAmount, PrepaidAmount, ChargeTotalAmount, LineExtensionAmount, \
    AllowanceTotalAmount, PayableAmount, TaxInclusiveAmount
from ..efact21 import DebitNoteLine
from ..efact21.Lines import PricingReference, Item, Price


def build_nota_debito(data):
    documento = data.get('documento', {})
    tipoDocumento = data.get('tipoDocumento', False)
    fechaEmision = validacion.transformar_fecha(data.get('fechaEmision', ''))

    detalle = data.get('detalle', False)
    descuento = data.get('descuento', False)
    indicadores = data.get('indicadores', False)
    referencia = data.get('referencia', False)

    serie = documento.get('serie', False)
    correlativo = documento.get('correlativo', False)
    nombreEmisor = documento.get('nombreEmisor', False)
    tipoDocEmisor = documento.get('tipoDocEmisor', False)
    numDocEmisor = documento.get('numDocEmisor', False)
    tipoDocReceptor = documento.get('tipoDocReceptor', False)
    numDocReceptor = documento.get('numDocReceptor', False)
    nombreReceptor = documento.get('nombreReceptor', False)
    tipoMoneda = documento.get('tipoMoneda', False)
    sustento = documento.get('sustento', '')  # SOLO NOTAS
    tipoMotivoNotaModificatoria = documento.get(
        'tipoMotivoNotaModificatoria', '')  # SOLO NOTAS
    mntTotal = documento.get('mntTotal', 0.0)
    mntTotalGrat = documento.get('mntTotalGrat', 0.0)
    mntTotalIgv = documento.get('mntTotalIgv', 0.0)
    mntTotalIsc = documento.get('mntTotalIsc', 0.0)
    # NO NECESARIOS
    direccionOrigen = documento.get('direccionOrigen', '')
    direccionUbigeo = documento.get('direccionUbigeo', '')
    nombreComercialEmisor = documento.get('nombreComercialEmisor', '')
    nombreComercialReceptor = documento.get('nombreComercialReceptor', '')
    tipoDocReceptorAsociado = documento.get('tipoDocReceptorAsociado', '')
    mntNeto = documento.get('mntNeto', 0.0)
    mntExe = documento.get('mntExe', 0.0)
    mntExo = documento.get('mntExo', 0.0)
    mntTotalIgv = documento.get('mntTotalIgv', 0.0)
    mntExportacion = documento.get('mntExportacion', 0.0)
    fechaVencimiento = documento.get('fechaVencimiento', 0.0)
    glosaDocumento = documento.get('glosaDocumento', '')
    codCentroCosto = documento.get('codCentroCosto', '')
    tipoCambioDestino = documento.get('tipoCambioDestino', '')

    mntTotalOtros = documento.get('mntTotalOtros', 0.0)
    mntTotalOtrosCargos = documento.get('mntTotalOtrosCargos', 0.0)
    mntTotalAnticipos = documento.get('mntTotalAnticipos', 0.0)
    tipoFormatoRepresentacionImpresa = documento.get(
        'tipoFormatoRepresentacionImpresa', '')

    mntDescuentoGlobal = descuento.get('mntDescuentoGlobal', 0.0)
    mntTotalDescuentos = descuento.get('mntTotalDescuentos', 0.0)

    # TIPO DE DOCUMENTO
    invoice_type_code = BasicGlobal.InvoiceTypeCode(
        tipoDocumento, listID="0101")

    # PROVEEDOR
    registration_name = BasicGlobal.RegistrationName(
        registration_name=nombreEmisor)
    party_identification = PartyIdentification(
        id_document=numDocEmisor, document_type=tipoDocEmisor)

    registration_address = RegistrationAddress(
        address_type_code="0000", address=None,
        urbanization=None, province_name=None,
        ubigeo=None,
        departament=None, district=None,
        country_code="PE")
    party_legal_entity = PartyLegalEntity(registration_name=registration_name,
                                          registration_address=registration_address)

    party_name = PartyName(nombreEmisor)

    party = Party.Party(party_name=party_name, party_legal_entity=party_legal_entity,
                        party_identification=party_identification)

    proveedor = SupplierParty.AccountingSupplierParty(party=party)

    # CLIENTE
    party_legal_entity = PartyLegalEntity(registration_name=nombreReceptor)
    party_identification = PartyIdentification(
        id_document=numDocReceptor, document_type=tipoDocReceptor)
    party = CustomerParty.Party(
        party_identification=party_identification, party_legal_entity=party_legal_entity)
    cliente = CustomerParty.AccountingCustomerParty(party=party)

    # MONTO DE PAGO
    prepaid_amount = PrepaidAmount(
        amount=mntTotalAnticipos, currencyID=tipoMoneda)
    charge_total_amount = ChargeTotalAmount(
        amount=mntTotalOtrosCargos, currencyID=tipoMoneda)
    line_extension_amount = LineExtensionAmount(
        amount=mntNeto + mntExe + mntExo, currencyID=tipoMoneda)
    allowance_total_amount = AllowanceTotalAmount(
        amount=mntTotalDescuentos, currencyID=tipoMoneda)
    payable_amount = PayableAmount(amount=mntTotal, currencyID=tipoMoneda)
    tax_inclusive_amount = TaxInclusiveAmount(
        amount=mntTotal, currencyID=tipoMoneda)

    requested_monetary_total = MonetaryTotal.RequestedMonetaryTotal(
        line_extension_amount=line_extension_amount,
        prepaid_amount=prepaid_amount,
        payable_amount=payable_amount,
        allowance_total_amount=allowance_total_amount,
        charge_total_amount=charge_total_amount,
        tax_inclusive_amount=tax_inclusive_amount)

    # FECHA DE EMISIÓN
    issue_date = General.IssueDate(date=fechaEmision)

    # IMPUESTOS
    tax_amount = TaxAmount(amount=mntTotalIgv +
                           mntTotalIsc, currencyID=tipoMoneda)
    tax_total = TaxTotal(tax_amount=tax_amount)

    # Exportacion
    if mntExportacion > 0:
        tax_scheme = TaxScheme("9995", "EXP", "FRE")
        category_id = CategoryID(category_id="G", add_attributes=True)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(
            amount=mntExportacion, currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0, currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(
            tax_amount=tax_amount, taxable_amount=taxable_amount, tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # GRATUITO
    if mntTotalGrat > 0:
        tax_scheme = TaxScheme("9996", "GRA", "FRE")
        category_id = CategoryID(category_id="E", add_attributes=True)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(
            amount=mntTotalGrat, currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0, currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(
            tax_amount=tax_amount, taxable_amount=taxable_amount, tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # EXONERADO
    if mntExo > 0:
        tax_scheme = TaxScheme("9997", "EXO", "VAT")
        category_id = CategoryID(category_id="E", add_attributes=True)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)

        taxable_amount = TaxableAmount(amount=mntExo, currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0, currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(
            tax_amount=tax_amount, taxable_amount=taxable_amount, tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # EXENTO O INAFECTO
    if mntExe > 0:
        tax_scheme = TaxScheme("9998", "INA", "FRE")
        category_id = CategoryID(category_id="O", add_attributes=True)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)

        taxable_amount = TaxableAmount(amount=mntExe, currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0, currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(
            tax_amount=tax_amount, taxable_amount=taxable_amount, tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # IGV
    tax_scheme = TaxScheme("1000", "IGV", "VAT")
    category_id = CategoryID(category_id="S", add_attributes=True)
    tax_category = TaxCategory(category_id=category_id, tax_scheme=tax_scheme)
    taxable_amount = TaxableAmount(amount=mntNeto, currencyID=tipoMoneda)
    tax_amount = TaxAmount(amount=mntTotalIgv, currencyID=tipoMoneda)
    tax_subtotal = TaxSubtotal(
        tax_amount=tax_amount, taxable_amount=taxable_amount, tax_category=tax_category)

    tax_total.add_tax_subtotal(tax_subtotal)

    # ISC
    if mntTotalIsc > 0:
        tax_scheme = TaxScheme("2000", "ISC", "EXC")
        category_id = CategoryID(category_id="S", add_attributes=True)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(amount=mntNeto, currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=mntTotalIsc, currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(
            tax_amount=tax_amount, taxable_amount=taxable_amount, tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # FACTURA
    id = serie + "-" + str(correlativo).zfill(8)

    # BILLINGREFERENCE
    cod_id = referencia[0].get('serieRef') + "-" + \
        str(referencia[0].get('correlativoRef')).zfill(8)
    document_type_code = referencia[0].get("tipoDocumentoRef")
    invoice_document_reference = BillingReference.InvoiceDocumentReference(
        cod_id, document_type_code)

    billing_reference = BillingReference.BillingReference(
        invoice_document_reference)

    # DISCREPANCYRESPONSE -> FACTURA AFECTADA
    ref_id = referencia[0].get('serieRef') + "-" + \
        str(referencia[0].get('correlativoRef')).zfill(8)
    resp_code = tipoMotivoNotaModificatoria
    description = sustento
    discrepancy_response = DiscrepancyResponse.DiscrepancyResponse(
        ref_id, resp_code, description)

    # MONEDA
    document_currency_code = BasicGlobal.DocumentCurrencyCode(
        document_currency_code=tipoMoneda)

    # NUMERO DE DOCUMENTO
    nota_credito = DebitNote(
        doc_id=id,
        issue_date=issue_date,
        document_currency_code=document_currency_code,
        discrepancy_response=discrepancy_response,
        billing_reference=billing_reference,
        accounting_supplier_party=proveedor,
        accounting_customer_party=cliente,
        tax_total=tax_total,
        requested_monetary_total=requested_monetary_total
    )

    # LINEAS DE NOTA DE CRÉDITO
    for ord, line in enumerate(detalle):
        # CANTIDAD DE ITEMS
        debit_quantity = DebitNoteLine.DebitQuantity(
            quantity=line.get("cantidadItem", 0),
            unit_code=line.get('unidadMedidaItem')
        )

        # PRECIOS DE REFERENCIA
        line_extension_amount = LineExtensionAmount(
            amount=line.get("montoItem", 0), currencyID=tipoMoneda)

        precio = line.get('precioItem', 0) if not line.get(
            "no_onerosa") else line.get('precioItemReferencia', 0)
        price_code = "01" if not line.get("no_onerosa") else "02"
        price_amount = PriceAmount(amount=precio, currencyID=tipoMoneda)

        pricing_reference = PricingReference(
            price_amount=price_amount, price_code=price_code)

        # IMPUESTOS
        tax_amount = TaxAmount(amount=line.get("montoIgv", 0.0),
                               currencyID=tipoMoneda)
        tax_total = TaxTotal(tax_amount=tax_amount)

        cod_afectacion_igv = line.get("codAfectacionIgv", False)

        tasaIgv = 18.0
        # 9995 -	Exportación
        if cod_afectacion_igv in ["40"]:
            tax_scheme = TaxScheme("9995", "EXP", "EXP")
            tax_category = TaxCategory(category_id="G", percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "montoItem", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get(
                "montoIgv", 0.0), currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(
                taxable_amount=taxable_amount, tax_amount=tax_amount, tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 9996 -	Gratuito
        if cod_afectacion_igv in ["11", "12", "13", "14", "15", "16", "40", "21", "31", "32", "33", "34", "35", "36", "37"]:
            tax_scheme = TaxScheme("9996", "GRA", "FRE")
            tax_category = TaxCategory(
                category_id="E",
                percent=tasaIgv,
                tax_exemption_reason_code=line.get("codAfectacionIgv"),
                tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "montoItem", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get(
                "montoIgv", 0.0), currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(
                taxable_amount=taxable_amount, tax_amount=tax_amount, tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 9996 -	Inafecto
        if cod_afectacion_igv in ["30"]:
            tax_scheme = TaxScheme("9998", "INA", "FRE")
            tax_category = TaxCategory(category_id="O",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "montoItem", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get(
                "montoIgv", 0.0), currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(
                taxable_amount=taxable_amount, tax_amount=tax_amount, tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 1000 - IGV Impuesto General a las Ventas
        if cod_afectacion_igv in ["10"]:
            tax_scheme = TaxScheme("1000", "IGV", "VAT")
            tax_category = TaxCategory(category_id="S",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "montoItem", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get(
                "montoIgv", 0.0), currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(
                taxable_amount=taxable_amount, tax_amount=tax_amount, tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        item = Item(description=line.get('nombreItem'))
        price = Price(price_amount=line.get(
            'precioItemSinIgv'), currency_id=tipoMoneda)

        credit_note_line = DebitNoteLine.DebitNoteLine(
            ord=ord+1,
            debit_quantity=debit_quantity,
            line_extension_amount=line_extension_amount,
            pricing_reference=pricing_reference,
            tax_total=tax_total,
            item=item,
            price=price)

        nota_credito.add_credit_note_line(credit_note_line)

    nota_credito.set_file_name(
        str(numDocEmisor) + "-08-" + serie + "-" + str(correlativo).zfill(8))

    return nota_credito
