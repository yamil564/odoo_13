from . import validacion
from ..efact21.Documents import Factura
from ..efact21 import CustomerParty
from ..efact21 import SupplierParty
from ..efact21 import BasicGlobal
from ..efact21 import General
from ..efact21 import InvoiceLine
from ..efact21 import MonetaryTotal
from ..efact21 import Party
from ..efact21.AllowanceCharge import AllowanceCharge
from ..efact21.AmountTypes import Amount,PriceAmount, PrepaidAmount, ChargeTotalAmount, LineExtensionAmount, \
    AllowanceTotalAmount, PayableAmount, TaxInclusiveAmount
from ..efact21.BasicGlobal import RegistrationName,Note
from ..efact21.DocumentReference import DespatchDocumentReference, DocumentTypeCode,AdditionalDocumentReference
from ..efact21.OrderReference import OrderReference
from ..efact21.Lines import PricingReference, Item, Price
from ..efact21.Party import PartyIdentification, PartyLegalEntity, PartyName
from ..efact21.RegistrationAddress import RegistrationAddress
from ..efact21.TaxTotal import TaxTotal, TaxSubtotal, TaxCategory, TaxScheme, CategoryID, TaxableAmount, TaxAmount, BaseUnitMeasure, PerUnitAmount
from ..efact21.TaxScheme import TaxSchemeID
from ..efact21.PaymentTerms import PaymentTerms
from ..efact21.PaymentMeans import PaymentMeans

# import yaml
import re
import logging
_logger = logging.getLogger(__name__)
patron_cuota = re.compile("Cuota[0-9]{3}$")

# def validate_json(data):
#     with open("./files/schemas_json/invoice.yaml") as f:
#         spec = yaml.safe_load(f.read())

#     flex.core.validate(spec, data)


def build_factura(data):
    flag_error = False
    errors = []
    for field in validacion.fields_required:
        if field not in data:
            flag_error = True
            errors.append({
                "status": 400,
                "code": "01",
                "detail": validacion.error_list["01"].replace("$_PARAMETRO", field) + validacion.fields_required[field]
            })
    if flag_error:
        return {
            "errors": errors
        }

    tipoDocumento = data.get('tipoDocumento', '')
    fechaEmision = validacion.transformar_fecha(data.get('fechaEmision', ''))
    # correoReceptor = data.get('correoReceptor', '')
    documento = data.get('documento', False)
    detalle = data.get('detalle', False)
    descuento = data.get('descuento', False)
    # tipoEnvio = data.get('tipoEnvio', -1)
    # anticipos = data.get('anticipos', [])
    # facturaGuia = data.get("facturaGuia", {})
    # indicadores = data.get('indicadores', False)
    tipoOperacion = data.get("tipoOperacion",False)


    # indExportacion = False
    # if indicadores:
    #     indAnticipo = indicadores.get("indAnticipo", False)
    #     indExportacion = indicadores.get('indExportacion', False)
    #     indVentaItinerante = indicadores.get("indVentaItinerante", False)
    #     indVentaInterna = indicadores.get("indVentaInterna", False)

    #     arr = [["indAnticipo", (1 if indAnticipo else 0)],
    #            ["indExportacion", (1 if indExportacion else 0)],
    #            ["indVentaInterna", (1 if indVentaInterna else 0)],
    #            ["indVentaItinerante", (1 if indVentaItinerante else 0)]]

    #     mas_de_un_indicador = sum([x[1] for x in arr]) > 1
    #     sin_indicador = sum([x[1] for x in arr]) == 0

    #     if mas_de_un_indicador:
    #         flag_error = True
    #         errors.append({
    #             "status": 400,
    #             "code": "-",
    #             "detail": "Sólo puede habilitar un indicador en el comprobante"
    #         })
    #     elif sin_indicador:
    #         flag_error = True
    #         errors.append({
    #             "status": 400,
    #             "code": "-",
    #             "detail": "Debe asignar un indicador al comprobante. Los indicadores disponibles son: 'indAnticipo','indExportacion','indVentaInterna','indVentaItinerante' "
    #         })
    # else:
    #     errors.append({
    #         "status": 400,
    #         "code": "-",
    #         "detail": "No se ha encontrado el atributo 'indicadores'."
    #     })

    # if tipoEnvio < 0 or tipoEnvio > 2:
    #     flag_error = True
    #     errors.append({
    #         "status": 400,
    #         "code": "51",
    #         "detail": validacion.error_list[
    #             "51"] + " Tipo de Envio (tipoEnvio) no válido (0=Desarrollo, 1=Producción)."
    #     })

    if not fechaEmision:
        flag_error = True
        errors.append({
            "status": 400,
            "code": "51",
            "detail": validacion.error_list[
                "51"] + " Fecha de Emisión (fechaEmision) tiene formato incorrecto (yyyy-MM-dd)."
        })

    if not documento:
        flag_error = True
        errors.append({
            "status": 400,
            "code": "51",
            "detail": validacion.error_list["51"] + " Información de documento (documento) tiene formato incorrecto."
        })

    if not descuento:
        flag_error = True
        errors.append({
            "status": 400,
            "code": "51",
            "detail": validacion.error_list[
                "51"] + " Información de descuento (descuento) tiene formato incorrecto."
        })

    if not detalle:
        flag_error = True
        errors.append({
            "status": 400,
            "code": "51",
            "detail": validacion.error_list[
                "51"] + " Información del detalle de documento (detalle) tiene formato incorrecto."
        })

    if flag_error:
        return {
            "errors": errors
        }

    # VALIDACION DOCUMENTO
    for field in validacion.fields_required_doc_fac_bol:
        if field not in documento:
            flag_error = True
            errors.append({
                "status": 400,
                "code": "01",
                "detail": validacion.error_list["01"].replace("$_PARAMETRO", field) +
                          validacion.fields_required_doc_fac_bol[field]
                          })
    if ('mntNeto' not in documento) and ('mntExe' not in documento) and ('mntExo' not in documento):
        flag_error = True
        errors.append({
            "status": 400,
            "code": "51",
            "detail": validacion.error_list[
                "51"] + " Es necesario el Monto Neto (mntNeto) o el Monto Gravado (mntExe) o el Monto Exonerado (mntExo)."
        })

    # VALIDACION DETALLE
    for line in detalle:
        for field in validacion.fields_required_detalle_fac_bol:
            if field not in line:
                flag_error = True
                errors.append({
                    "status": 400,
                    "code": "01",
                    "detail": validacion.error_list["01"].replace("$_PARAMETRO", field) +
                              validacion.fields_required_detalle_fac_bol[field]
                              })

    if flag_error:
        return {
            "errors": errors
        }

    serie = documento.get('serie', False)
    correlativo = documento.get('correlativo', False)
    nombreEmisor = documento.get('nombreEmisor', False)
    tipoDocEmisor = documento.get('tipoDocEmisor', False)
    numDocEmisor = documento.get('numDocEmisor', False)
    tipoDocReceptor = documento.get('tipoDocReceptor', False)
    numDocReceptor = documento.get('numDocReceptor', False)
    nombreReceptor = documento.get('nombreReceptor', False)
    tipoMoneda = documento.get('tipoMoneda', False)
    mntTotal = documento.get('mntTotal', 0.0)
    mntTotalGrat = documento.get('mntTotalGrat', 0.0)
    mntTotalAnticipos = documento.get("mntTotalAnticipos", 0.0)
    mntExportacion = documento.get("mntExportacion", 0.0)
    
    formaPago = documento.get("formaPago","Contado")
    creditoCuotas = documento.get("creditoCuotas",[])
    
    if formaPago not in ["Contado","Credito"]:
        return {
            "errors":[
                {
                    "status":400,
                    "code": "51",
                    "detail":"El atributo forma de pago solo puede tomar los valores 'Contado' o 'Credito'"
                }
            ]
        }
    elif formaPago == "Credito":
        if len(creditoCuotas) == 0:
            return {
                "errors":[
                {
                    "status":400,
                    "code": "51",
                    "detail":"Si la forma de pago es crédito, entonces debe establecer por lo menos una cuota."
                }
            ]
            }
        for cc in creditoCuotas:
            if not patron_cuota.match(cc.get("nombre","")):
                return {
                    "errors":[
                        {
                            "status":400,
                            "code": "51",
                            "detail":"El nombre de la cuota '{}'".format(cc.get("nombre")+ "debe tener el siguiente formato 'cuota[0-9]{3}'. Ejemplo: cuota001,cuota002,...cuota015")
                        }
                    ]
                }
            if not validacion.transformar_fecha(cc.get("fechaVencimiento","")):
                return {
                    "errors":[
                        {
                            "status":400,
                            "code": "51",
                            "detail":"El formato de la fecha de vencimiento de la cuota '{}' no ha sido establecido o es inválido".format(cc.get("nombre"))
                        }
                    ]
                }
            if type(cc.get("monto",0.0)) not in [float,int]:
                if cc.get("monto",0.0) > 0:
                    return {
                        "errors":[
                            {
                                "status":400,
                                "code": "51",
                                "detail":"El monto de la cuota '{}' no ha sido establecido o es igual a cero.".format(cc.get("nombre"))
                            }
                        ]
                    }

    #NUMERO DE LA ORDEN DE COMPRA O SERVICIO
    ordenCompra = documento.get("ordenCompra",False)
    order_reference = None
    if ordenCompra:
        if  re.search("^\s*$",ordenCompra):
            return {
                "errors":[{
                    "status":400,
                    "code":"51",
                    "detail":"Orden de compra: No se permite espacios en blanco, saltos de línea, fin de línea, etc. "
                }]
            }
        order_reference = OrderReference(order_reference_id=ordenCompra,order_type_code_required=False)

    documentosRelacionados = documento.get("documentosRelacionados",[])

    for dr in documentosRelacionados:
        if re.search("^\s*$",dr.get("number")):
            return {
                "errors":[{
                    "status":400,
                    "code":"51",
                    "detail":"Documento relacionado: No se permite espacios en blanco, saltos de línea, fin de línea, etc."
                }]
            }
        if dr.get("type_code") not in ["01","02","03","04","05","06","07","08","09","99"]:
            return {
                "errors":[{
                    "status":400,
                    "code":"51",
                    "detail":"Los tipos de documento permitidos son: '01','02','03','04','05','06','07','08','09','99'"
                }]
            }

    # NO NECESARIOS
    # direccionOrigen = documento.get('direccionOrigen', '')
    # direccionUbigeo = documento.get('direccionUbigeo', '')

    # nombreComercialEmisor = documento.get('nombreComercialEmisor', '')
    # nombreComercialReceptor = documento.get('nombreComercialReceptor', '')
    # tipoDocReceptorAsociado = documento.get('tipoDocReceptorAsociado', '')
    # numDocReceptorAsociado = documento.get('numDocReceptorAsociado', '')
    # nombreReceptorAsociado = documento.get('nombreReceptorAsociado', '')
    # direccionDestino = documento.get('direccionDestino', '')#SOLO BOLETA
    # sustento = documento.get('sustento', '') #SOLO NOTAS
    # tipoMotivoNotaModificatoria = documento.get('tipoMotivoNotaModificatoria', '') #SOLO NOTAS
    mntNeto = documento.get('mntNeto', 0.0)
    mntExe = documento.get('mntExe', 0.0)
    mntExo = documento.get('mntExo', 0.0)
    mntTotalIgv = documento.get('mntTotalIgv', 0.0)
    mntTotalIsc = documento.get('mntTotalIsc', 0.0)
    mntICBPER = documento.get("mntICBPER", 0.0)
    fechaVencimiento = documento.get('fechaVencimiento', 0.0)
    
    # glosaDocumento = documento.get('glosaDocumento', '')
    # codCentroCosto = documento.get('codCentroCosto', '')
    # tipoCambioDestino = documento.get('tipoCambioDestino', '')
    # mntTotalOtros = documento.get('mntTotalOtros', 0.0)
    mntTotalOtrosCargos = documento.get('mntTotalOtrosCargos', 0.0)
    # mntTotalAnticipos = documento.get('mntTotalAnticipos', 0.0)
    # tipoFormatoRepresentacionImpresa = documento.get('tipoFormatoRepresentacionImpresa', '')
    # numero_guia = documento.get("numero_guia", False)
    # percepcion = data.get("percepcion", None)
    detraccion = data.get("detraccion", None)

    mntDescuentoGlobal = descuento.get('mntDescuentoGlobal', 0.0)
    mntTotalDescuentos = descuento.get('mntTotalDescuentos', 0.0)

    # if indExportacion:
    #     for line in detalle:
    #         if line.get('codAfectacionIgv') != "40":
    #             return {
    #                 "errors": [{
    #                     "status": 400,
    #                     "code": "51",
    #                     "detail": validacion.error_list["51"] +
    #                     " El Tipo de Afectacion IGV(codAfectacionIgv) del detalle deber ser igual a '40' "
    #                     "en caso de exportaciones."
    #                 }]
    #             }

    # TIPO DE DOCUMENTO
    invoice_type_code = BasicGlobal.InvoiceTypeCode(tipoDocumento, listID=tipoOperacion)

    
    # DETRACCION
    payment_terms_detraction = None
    payment_means_detraction = None

    if detraccion != None:
        payment_means_detraction = PaymentMeans(id="Detraccion",
                                                payment_means_code=detraccion.get("medio_pago"),
                                                payee_financial_account=detraccion.get("numero_cuenta_banco_nacion"))
        
        payment_terms_detraction = PaymentTerms(id="Detraccion",
                                                payment_means_id=detraccion.get("codigo"),
                                                payment_percent=detraccion.get("tasa"),
                                                amount=Amount(detraccion.get("monto"),currencyID="PEN"),
                                                detraction=True)

    # PROVEEDOR
    registration_name = RegistrationName(registration_name=nombreEmisor)
    party_identification = PartyIdentification(
        id_document=numDocEmisor, document_type=tipoDocEmisor)

    registration_address = RegistrationAddress(address_type_code="0000", address=None,
                                               urbanization=None, province_name=None,
                                               ubigeo=None,
                                               departament=None, district=None,
                                               country_code="PE")
    party_legal_entity = PartyLegalEntity(registration_name=registration_name,
                                          registration_address=registration_address)

    party_name = PartyName(nombreEmisor)

    party = Party.Party(party_name=party_name,
                        party_legal_entity=party_legal_entity,
                        party_identification=party_identification)

    proveedor = SupplierParty.AccountingSupplierParty(party=party)

    # CLIENTE
    party_legal_entity = PartyLegalEntity(registration_name=nombreReceptor)
    party_identification = PartyIdentification(id_document=numDocReceptor,
                                               document_type=tipoDocReceptor)
    party = CustomerParty.Party(party_identification=party_identification,
                                party_legal_entity=party_legal_entity)
    cliente = CustomerParty.AccountingCustomerParty(party=party)

    # DESCUENTO GLOBAL
    descuento_global = None
    if "descuentoGlobal" in documento:
        documento_descuento_global = documento["descuentoGlobal"]
        if ("factor" in documento_descuento_global) and ("montoDescuento" in documento_descuento_global) and ("montoBase" in documento_descuento_global):
            descuento_global = AllowanceCharge(charge_indicator=False,
                                               allowance_charge_reason_code="02",
                                               multiplier_factor_numeric=documento_descuento_global.get(
                                                   "factor", 0.0),  # Porcentaje del descuento
                                               amount=documento_descuento_global.get(
                                                   "montoDescuento"),
                                               # base_amount es el monto total de la línea sin IGV y sin descuento
                                               base_amount=documento_descuento_global.get(
                                                   "montoBase"),
                                               currency_id=tipoMoneda)

    #RETENCIÓN
    retencion = None
    if "retencion" in documento:
        documento_retencion = documento["retencion"]
        if ("factor" in documento_retencion) and ("montoRetencion" in documento_retencion) and ("montoBase" in documento_retencion):
            retencion = AllowanceCharge(charge_indicator=False,
                                                allowance_charge_reason_code="62",
                                                multiplier_factor_numeric=documento_retencion.get(
                                                    "factor", 0.0),  # Porcentaje de la retención
                                                amount=documento_retencion.get(
                                                    "montoRetencion"),
                                                base_amount=documento_retencion.get(
                                                    "montoBase"),
                                                currency_id=tipoMoneda)
    # MONTO DE PAGO
    prepaid_amount = None
    charge_total_amount = None
    if mntTotalAnticipos > 0 :
        prepaid_amount = PrepaidAmount(amount=round(mntTotalAnticipos, 2), currencyID=tipoMoneda)
    if mntTotalOtrosCargos > 0:
        charge_total_amount = ChargeTotalAmount(amount=round( mntTotalOtrosCargos, 2), currencyID=tipoMoneda)

    line_extension_amount = LineExtensionAmount(amount=round( mntNeto + mntExe + mntExo + mntExportacion, 2), currencyID=tipoMoneda)
    allowance_total_amount = AllowanceTotalAmount(amount=round(0, 2), currencyID=tipoMoneda)
    payable_amount = PayableAmount(amount=round(mntTotal, 2), currencyID=tipoMoneda)
    tax_inclusive_amount = TaxInclusiveAmount(amount=round(mntNeto + mntExe + mntExo + mntTotalIgv +mntExportacion, 2), currencyID=tipoMoneda)

    legal_monetary_total = MonetaryTotal.LegalMonetaryTotal(line_extension_amount=line_extension_amount,
                                                            prepaid_amount=prepaid_amount,
                                                            payable_amount=payable_amount,
                                                            allowance_total_amount=allowance_total_amount,
                                                            charge_total_amount=charge_total_amount,
                                                            tax_inclusive_amount=tax_inclusive_amount)
    # FECHA DE VENCIMIENTO
    due_date = General.DueDate(due_date=fechaVencimiento) if fechaVencimiento else None

    # FECHA DE EMISIÓN
    issue_date = General.IssueDate(date=fechaEmision)

    # IMPUESTOS
    tax_amount = TaxAmount(amount=mntTotalIgv + mntTotalIsc,
                           currencyID=tipoMoneda)
    tax_total = TaxTotal(tax_amount=tax_amount)

    # Exportacion
    if mntExportacion > 0:
        tax_scheme = TaxScheme("9995", "EXP", "FRE")
        category_id = CategoryID(category_id="G", add_attributes=False)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(amount=mntExportacion,
                                       currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0,
                               currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                   taxable_amount=taxable_amount,
                                   tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # GRATUITO
    if mntTotalGrat > 0:
        tax_scheme = TaxScheme("9996", "GRA", "FRE")
        category_id = CategoryID(category_id="Z", add_attributes=False)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(amount=mntTotalGrat,
                                       currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0,
                               currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                   taxable_amount=taxable_amount,
                                   tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # EXONERADO
    if mntExo > 0:
        tax_scheme = TaxScheme("9997", "EXO", "VAT")
        category_id = CategoryID(category_id="E", add_attributes=False)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)

        taxable_amount = TaxableAmount(amount=mntExo,
                                       currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=0,
                               currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                   taxable_amount=taxable_amount,
                                   tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # EXENTO O INAFECTO
    if mntExe > 0:
        tax_scheme = TaxScheme("9998", "INA", "FRE")
        category_id = CategoryID(category_id="E", add_attributes=False)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)

        tax_amount = TaxAmount(amount=0,
                               currencyID=tipoMoneda)
        taxable_amount = TaxableAmount(amount=mntExe,
                                       currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                   taxable_amount=taxable_amount,
                                   tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # IGV
    if mntExportacion == 0:
        tax_scheme_id = TaxSchemeID("1000", True)
        tax_scheme = TaxScheme(tax_scheme_id, "IGV", "VAT")
        category_id = CategoryID(category_id="S", add_attributes=False)
        tax_category = TaxCategory(category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(amount=mntNeto,
                                    currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=mntTotalIgv,
                            currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                taxable_amount=taxable_amount,
                                tax_category=tax_category)

        tax_total.add_tax_subtotal(tax_subtotal)

    # ISC
    if mntTotalIsc > 0:
        tax_scheme = TaxScheme("2000", "ISC", "EXC")
        category_id = CategoryID(category_id="S", add_attributes=False)
        tax_category = TaxCategory(
            category_id=category_id, tax_scheme=tax_scheme)
        taxable_amount = TaxableAmount(amount=mntNeto,
                                       currencyID=tipoMoneda)
        tax_amount = TaxAmount(amount=mntTotalIsc,
                               currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                   taxable_amount=taxable_amount,
                                   tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # ICBPER
    if mntICBPER > 0:
        tax_scheme = TaxScheme("7152", "ICBPER", "OTH")
        tax_category = TaxCategory(tax_scheme=tax_scheme)

        tax_amount = TaxAmount(amount=mntICBPER,
                               currencyID=tipoMoneda)
        tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                   tax_category=tax_category)
        tax_total.add_tax_subtotal(tax_subtotal)

    # FACTURA
    id = serie + "-" + str(correlativo).zfill(8)
    fact = Factura(ubl_extensions=None, ubl_version="2.1", id=id,
                   issue_date=issue_date, issue_time=None, due_date=due_date,
                   invoice_type_code=invoice_type_code, document_currency_code=tipoMoneda,
                   customization="2.0",accounting_supplier_party=proveedor, accounting_customer_party=cliente,
                   legal_monetary_total=legal_monetary_total, tax_total=tax_total,
                   descuento_global=descuento_global,retencion=retencion,order_reference=order_reference,
                   payment_means_detraction=payment_means_detraction,payment_terms_detraction=payment_terms_detraction)
    
    if detraccion != None:
        fact.add_note(Note("Operación sujeta a detracción",languageLocaleID="2006"))

    if formaPago == "Credito":
        formaPago_credito_total = round(sum([cuota.get("monto") for cuota in creditoCuotas]),2)
        amount = Amount(formaPago_credito_total,currencyID=tipoMoneda)
        fact.add_payment_terms(PaymentTerms(id="FormaPago",
                                            payment_means_id=formaPago,
                                            amount=amount))
        for cuota in creditoCuotas:
            monto_cuota = Amount(cuota["monto"],currencyID=tipoMoneda)
            fact.add_payment_terms(PaymentTerms(id="FormaPago",
                                                payment_means_id=cuota["nombre"],
                                                amount=monto_cuota,
                                                payment_due_date=cuota["fechaVencimiento"]))
    elif formaPago == "Contado":
        fact.add_payment_terms(PaymentTerms(id="FormaPago",
                                            payment_means_id=formaPago))

    for dr in documentosRelacionados:
        adr = AdditionalDocumentReference(id=dr.get("number"),document_type_code=dr.get("type_code","00"))
        fact.add_additional_document_reference(adr)


    if documento.get('numero_guia', False):
        guia_doc_type_code = DocumentTypeCode("09")
        guia_doc_type_code.listName = "Tipo de Documento"
        guia_doc_type_code.listURI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01"
        desp_doc_ref = DespatchDocumentReference(
            documento['numero_guia'], guia_doc_type_code)
        fact.despatch_document_reference = desp_doc_ref

    # LINEAS
    for line in detalle:
        invoice_quantity = InvoiceLine.InvoicedQuantity(quantity=line.get("cantidadItem", 0),
                                                        unit_code=line.get('unidadMedidaItem'))
        line_extension_amount = LineExtensionAmount(
            amount=line.get("montoItem", 0), currencyID=tipoMoneda)

        precio = line.get('precioItem', 0) if not line.get(
            "no_onerosa") else line.get('precioItemReferencia', 0)
        price_code = "01" if not line.get("no_onerosa") else "02"
        price_amount = PriceAmount(amount=precio, currencyID=tipoMoneda)
        pricing_reference = PricingReference(price_amount=price_amount,
                                             price_code=price_code)

        tax_amount = TaxAmount(amount=line.get("montoIgv", 0.0),
                               currencyID=tipoMoneda)
        tax_total = TaxTotal(tax_amount=tax_amount)

        cod_afectacion_igv = line.get("codAfectacionIgv", False)

        tasaICBPER = line.get("tasa_ICBPER", 10)
        afectacion_icbper = line.get("afectacionICBPER", False)

        tasaIgv = line.get("tasaIgv",0)
        # 1000 - IGV Impuesto General a las Ventas
        if cod_afectacion_igv in ["10"]:
            tax_scheme = TaxScheme("1000", "IGV", "VAT")
            tax_category = TaxCategory(category_id="S",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get("montoItem", 0.0),
                                           currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get("montoIgv", 0.0),
                                   currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(taxable_amount=taxable_amount,
                                       tax_amount=tax_amount,
                                       tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 9995 -	Exportación
        if cod_afectacion_igv in ["40"]:
            tax_scheme = TaxScheme("9995", "EXP", "FRE")
            tax_category = TaxCategory(category_id="G",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "montoItem", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get(
                "montoIgv", 0.0), currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(taxable_amount=taxable_amount,
                                       tax_amount=tax_amount,
                                       tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 9996 -	Gratuito
        if cod_afectacion_igv in ["11", "12", "13", "14", "15", "16", "21", "31", "32", "33", "34", "35", "36",
                                  "37"]:
            tax_scheme = TaxScheme("9996", "GRA", "FRE")
            tax_category = TaxCategory(category_id="Z",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get("montoItem", 0.0),
                                           currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get("montoIgv", 0.0),
                                   currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(taxable_amount=taxable_amount,
                                       tax_amount=tax_amount,
                                       tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 9997 - Exonerado
        if cod_afectacion_igv in ["20"]:
            tax_scheme = TaxScheme("9997", "EXO", "VAT")
            tax_category = TaxCategory(category_id="E",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "montoItem", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get("montoIgv", 0.0),
                                   currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(taxable_amount=taxable_amount,
                                       tax_amount=tax_amount,
                                       tax_category=tax_category)
            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        # 9998 -	Inafecto
        if cod_afectacion_igv in ["30"]:
            tax_scheme = TaxScheme("9998", "INA", "FRE")
            tax_category = TaxCategory(category_id="O",
                                       percent=tasaIgv,
                                       tax_exemption_reason_code=line.get(
                                           "codAfectacionIgv"),
                                       tax_scheme=tax_scheme)
            taxable_amount = TaxableAmount(amount=line.get(
                "precioItemReferencia", 0.0), currencyID=tipoMoneda)
            tax_amount = TaxAmount(amount=line.get("montoIgv", 0.0),
                                   currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(taxable_amount=taxable_amount,
                                       tax_amount=tax_amount,
                                       tax_category=tax_category)

            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        if afectacion_icbper:
            per_unit_amount = PerUnitAmount(
                amount=tasaICBPER, currencyID=tipoMoneda)
            tax_scheme = TaxScheme("7152", "ICBPER", "OTH")
            tax_category = TaxCategory(per_unit_amount=per_unit_amount,
                                       tax_scheme=tax_scheme)

            base_unit_measure = BaseUnitMeasure(quantity=round(line.get("cantidadItem", 0)),
                                                unit_code=line.get('unidadMedidaItem'))

            tax_amount = TaxAmount(amount=round(line.get("cantidadItem", 0.0)*tasaICBPER, 2),
                                   currencyID=tipoMoneda)

            tax_subtotal = TaxSubtotal(tax_amount=tax_amount,
                                       base_unit_measure=base_unit_measure,
                                       tax_category=tax_category)

            tax_total.add_tax_subtotal(tax_subtotal=tax_subtotal)

        item = Item(description=line.get('nombreItem'),commodity_classification=line.get("sunatCode",None))
        price = Price(price_amount=line.get('precioItemSinIgv'),
                      currency_id=tipoMoneda)

        descuento = None
        if "descuento" in line:
            line_descuento = line["descuento"]
            if "factor" in line_descuento and "montoDescuento" in line_descuento and "montoBase" in line_descuento:
                descuento = AllowanceCharge(charge_indicator=False,
                                            allowance_charge_reason_code="00",
                                            multiplier_factor_numeric=line_descuento.get(
                                                "factor", 0.0),  # Porcentaje del descuento
                                            amount=line_descuento.get(
                                                "montoDescuento"),
                                            # base_amount es el monto total de la línea sin IGV y sin descuento
                                            base_amount=line_descuento.get(
                                                "montoBase"),
                                            currency_id=tipoMoneda)

        invoice_line = InvoiceLine.InvoiceLine(invoice_quantity=invoice_quantity,
                                               line_extension_amount=line_extension_amount,
                                               pricing_reference=pricing_reference,
                                               tax_total=tax_total,
                                               item=item,
                                               price=price,
                                               descuento=descuento)

        fact.add_invoice_line(invoice_line)

    fact.set_file_name(str(numDocEmisor) + "-" + tipoDocumento +
                       "-" + serie + "-" + str(correlativo).zfill(8))

    return fact
