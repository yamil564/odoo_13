# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tnc, tnd, tdc, tdr
from pytz import timezone
from datetime import datetime, timedelta
from odoo.addons.gestionit_pe_fe.models.account.oauth import send_doc_xml, generate_and_signed_xml
import base64
import re
# import urllib
# import json
import logging
# import requests
from collections import defaultdict
from odoo.tools import float_is_zero
patron_dni = re.compile("\d{8}$")
_logger = logging.getLogger(__name__)

codigo_unidades_de_medida = [
    "DZN","DAY","HUR","LTR","NIU","CMT","GLL","OZI","GRM","GLL","KGM","LBR","MTR","LBR","SMI","ONZ","FOT","INH","LTN","BX","MTQ",
    '4A','BJ','BLL','BG','BO','BX','CT','CMK','CMQ','CEN','CY','CJ','DZP','BE','GLI','GRO','HLT','LEF','SET','KWH','KT','CA','MWH','MTK','MTQ','MGM','MLT','MMT','MMK','MMQ','MLL','UM','PF','PK','PR','FTK','FTQ','C62','PG','ST','RM','DR','STN','TNE','TU','ZZ','YRD','YDK'
]
codigos_tipo_afectacion_igv = [
    "10", "11", "12", "13", "14", "15", "16", "20", "30", "31", "34", "35", "36", "40"
]


class AccountMoveDocumentReference(models.Model):
    _name = "account.move.document.reference"
    _description = "Otros documentos relacionados con la operación"

    move_id = fields.Many2one("account.move")
    document_type_code = fields.Selection(
        selection=tdr, string="Tipo de documento")
    document_number = fields.Char("Número de documento")

    def get_name_tdr(self, code):
        res = [c[1] for c in tdr if c[0] == code]
        return res[0] if len(res) > 0 else ""


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_warehouse_ids(self):
        if self._context.get("default_type", "entry") in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
            user = self.env.user
            allowed_company_ids = self._context.get("allowed_company_ids")
            wh_ids = user.sudo().warehouse_ids.filtered(
                lambda r: r.company_id.id in allowed_company_ids)
            if len(wh_ids) > 0:
                return wh_ids.ids
            else:
                raise UserError(
                    "Para crear un comprobante de venta/compra su usuario debe estar asociado a un almacén de la compañia. Comuníquese con su administrador.")
        return False

    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén")

    warehouses_allowed_ids = fields.Many2many(
        "stock.warehouse", string="Almacenes Permitidos", default=_get_default_warehouse_ids)

    journal_ids = fields.Many2many(
        "account.journal", string="Series permitidas", related="warehouse_id.journal_ids")

    journal_type = fields.Selection(
        selection=[("sale", "Venta"), ("purchase", "compra")])

    document_reference_ids = fields.One2many(
        "account.move.document.reference", "move_id", string="Otros documentos relacionados")

    credit_note_ids = fields.One2many("account.move", "reversed_entry_id")

    credit_note_count = fields.Integer(
        "Número de notas de crédito", compute='_compute_credit_count')

    account_summary_id = fields.Many2one("account.summary",
                                         string="Resumen Diario",
                                         ondelete="set null",copy=False,
                                         default=False)

    


    @api.depends('credit_note_ids')
    def _compute_credit_count(self):
        for inv in self:
            self.env.cr.execute(
                "select count(*) from account_move where reversed_entry_id = {}".format(inv.id))
            result = self.env.cr.fetchall()
            inv.credit_note_count = result[0][0]



    def action_view_credit_notes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Notas de Crédito',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('reversed_entry_id', '=', self.id)],
        }



    @api.model
    def default_get(self, fields_list):
        res = super(AccountMove, self).default_get(fields_list)
        refund_id = self._context.get("default_refund_invoice_id", False)
        domain = []
        # _logger.info(self.env.user)
        user = self.env.user

        if user.active:
            allowed_company_ids = self._context.get("allowed_company_ids", [user.company_id.id])
            # _logger.info(self._context)
            # _logger.info(user.warehouse_ids)
            # _logger.info(allowed_company_ids)
            warehouse_ids = user.warehouse_ids.filtered(
                lambda r: r.company_id.id in allowed_company_ids)

            if len(warehouse_ids) > 0:
                res.update({"warehouse_id": warehouse_ids[0].id})
                journal_ids = warehouse_ids[0].journal_ids.filtered(lambda r: r.invoice_type_code_id == res.get(
                    "invoice_type_code") and r.type == res.get("journal_type"))
                if len(journal_ids) > 0:
                    res.update({"journal_id": journal_ids[0].id})

            if refund_id:
                refund_obj = self.env["account.move"].browse(refund_id)
                domain += [['tipo_comprobante_a_rectificar',
                            'in', [refund_obj.invoice_type_code]]]

        return res

    invoice_type_code = fields.Selection(selection=[('00', 'Otros'),
                                                    ('01', 'Factura'),
                                                    ('03', 'Boleta'),
                                                    ('07', 'Nota de crédito'),
                                                    ('08', 'Nota de débito'),
                                                    ('91', 'Comprobante de No Domiciliado'),
                                                    ('97', 'Nota de Crédito-No Domiciliado'),
                                                    ('98', 'Nota de Dédito-No Domiciliado')],
                                         string="Tipo de Comprobante",
                                         readonly=True
                                         )

    ##### DOMAIN DINAMICO PARA TIPOS DE DOCUMENTO VENTA Y COMPRA ########
    def _selection_tipo_documento_table_10(self):
        return [i[0] for i in tdc]

    """@api.onchange('invoice_type_code','journal_ids','journal_type','type','warehouse_id')
    def set_domain_for_journal_id(self):
        for rec in self:
            if rec.invoice_type_code and rec.journal_ids and rec.journal_type and rec.warehouse_id and rec.type in ['out_invoice','out_refund']:
                res={}
                res['domain']={'journal_id':[
                    ('invoice_type_code_id','=',rec.invoice_type_code),
                    #('id','in',[i.id for i in rec.journal_ids]),
                    ('type','=',rec.journal_type)]}
                
                return res

            elif rec.invoice_type_code and rec.journal_ids and rec.journal_type and rec.warehouse_id and rec.type in ['in_invoice','in_refund']:
                res={}
                res['domain']={'journal_id':[
                    ('invoice_type_code_id','=',self._selection_tipo_documento_table_10()),
                    #('id','in',[i.id for i in rec.journal_ids]),
                    ('type','=',rec.journal_type)]}
                
                return res"""

    #####################################################################
    @api.onchange('invoice_type_code','journal_ids','journal_type','type','warehouse_id')
    def set_domain_for_journal_id(self):
        for rec in self:

            if rec.invoice_type_code and rec.journal_ids and rec.journal_type and rec.warehouse_id and rec.type in ['in_invoice','in_refund']:
                res={}
                res['domain']={'journal_id':[
                    ('invoice_type_code_id','=',self._selection_tipo_documento_table_10()),
                    #('id','in',[i.id for i in rec.journal_ids]),
                    ('type','=',rec.journal_type)]}
                
                return res


    #####################################################################

    account_log_status_ids = fields.One2many(
        "account.log.status", "account_move_id", string="Registro de Envíos", copy=False)
    current_log_status_id = fields.Many2one("account.log.status", copy=False)

    estado_emision = fields.Selection(
        selection=[
            ('A', 'Aceptado'),
            ('E', 'Enviado a SUNAT'),
            ('N', 'Envio Erróneo'),
            ('O', 'Aceptado con Observación'),
            ('R', 'Rechazado'),
            ('P', 'Pendiente de envió a SUNAT'),
        ],
        string="Estado Emisión a SUNAT",
        related="current_log_status_id.status",
        store=True
    )

    sustento_nota = fields.Text(string="Sustento de nota", readonly=True, states={
                                'draft': [('readonly', False)]}, copy=False)

    tipo_nota_credito = fields.Selection(string='Tipo de Nota de Crédito', readonly=True,
                                         selection="_selection_tipo_nota_credito", states={'draft': [('readonly', False)]})
    tipo_nota_debito = fields.Selection(string='Tipo de Nota de Débito', readonly=True,
                                        selection="_selection_tipo_nota_debito", states={'draft': [('readonly', False)]})

    order_reference = fields.Char("Número de la orden de compra")

    def _selection_tipo_nota_credito(self):
        return tnc

    def _selection_tipo_nota_debito(self):
        return tnd

    estado_comprobante_electronico = fields.Selection(selection=[("0_NO_EXISTE", "NO EXISTE"),
                                                                 ("1_ACEPTADO",
                                                                  "ACEPTADO"),
                                                                 ("2_ANULADO",
                                                                  "ANULADO"),
                                                                 ("3_AUTORIZADO",
                                                                  "AUTORIZADO"),
                                                                 ("4_NO_AUTORIZADO",
                                                                  "NO AUTORIZADO"),
                                                                 ("-", "-")], default="-", copy=False)

    estado_contribuyente_ruc = fields.Selection(selection=[("00_ACTIVO", "ACTIVO"),
                                                           ("01_BAJA_PROVISIONAL",
                                                            "BAJA PROVISIONAL"),
                                                           ("02_BAJA_PROV_POR_OFICIO",
                                                            "BAJA PROV. POR OFICIO"),
                                                           ("03_SUSPENSION_TEMPORAL",
                                                            "SUSPENSION TEMPORAL"),
                                                           ("10_BAJA_DEFINITIVA",
                                                            "BAJA DEFINITIVA"),
                                                           ("11_BAJA_DE_OFICIO",
                                                            "BAJA DE OFICIO"),
                                                           ("22_INHABILITADO-VENT.UNICA",
                                                            "INHABILITADO-VENT.UNICA"),
                                                           ("-", "-")], default="-", copy=False)

    condicion_domicilio_contribuyente = fields.Selection(selection=[("00_HABIDO", "HABIDO"),
                                                                    ("09_PENDIENTE",
                                                                     "PENDIENTE"),
                                                                    ("11_POR_VERIFICAR",
                                                                     "POR VERIFICAR"),
                                                                    ("12_NO_HABIDO",
                                                                     "NO HABIDO"),
                                                                    ("20_NO_HALLADO",
                                                                     "NO HALLADO"),
                                                                    ("-", "-")], default="-", copy=False)

    consulta_validez_observaciones = fields.Text(
        "Consulta Validez - Observaciones", copy=False)

    documento_baja_id = fields.Many2one(
        "account.comunicacion_baja", copy=False)
    # documento_baja_state = fields.Selection(
    #     string="Estado del Documento de Baja", related="documento_baja_id.state", copy=False)

    documento_baja_state = fields.Selection(selection=[
            ('A', 'Aceptado'),
            ('E', 'Enviado a SUNAT'),
            ('N', 'Envio Erróneo'),
            ('O', 'Aceptado con Observación'),
            ('R', 'Rechazado'),
            ('P', 'Pendiente de envió a SUNAT')
        ],
        string="Estado del Documento de Baja", compute="_compute_documento_baja_state", copy=False)

    def _compute_documento_baja_state(self):
        for record in self:
            if record.documento_baja_id:
                record.documento_baja_state = record.documento_baja_id.state
                return
            elif record.account_summary_id:
                if record.account_summary_id.cod_operacion == '3':
                    record.documento_baja_state = record.account_summary_id.estado_emision
                    return
            record.documento_baja_state = False


    resumen_anulacion_id = fields.Many2one("account.summary", copy=False)
    resumen_anulacion_state = fields.Selection(
        related="resumen_anulacion_id.estado_emision", copy=False)

    anulacion_comprobante = fields.Char(
        "Anulación de Comprobante", compute="_compute_obtener_estado_anulacion_comprobante")

    def _compute_obtener_estado_anulacion_comprobante(self):
        for record in self:
            if record.documento_baja_id:
                record.anulacion_comprobante = record.documento_baja_state
            elif record.resumen_anulacion_id:
                record.anulacion_comprobante = record.resumen_anulacion_state
            else:
                record.anulacion_comprobante = "-"


    #######################################################################
    @api.depends("amount_total", "type_detraction", "detraction_rate","is_invoice_in_me")
    def _compute_original_amount_detraction(self):
        for record in self:

            record.original_detraction_amount = round(
                record.amount_total*record.detraction_rate/100,2)

            if record.is_invoice_in_me:
                record.original_detraction_amount_pen = round(
                    record.exchange_rate_day*record.amount_total*record.detraction_rate/100,2)
    #######################################################################


    @api.depends("amount_total", "type_detraction", "detraction_rate","is_invoice_in_me")
    def _compute_amount_detraction(self):
        for record in self:

            record.detraction_amount = round(
                record.amount_total*record.detraction_rate/100)

            record.detraction_amount_pen = round(
                record.exchange_rate_day*record.amount_total*record.detraction_rate/100)

    ####### CAMPO DETECTOR SI DOC ES EN ME
    is_invoice_in_me = fields.Boolean(string="Es Documento en Moneda Extranjera",
        compute="compute_is_invoice_in_me",
        store=True)


    @api.depends('company_id','currency_id')
    def compute_is_invoice_in_me(self):
        for rec in self:
            rec.is_invoice_in_me = False
            if rec.currency_id and rec.currency_id != rec.company_id.currency_id:
                rec.is_invoice_in_me = True
            else:
                rec.is_invoice_in_me = False
    #########################################################

    # @api.onchange("amount_total", "type_detraction","detraction_rate")
    # def onchange_amount_detraction(self):
    #     for record in self:
    #         record.detraction_amount_pen = round(record.exchange_rate_day*record.amount_total*record.detraction_rate/100,2)

    has_detraction = fields.Boolean("Detracción?")
    type_detraction = fields.Many2one(
        "sunat.catalog.54", string="Tipo de detracción")
    account_journal_national_bank = fields.Many2one("res.partner.bank", domain=[(
        "is_national_bank_detraction", "=", True)], default=lambda self: self.env.company.default_national_bank_account_id.id)

    detraction_rate = fields.Float("Tasa %", default=0)
    detraction_code = fields.Char("Código")
    bank_account_number_national = fields.Char("Banco de la nación")
    
    ##############################################################
    original_detraction_amount = fields.Float(
        "Monto Exacto de Detracción", compute="_compute_original_amount_detraction", store=True)
    original_detraction_amount_pen = fields.Float(
        "Monto Exacto de Detracción PEN", compute="_compute_original_amount_detraction", store=True)
    ##############################################################

    detraction_amount = fields.Float(
        "Monto de Detracción", compute="_compute_amount_detraction", store=True)
    detraction_amount_pen = fields.Float(
        "Monto de Detracción PEN", compute="_compute_amount_detraction", store=True)
    

    detraction_medio_pago = fields.Many2one("sunat.catalog.59",
                                            string="Medio de Pago",
                                            default=lambda self: self.env.ref("gestionit_pe_fe.catalog_59_001", raise_if_not_found=False))
    paymentterm_line = fields.One2many("paymentterm.line", "move_id")

    invoice_payment_term_type = fields.Char(
        compute="_compute_invoice_payment_term_type")


    ################################### RESTRICCIÓN PARA LAS FECHAS DE VENCIMIENTO Y FECHAS DE CUOTAS #########
    @api.constrains("invoice_date_due", "paymentterm_line","paymentterm_line.date_due")
    def check_invoice_date_due_vs_cuotas(self):
        for record in self:

            if record.invoice_date_due and record.paymentterm_line and record.paymentterm_line.mapped('date_due'):
                _logger.info('\n\nENTRE \n\n')
                date_due_max = max(record.paymentterm_line.mapped('date_due'))
                if record.invoice_date_due < date_due_max:
                    raise UserError(
                        "Ninguna de las Fechas de Pago de las Cuotas debe ser mayor a la Fecha de Vencimiento del Documento !!")

    ##################################################################
    @api.constrains("invoice_date_due", "paymentterm_line","paymentterm_line.date_due")
    def check_invoice_date_emission_vs_cuotas(self):
        for record in self:

            if record.invoice_date and record.paymentterm_line and record.paymentterm_line.mapped('date_due'):
                _logger.info('\n\nENTRE \n\n')
                date_due_min = min(record.paymentterm_line.mapped('date_due'))
                if record.invoice_date >= date_due_min:
                    raise UserError(
                        "La fecha de vencimiento de las cuotas deben de ser posteriores a la fecha de emisión del comprobante !")   

    ###################################################################

    @api.depends("invoice_payment_term_id", "invoice_date_due")
    def _compute_invoice_payment_term_type(self):
        for record in self:
            record.invoice_payment_term_type = "Contado"
            if record.invoice_payment_term_id:
                record.invoice_payment_term_type = record.invoice_payment_term_id.type
            else:
                if record.invoice_date_due:
                    if (record.invoice_date != False and record.invoice_date_due > record.invoice_date) or \
                            (record.invoice_date == False and record.invoice_date_due > datetime.now(tz=timezone("America/Lima")).date()):
                        record.invoice_payment_term_type = "Credito"
                else:
                    record.invoice_payment_term_type = "Contado"

    residual_credit_paymentterm = fields.Monetary(
        "Saldo restante de plazos de pago a crédito", compute="_compute_residual_credit_paymentterm")

    @api.depends("paymentterm_line",
                 "paymentterm_line.amount",
                 "amount_total",
                 "amount_retention",
                 "detraction_amount")
    def _compute_residual_credit_paymentterm(self):
        for move in self:
            move.residual_credit_paymentterm = round(
                self.amount_total - self.detraction_amount - self.amount_retention - sum(move.paymentterm_line.mapped("amount")), 2)

    def check_paymenttermn_lines(self):
        for record in self:
            if record.type in ['out_invoice', 'in_invoice']:
                if record.invoice_payment_term_id:
                    if record.invoice_payment_term_type == "Credito":
                        amount_total = round(sum(record.paymentterm_line.mapped(
                            "amount")) + record.detraction_amount + record.amount_retention, 2)
                        if amount_total != round(record.amount_total, 2):
                            raise UserError(
                                "El monto total de los plazos de pago debe ser igual al total de la factura.")
                        if record.invoice_date:
                            if min(record.paymentterm_line.mapped("date_due")) <= record.invoice_date:
                                raise UserError(
                                    "La fecha de vencimiento de la cuota debe ser mayor a la fecha de emisión del comprobante")
                        else:
                            if min(record.paymentterm_line.mapped("date_due")) <= datetime.now(tz=timezone("America/Lima")).date():
                                raise UserError(
                                    "La fecha de vencimiento de la cuota debe ser mayor a la fecha de emisión del comprobante")

    @api.onchange("type_detraction")
    def change_type_detraction(self):
        for record in self:
            record.detraction_rate = record.type_detraction.rate
            record.detraction_code = record.type_detraction.code

    @api.onchange("account_journal_national_bank")
    def change_account_journal_national_bank(self):
        for record in self:
            record.bank_account_number_national = record.account_journal_national_bank.acc_number

    json_comprobante = fields.Text(string="JSON Comprobante", copy=False)
    json_respuesta = fields.Text(string="JSON Respuesta", copy=False)
    # cdr_sunat = fields.Binary(string="CDR", copy=False)
    digest_value = fields.Char(string="Digest Value", copy=False,
                               default="*", related="current_log_status_id.digest_value")

    status_envio = fields.Boolean(
        string="Estado del envio del documento",
        default=False,
        copy=False
    )
    status_baja = fields.Boolean(
        string="Estado de la baja del documento",
        default=False,
        copy=False
    )
    # variables para notas de venta
    sustento_nota = fields.Text(
        string="Sustento de nota",
        readonly=True,
        states={
            'draft': [
                ('readonly', False)
            ]
        },
        copy=False)

    tipo_cambio_fecha_factura = fields.Float(
        string="Tipo de cambio a la fecha de factura",
        default=1.0)

    tipo_operacion = fields.Selection(selection=[(
        "01", "Venta Interna"), ("02", "Exportación")], default="01", required=True, copy=False)

    invoice_type_code_catalog_51 = fields.Many2one("sunat.catalog.51",
                                                   string="Tipo de Operación",
                                                   default=lambda self: self.env.ref("gestionit_pe_fe.catalog_51_0101", raise_if_not_found=False))

    apply_same_discount_on_all_lines = fields.Boolean("Aplicar el mismo descuento en todas las líneas?", states={
                                                      'draft': [('readonly', False)]}, readonly=True)
    discount_on_all_lines = fields.Float(
        "Descuento (%)", states={'draft': [('readonly', False)]}, readonly=True)

    def action_apply_same_discount_on_all_lines(self):
        self.invoice_line_ids = [(1, line.id, {"discount": self.discount_on_all_lines if all([(True if ta not in ["31", "32", "33", "34", "35", "36", "37"] else False)
                                                                                              for ta in line.tax_ids.mapped("tax_group_id.tipo_afectacion")]) else 0})
                                 for line in self.invoice_line_ids
                                 ]

    apply_global_discount = fields.Boolean("Aplicar descuento global", default=False, states={
                                           'draft': [('readonly', False)]}, readonly=True)
    descuento_global = fields.Float(
        string="Descuento Global (%)",
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=0.0)

    apply_retention = fields.Boolean("Aplicar Retención", default=False, states={
                                     'draft': [('readonly', False)]}, readonly=True)

    retention_rate = fields.Float("% de Retención", default=0, states={
                                  'draft': [('readonly', False)]}, readonly=True)

    @api.onchange('line_ids',
                  'descuento_global',
                  'apply_retention',
                  'apply_global_discount',
                  'retention_rate',
                  'invoice_payment_term_id',
                  'invoice_date_due',
                  'invoice_cash_rounding_id',
                  'invoice_vendor_bill_id')
    def _onchange_recompute_dynamic_lines(self):
        super(AccountMove, self)._onchange_recompute_dynamic_lines()
        for record in self:
            line_ids = []

            # Descuento Global
            if not record.apply_global_discount:
                record.descuento_global = 0

            line_discount_global_ids = record.line_ids.filtered(
                lambda r: r.type_charge_or_discount_code == "02")
            if len(line_discount_global_ids) > 0:
                # line_ids += [(2, ldg.id) for ldg in line_discount_global_ids]
                # record.line_ids = line_ids
                record.line_ids = [(2, ldg.id)
                                   for ldg in line_discount_global_ids]

            if abs(record.descuento_global) > 0:
                record.descuento_global = abs(record.descuento_global)
                product = record.env.company.default_product_global_discount_id
                company = record.company_id
                if not product:
                    raise UserError(
                        "Debes configurar el producto de descuento global en la sección de configuración de ventas")

                tax_ids = record.line_ids.filtered(
                    lambda r: r.type_charge_or_discount_code != "02").mapped("tax_ids")

                for tax in tax_ids.filtered(lambda r: r.tax_group_id.tipo_afectacion in ["10", "20", "30", "40"]):
                    if tax.price_include:
                        base_amount = abs(sum(record.line_ids.filtered(
                            lambda r: r.type_charge_or_discount_code != "02" and tax._origin.id in r.tax_ids.ids).mapped('price_total')))
                        price_unit = (base_amount)*record.descuento_global/100
                    else:
                        base_amount = abs(sum(record.line_ids.filtered(
                            lambda r: r.type_charge_or_discount_code != "02" and tax._origin.id in r.tax_ids.ids).mapped('price_subtotal')))
                        price_unit = (base_amount)*record.descuento_global/100
                    values = {
                        "sequence": 10000,
                        "product_id": product.id,
                        "tax_ids": [(6, 0, [tax._origin.id])],
                        "name": product.name,
                        "product_uom_id": product.uom_id.id,
                        "price_unit": -round(price_unit, 6),
                        "quantity": 1,
                        "currency_id": False if self.currency_id == company.currency_id else self.currency_id.id,
                        "company_currency_id": company.currency_id.id,
                        "account_id": product.product_tmpl_id.property_account_income_id.id,
                        "company_id": company.id,
                        "is_charge_or_discount": True,
                        "recompute_tax_line": True,
                        "type_charge_or_discount_code": "02",
                        "exclude_from_invoice_tab": True
                    }
                    line_ids.append((0, 0, values))

            if len(line_ids) > 0:
                if type(self.id) == int:
                    record.write({"invoice_line_ids": line_ids})
                else:
                    record.invoice_line_ids = line_ids
                    record.invoice_line_ids._onchange_price_subtotal()
                    record.line_ids._onchange_price_subtotal()
                    record._recompute_dynamic_lines(recompute_all_taxes=True)
            # Fin Descuento Global

            # Retención
            # line_ids = []

            if not record.apply_retention:
                record.retention_rate = 0
            elif record.retention_rate == 0:
                record.retention_rate = 3

            # line_retention_id = record.line_ids.filtered(lambda r:r.type_charge_or_discount_code == "62")
            # if len(line_retention_id) == 1:
            #     record.line_ids = [(2, lr.id) for lr in line_retention_id]

            # if abs(record.retention_rate) > 0:
            #     record.retention_rate = abs(record.retention_rate)
            #     account_account_retention_id = record.env.company.default_account_account_retention_id
            #     company = record.company_id
            #     if not account_account_retention_id:
            #         raise UserError("Debes configurar la cuenta de retención en la sección de ajustes de facturación electrónica")

            #     base_amount = abs(sum(record.line_ids.filtered(lambda r: r.type_charge_or_discount_code != '62' and (len(r.tax_ids) > 0 or r._origin.tax_ids) ).mapped('price_total')))

            #     values = {
            #         "sequence":10000,
            #         "tax_ids": [],
            #         "name": account_account_retention_id.name,
            #         "price_unit": -round(abs(base_amount*record.retention_rate/100), 6),
            #         "quantity": 1,
            #         "currency_id": False if self.currency_id == company.currency_id else self.currency_id.id,
            #         "company_currency_id":company.currency_id.id,
            #         "account_id": account_account_retention_id.id,
            #         "company_id": company.id,
            #         "is_charge_or_discount": True,
            #         "recompute_tax_line": True,
            #         "type_charge_or_discount_code": "62",
            #         "exclude_from_invoice_tab": True
            #     }
            #     line_ids.append((0, 0, values))

            # Fin Retención

            # if len(line_ids) > 0:
            #     if type(self.id) == int:
            #         record.write({"invoice_line_ids": line_ids})
            #     else:
            #         record.invoice_line_ids = line_ids
            #         record.invoice_line_ids._onchange_price_subtotal()
            #         record.line_ids._onchange_price_subtotal()
            #         record._recompute_dynamic_lines(recompute_all_taxes=True)

    total_venta_gravado = fields.Monetary(
        string="Gravado",
        default=0.0,
        compute="_compute_amount")
    total_venta_inafecto = fields.Monetary(
        string="Inafecto",
        default=0.0,
        compute="_compute_amount")
    total_venta_exonerada = fields.Monetary(
        string="Exonerado",
        default=0.0,
        compute="_compute_amount")
    total_venta_gratuito = fields.Monetary(
        string="Gratuita",
        default=0.0,
        compute="_compute_amount")

    total_venta_exportacion = fields.Monetary(
        string="Exportación",
        default=0.0,
        compute="_compute_amount")

    amount_igv = fields.Monetary(
        string="IGV",
        default=0.0,
        compute="_compute_amount")

    total_descuentos = fields.Monetary(
        string="Total Descuentos",
        default=0.0,
        compute="_compute_amount")
    total_descuento_global = fields.Monetary(
        string="Total Descuentos Global",
        default=0.0,
        compute="_compute_amount")

    amount_retention = fields.Monetary(
        string="Retención", default=0, compute="_compute_amount")

    # monto_en_letras = fields.Char("Monto en letras",compute=_compute_monto_en_letras)
    tiene_guia_remision = fields.Boolean(
        "Tienes guía de Remisión", default=False, copy=False)
    invoice_picking_id = fields.Many2one(
        "stock.picking", string="Documento de Envío", copy=False)
    stock_picking_id = fields.Many2one(
        "stock.picking", string="Documento de Envío", copy=False)
    numero_guia = fields.Char(
        "Número de Guía", related="invoice_picking_id.numero_guia", copy=False)
    numero_guia_remision = fields.Char(
        "Número de Guía de Remisión", copy=False)
    guia_remision_ids = fields.Many2many(
        "gestionit.guia_remision", string="Guía de Remisión")
    guia_remision_count = fields.Integer(
        "Cantidad de GRE", compute="_compute_guia_remision_count")

    ######################## FLAG DE ITEMS GRATUITOS ########################
    exist_items_gratuito = fields.Boolean(string="Operacion Gratuita",copy=False,
        compute="compute_exist_items_gratuito",default=False,store=True)

    @api.depends(
        'line_ids',
        'line_ids.tax_ids',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'descuento_global',
        'apply_global_discount',
        'retention_rate',
        'apply_retention')
    def compute_exist_items_gratuito(self):
        for move in self:
            move.exist_items_gratuito = False

            for line in move.line_ids:
                if len([1 for line_tax in line.tax_ids \
                    if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36", "37"]]):
                    move.exist_items_gratuito = True

    ###########################################################################
    def _compute_guia_remision_count(self):
        for record in self:
            record.guia_remision_count = len(record.guia_remision_ids)

    # Forzar eliminación de un comprobante
    def unlink(self):
        cancelled_moves = self.filtered(lambda m: m.state == "cancel")
        super(AccountMove, cancelled_moves.with_context(
            force_delete=True)).unlink()
        return super(AccountMove, self - cancelled_moves).unlink()

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'descuento_global',
        'apply_global_discount',
        'retention_rate',
        'apply_retention')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()

        for move in self:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab or line.is_charge_or_discount:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1

            move.amount_untaxed = sign * \
                (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            move.amount_tax = sign * \
                (total_tax_currency if len(currencies) == 1 else total_tax)
            move.amount_total = sign * \
                (total_currency if len(currencies) == 1 else total)
            move.amount_residual = -sign * \
                (total_residual_currency if len(currencies) == 1 else total_residual)

            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(
                total) if move.type == 'entry' else -total
            move.amount_residual_signed = total_residual

            # currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
            # is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual


        for move in self:
            move.total_venta_gravado = sum([
                line.price_subtotal
                for line in move.line_ids
                if len([line.price_subtotal for line_tax in line.tax_ids
                        if line_tax.tax_group_id.tipo_afectacion in ["10"]])
            ])
            # *(1-move.descuento_global/100.0)

            move.total_venta_inafecto = sum([
                line.price_subtotal
                for line in move.line_ids
                if len(
                    [line.price_subtotal for line_tax in line.tax_ids
                     if line_tax.tax_group_id.tipo_afectacion in ["30"]])
            ])
            # *(1-move.descuento_global/100.0)

            move.total_venta_exonerada = sum([
                line.price_subtotal
                for line in move.line_ids
                if len(
                    [line.price_subtotal for line_tax in line.tax_ids
                     if line_tax.tax_group_id.tipo_afectacion in ["20"]])
            ])
            # *(1-move.descuento_global/100.0)
            ##### CALCULO DE IMPUESTO SEGÚN METODO REDONDEO DE LA CONFIG:
            if move.company_id.tax_calculation_rounding_method =='round_per_line':
                move.amount_igv = sum([
                    line.price_total - line.price_subtotal
                    for line in move.line_ids
                    if len([line.price_subtotal for line_tax in line.tax_ids
                            if line_tax.tax_group_id.tipo_afectacion in ["10"]])
                ])

            elif move.company_id.tax_calculation_rounding_method =='round_globally':
            #  *(1-move.descuento_global/100.0)
                move.amount_igv = sum([
                    line.price_subtotal*[line_tax.amount for line_tax in line.tax_ids
                            if line_tax.tax_group_id.tipo_afectacion in ["10"]][0]*0.01

                    for line in move.line_ids
                    if len([line.price_subtotal for line_tax in line.tax_ids
                            if line_tax.tax_group_id.tipo_afectacion in ["10"]])
                ])

            move.total_descuento_global = (move.total_venta_gravado + move.total_venta_exonerada +
                                           move.total_venta_inafecto)*(move.descuento_global/100.0)/(1-move.descuento_global/100.0)

            move.total_venta_gratuito = sum([
                line.price_unit*line.quantity
                for line in move.line_ids
                if len([1 for line_tax in line.tax_ids
                        if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36", "37"]])
            ])

            move.total_venta_exportacion = sum([
                line.price_unit*line.quantity
                for line in move.line_ids
                if len([1 for line_tax in line.tax_ids
                        if line_tax.tax_group_id.tipo_afectacion in ["40"]])
            ])

            move.total_descuentos = sum([
                ((line.price_subtotal / (1-line.discount/100.0))
                 * line.discount/100.0) + line.descuento_unitario
                for line in move.line_ids
                if line.discount < 100
            ]) + move.total_descuento_global

            move.amount_retention = (move.total_venta_gravado + move.total_venta_exonerada +
                                     move.total_venta_inafecto + move.amount_igv)*move.retention_rate/100

            # move.amount_untaxed = move.total_venta_gravado + \
            #         move.total_venta_exonerada + \
            #         move.total_venta_inafecto

            # move.amount_total = move.amount_untaxed + \
            #                     move.amount_igv

            # move.amount_residual = - move.amount_total

    mostrar_button_draft = fields.Boolean(string="Mostrar Botón Draft",
        compute="compute_mostrar_button_draft")

    mostrar_button_cancel_anulados = fields.Boolean(string="Mostrar Botón Cancelar Anulados",
        compute="compute_mostrar_button_cancel_anulados")


    @api.depends('type','estado_comprobante_electronico','estado_emision')
    def compute_mostrar_button_draft(self):
        for move in self:
            move.mostrar_button_draft=True
            if move.type in ['out_invoice','out_refund'] and \
                move.estado_emision in ["E", "A", "O"] or move.estado_comprobante_electronico in ["1_ACEPTADO"]:
                move.mostrar_button_draft = False



    @api.depends('type','estado_comprobante_electronico','estado_emision')
    def compute_mostrar_button_cancel_anulados(self):
        for move in self:

            current_user = self.env.user
            move.mostrar_button_cancel_anulados=False

            if move.type in ['out_invoice','out_refund'] and \
                ((move.estado_emision in ["E", "A", "O"] and \
                move.estado_comprobante_electronico in ["2_ANULADO"]) or move.estado_comprobante_electronico in ["2_ANULADO"]) and \
                current_user.has_group('gestionit_pe_fe.group_user_cancelar_anulados'):

                move.mostrar_button_cancel_anulados = True
            else:
                move.mostrar_button_cancel_anulados = False



    ####### FUNCIONALIDAD PARA CANCELACIÓN MASIVA !! ##########
    def button_cancel_anulados_sunat(self):
        current_user = self.env.user
        _logger.info('\n\nCANCELAR ANULADOS !!!\n\n')

        if current_user.has_group('gestionit_pe_fe.group_user_cancelar_anulados'):

            for line in self:
                if (line.estado_emision in ["E", "A", "O"] and line.estado_comprobante_electronico in ["2_ANULADO"]) or \
                    (line.estado_comprobante_electronico in ["2_ANULADO"]):

                    line.button_draft()
                    line.button_cancel()

                elif line.estado_emision in ["E", "A", "O"] and line.estado_comprobante_electronico in ["1_ACEPTADO"]:

                    raise UserError(
                        "Este comprobante ya fue enviado a SUNAT y no puede ser editado.")

    ###########################################################


    
    def button_draft(self):
        super(AccountMove, self).button_draft()

        current_user = self.env.user

        if not current_user.has_group('gestionit_pe_fe.group_user_cancelar_anulados'):
            for move in self:

                if move.estado_emision in ["E", "A", "O"] or move.estado_comprobante_electronico in ["1_ACEPTADO", "2_ANULADO"]:
                    raise UserError(
                        "Este comprobante ya fue enviado a SUNAT y no puede ser editado.")
                else:
                    if move.current_log_status_id:
                        move.current_log_status_id.action_set_last_log_unlink()
        else:
            for move in self:

                if move.estado_emision in ["E", "A", "O"] and move.estado_comprobante_electronico in ["1_ACEPTADO"]:
                    raise UserError(
                        "Este comprobante ya fue enviado a SUNAT y fue ACEPTADO, por lo que no puede ser editado.")
                else:
                    if move.current_log_status_id:
                        move.current_log_status_id.action_set_last_log_unlink()




    def post(self):
        # Validar journal
        for move in self:
            move.check_paymenttermn_lines()
            # _logger.info(move.name)
            if move.journal_id.invoice_type_code_id not in ['01', '03', '07', '08', '09']:
                return super(AccountMove, move).post()
            else:
                if move.type in ["in_invoice", "in_refund"]:
                    if move.inv_supplier_ref:
                        move._validate_inv_supplier_ref()
                    else:
                        raise UserError(
                            "El número de comprobante del proveedor es obligatorio")
                    return super(AccountMove, move).post()

                if not move.journal_id.electronic_invoice:
                    return super(AccountMove, move).post()
                    # obj = super(AccountMove, self).post()
                    # return obj
                else:
                    # Validaciones cuando el comprobante es factura
                    msg_error = []
                    msg_error += move.validar_datos_compania()
                    msg_error += move.validar_diario()

                    ######################## GROUP_USER PARA EMISIÓN FUERA DE PLAZO #######
                    current_user = self.env.user
                    
                    if not current_user.has_group('gestionit_pe_fe.group_user_sunat_send_out_date'):
                        msg_error += move.validar_fecha_emision()
                    ###############################

                    msg_error += move.validar_lineas()
                    msg_error += move.validacion_exportacion()

                    if move.journal_id.invoice_type_code_id == "01":
                        msg_error += move.validacion_factura()
                        if len(msg_error) > 0:
                            msg = "\n\n".join(msg_error)
                            raise UserError(msg)

                    if move.journal_id.invoice_type_code_id == "03":
                        msg_error += move.validacion_boleta()
                        if len(msg_error) > 0:
                            msg = "\n\n".join(msg_error)
                            raise UserError(msg)

                    if move.journal_id.invoice_type_code_id == "07":
                        msg_error += move.validacion_nota_credito()
                        if len(msg_error) > 0:
                            msg = "\n\n".join(msg_error)
                            raise UserError(msg)

                    # if move.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != "6" and move.journal_id.invoice_type_code_id == "01":
                    #     raise UserError(
                    #         "Tipo de documento del receptor no valido")

                    super(AccountMove, move).post()

                    move.action_generate_and_signed_xml()

                    # if move.journal_id.invoice_type_code_id == "03" or move.journal_id.tipo_comprobante_a_rectificar == "03":
                    #     return obj

                    if not move.journal_id.send_async:
                        move.action_send_invoice()

                    # return obj

    def action_generate_and_signed_xml(self):
        if not self.current_log_status_id:
            vals = generate_and_signed_xml(self)
            account_log_status = self.env["account.log.status"].create(vals)
            account_log_status.action_set_last_log()

    def action_send_invoice(self):
        if not (self.current_log_status_id and (self.journal_id.invoice_type_code_id == "01" or self.journal_id.tipo_comprobante_a_rectificar == "01")):
            self.action_generate_and_signed_xml()

        if self.current_log_status_id.status in ["P", "N",False]:
            try:
                vals = send_doc_xml(self)
                self.current_log_status_id.write(vals)
            except Exception as e:
                return vals

    inv_supplier_ref = fields.Char("Número de comprobante")

    # @api.model
    def _validate_inv_supplier_ref(self):
        if self.inv_supplier_ref:
            if not (re.match("^F\w{3}[-]\d{1,8}$", self.inv_supplier_ref) or
                    re.match("^B\w{3}[-]\d{1,8}$", self.inv_supplier_ref) or
                    re.match("^E\w{3}[-]\d{1,8}$", self.inv_supplier_ref)):
                raise UserError(
                    "La referencia debe tener el formato XXXX-########")
        else:
            raise UserError("Debe colocar el número de comprobante.")

    def validar_datos_compania(self):
        errors = []
        if not self.company_id.partner_id.vat:
            errors.append(
                "* No se tiene configurado el RUC de la empresa emisora")

        if not self.company_id.partner_id.l10n_latam_identification_type_id:
            errors.append(
                "* No se tiene configurado el tipo de documento de la empresa emisora")
        elif self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != '6':
            errors.append(
                "* El Tipo de Documento de la empresa emisora debe ser RUC")

        if not self.company_id.partner_id.ubigeo:
            errors.append(
                "* No se encuentra configurado el Ubigeo de la empresa emisora.")

        if not self.company_id.partner_id.street:
            errors.append(
                "* No se encuentra configurado la dirección de la empresa emisora.")

        if not self.company_id.partner_id.name:
            errors.append(
                "* No se encuentra configurado la Razón Social de la empresa emisora.")

        return errors

    def validar_diario(self):
        errors = []
        if self.journal_id.tipo_envio != self.company_id.tipo_envio:
            errors.append(
                "* El tipo de envío configurado en la compañía debe coincidir con el tipo de envío del Diario que ha seleccionado.")
        return errors

    def validar_fecha_emision(self):
        errors = []
        now = datetime.now(tz=timezone("America/Lima")).date()

        if not self.invoice_date:
            self.invoice_date = now
        # now = datetime.strptime(fields.Date.today(), "%Y-%m-%d")

        # if now < datetime.strptime(self.invoice_date, "%Y-%m-%d"):
        if now < self.invoice_date:
            errors.append(
                "* La fecha de la emisión del comprobante debe ser menor o igual a la fecha del día de hoy.")
        elif abs(self.invoice_date - now).days > 3:
            # elif abs(datetime.strptime(self.invoice_date, "%Y-%m-%d") - now).days > 3:
            errors.append(
                "* La fecha de Emisión debe tener como máximo una antiguedad de 3 días.")

        return errors

    def validar_lineas(self):
        errors = []
        for line in self.invoice_line_ids.filtered(lambda r: not r.display_type):
            if line.name:
                if len(line.name) < 4 and len(line.name) > 250:
                    errors.append(
                        "* La cantidad de carácteres de la descripción del producto debe ser mayor a 4 y menor a 250")
                    break
            else:
                errors.append(
                    "* La descripción del detalle de los productos esta vacío.")
                break

            if not line.product_uom_id.code:
                errors.append(
                    "* La Unidad de medida del detalle de las líneas del comprobante esta vacío.")
            else:
                if line.product_uom_id.code not in codigo_unidades_de_medida:
                    errors.append(
                        "* El código de la unidad de medida del detalle de las líneas del comprobante es invalido.")
                    break

            if line.quantity <= 0:
                errors.append(
                    "* La cantidad del detalle de las líneas del comprobante es mayor a 0.")
                break

            if len(line.tax_ids) == 0:
                errors.append(
                    "* Las líneas del detalle del comprobante deben poseer al menos un impuesto.")
                break
            else:
                for line_tax in line.tax_ids:
                    if not line_tax.tax_group_id.codigo == "7152":
                        if not line_tax.tax_group_id.tipo_afectacion:
                            errors.append(
                                "* El impuesto seleccionado en las líneas del comprobante no posee tipo de afectación al IGV.")
                            break
                        else:
                            if line_tax.tax_group_id.tipo_afectacion not in codigos_tipo_afectacion_igv:
                                errors.append(
                                    "* El código de tipo de afectación ingresado no es Válido. Consulte con su Administrador del Sistema.")
                                break

            if line.discount == 100:
                errors.append(
                    "El descuento no puede ser del 100%. Si el producto es gratuito, use el impuesto GRATUITO.")

            if line.discount < 0:
                errors.append(
                    "Error: El descuento no puede ser menor a cero. Error en el producto {}".format(line.name))

            if line.discount > 0 and len(line.tax_ids.filtered(lambda r: r.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"])) > 0:
                errors.append(
                    "Error: Las líneas gratuitas no deben tener descuento. Error en el producto {}".format(line.name))

            # if line.price_unit == 0 and len([1 for tax in line.tax_ids if tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"]]) > 0:
            # if line.price_unit == 0 and line.tax_ids[0].tax_group_id.tipo_afectacion == "31":
            if line.price_unit == 0:
                errors.append(
                    "El precio unitario de los productos debe ser siempre mayor a 0. Revise el producto {} y cambie el precio a un valor mayor a 0.".format(line.name))
                break

            # if line.price_unit == 0 and len([1 for tax in line.invoice_line_tax_ids if tax.tipo_afectacion_igv.code in ["31","32","33","34","35","36"]]) == 0:

        return errors

    def validacion_factura(self):
        ### AMOUNT_TOTAL <= 700
        errors = []
        if self.invoice_type_code_catalog_51.code in ["0101"]:
            if self.amount_total <=700.00:

                if self.partner_id.l10n_latam_identification_type_id and self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code not in ["0","1","4","6","7"]:
                    errors.append(
                        "* No es un tipo de Documento Válido para el Comprobante.")

                if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code=="06" and self.partner_id.vat:
                    errors.append(
                        "* El cliente selecionado no tiene RUC, esto es necesario para facturas")

                elif len(self.partner_id.vat) != 11:
                    errors.append(
                        "* El RUC del cliente selecionado debe tener 11 dígitos")

                for line in self.invoice_line_ids.filtered(lambda r: not r.display_type):
                    if len(line.tax_ids) == 0:
                        errors.append(
                            "* El Producto debe tener al menos un tipo de impuesto Asociado")
                    for tax in line.tax_ids:
                        if not tax.tax_group_id.tipo_afectacion:
                            errors.append(
                                "* El Tipo de Afectacion al IGV no esta configurado para el Impuesto %s del item %s" % (tax.name, line.name))
                    # Falta Validar los tipos de Afectación al IGV
                    if not line.product_uom_id.code:
                        errors.append(
                            "* La Unidad de Medida seleccionada para el item %s no tiene código" % (line.name))
            else:

                if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != "6":
                    errors.append(
                        "* El cliente seleccionado debe tener como tipo de documento el RUC, esto es necesario para facturas.")
                    
            if not self.partner_id.vat:
                errors.append(
                    "* El cliente selecionado no tiene RUC, esto es necesario para facturas")

            elif len(self.partner_id.vat) != 11:
                errors.append(
                    "* El RUC del cliente selecionado debe tener 11 dígitos")

            for line in self.invoice_line_ids.filtered(lambda r: not r.display_type):
                if len(line.tax_ids) == 0:
                    errors.append(
                        "* El Producto debe tener al menos un tipo de impuesto Asociado")
                for tax in line.tax_ids:
                    if not tax.tax_group_id.tipo_afectacion:
                        errors.append(
                            "* El Tipo de Afectacion al IGV no esta configurado para el Impuesto %s del item %s" % (tax.name, line.name))
                # Falta Validar los tipos de Afectación al IGV
                if not line.product_uom_id.code:
                    errors.append(
                        "* La Unidad de Medida seleccionada para el item %s no tiene código" % (line.name))

        if self.invoice_type_code_catalog_51.code not in ["0200","0201","0202","0203","0204","0205","0206","0207","0208","0101"]:
            if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != "6":
                errors.append(
                    "* El cliente seleccionado debe tener como tipo de documento el RUC, esto es necesario para facturas.")
                    
            if not self.partner_id.vat:
                errors.append(
                    "* El cliente selecionado no tiene RUC, esto es necesario para facturas")

            elif len(self.partner_id.vat) != 11:
                errors.append(
                    "* El RUC del cliente selecionado debe tener 11 dígitos")

            for line in self.invoice_line_ids.filtered(lambda r: not r.display_type):
                if len(line.tax_ids) == 0:
                    errors.append(
                        "* El Producto debe tener al menos un tipo de impuesto Asociado")
                for tax in line.tax_ids:
                    if not tax.tax_group_id.tipo_afectacion:
                        errors.append(
                            "* El Tipo de Afectacion al IGV no esta configurado para el Impuesto %s del item %s" % (tax.name, line.name))
                # Falta Validar los tipos de Afectación al IGV
                if not line.product_uom_id.code:
                    errors.append(
                        "* La Unidad de Medida seleccionada para el item %s no tiene código" % (line.name))

        return errors

    def validacion_boleta(self):
        errors = []
        if self.invoice_type_code_catalog_51.code not in ["0200","0201","0202","0203","0204","0205","0206","0207","0208"]:
            if abs(self.amount_residual_signed) >= 700 and self.journal_id.invoice_type_code_id == '03':
                if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code not in ['1','4','6','7']:
                    errors.append("* El tipo de documento de identidad del cliente debe ser DNI/RUC/CE. Obligatorio para Boletas de venta mayores a S/ 700.")
                else:
                    if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code == '1':
                        if not patron_dni.match(self.partner_id.vat or ""):
                            errors.append("* El Documento de identidad (DNI/CE) del cliente no tiene un formato válido. Obligatorio para Boletas de venta mayores a S/ 700.")
                    elif self.partner_id.vat in ["0",False,""]:
                        errors.append("* El Documento de identidad (DNI/CE) del cliente no tiene un formato válido. Obligatorio para Boletas de venta mayores a S/ 700.")
        return errors


    def is_alphanum_or_empty(self,cad):
        
        if cad.isalnum() or cad == '':
            return True
        else:
            return False



    def validacion_exportacion(self):

        errors = []
        
        if self.invoice_type_code_catalog_51.code in ["0200","0201","0202","0203","0204","0205","0206","0207","0208"]:

            if not ( self.is_alphanum_or_empty(self.partner_id.vat or '') and self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code == "0"):
                errors.append("El cliente debe tener tipo de documento 'DOC.TRI.SIN.RUC' y número de documento alfanumérico")

            if "40" not in self.invoice_line_ids.mapped("tax_ids.tax_group_id.tipo_afectacion"):
                errors.append("El comprobante de exportación debe tener todas sus líneas con el impuesto de exportación.")
            for prod in self.invoice_line_ids.mapped("product_id"):
                if not bool(prod.sunat_code) or not bool(re.compile("\d{8}$").match(prod.sunat_code)):
                    errors.append("El código sunat del producto {} no es válido.".format(prod.sunat_code))
        return errors

    def validacion_nota_credito(self):
        errors = []
        if self.descuento_global != 0 or self.apply_global_discount:
            errors.append(
                "* No es posible aplicar un descuento global a una Nota de crédito. Esta opción solo esta disponible para Facturas y Boletas")
        return errors

    @api.constrains("has_detraction", "invoice_type_code_catalog_51")
    def check_detraction(self):
        for record in self:
            if not(record.has_detraction and record.invoice_type_code_catalog_51.code == "1001"):
                if record.has_detraction:
                    raise UserError(
                        "Si la factura tiene detracción, entonces el tipo de operación es 'Operación sujeta a detracción'")
                if record.invoice_type_code_catalog_51.code == "1001":
                    raise UserError(
                        "Si el tipo de operación es 'Operación sujeta a detracción' entonces la debe activar el campo 'Detracción?'.")

    def generar_nota_debito(self):
        self.ensure_one()
        new_moves = self.env['account.move']
        # copy sale/purchase links
        for move in self.env['account.debit.note'].move_ids.with_context(include_business_fields=True):
            default_values = self.env['account.debit.note']._prepare_default_values(
                move)
            # Context key is used for l10n_latam_invoice_document for ar/cl/pe
            new_move = move.with_context(
                internal_type='debit_note').copy(default=default_values)
            move_msg = _(
                "This debit note was created from:") + " <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>" % (
                move.id, move.name)
            new_move.message_post(body=move_msg)
            new_moves |= new_move
        # log.info("MOVIEMIENTOS DÉBITO")
        # log.info(new_moves)
        action = {
            'name': _('Debit Notes'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(new_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': new_moves.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', new_moves.ids)],
            })
        return action

    def generar_nota_credito(self):
        self.ensure_one()
        moves = self.env['account.move'].browse(self.id)

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(
                self.env['account.move.reversal']._prepare_default_reversal(move))

        batches = [
            # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], True],
            [self.env['account.move'], [], False],  # Others.
        ]
        refund_method = 'refund'
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and refund_method in (
                'cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            if is_cancel_needed is True:
                pass
            else:
                new_moves = moves._reverse_moves(
                    default_values_list, cancel=is_cancel_needed)

                if refund_method == 'modify':
                    moves_vals_list = []
                    for move in moves.with_context(include_business_fields=True):
                        moves_vals_list.append(move.copy_data(
                            {'date': move.date})[0])
                    new_moves = self.self.env['account.move'].create(
                        moves_vals_list)

                moves_to_redirect |= new_moves

        moves_to_redirect.invoice_type_code = '07'

        for j in moves_to_redirect.journal_ids:
            if j.invoice_type_code_id == '07':
                moves_to_redirect.journal_id = j.id
        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
        return action

    # def _reverse_moves(self, default_values_list=None, cancel=False):
    #     ''' Reverse a recordset of account.move.
    #     If cancel parameter is true, the reconcilable or liquidity lines
    #     of each original move will be reconciled with its reverse's.

    #     :param default_values_list: A list of default values to consider per move.
    #                                 ('type' & 'reversed_entry_id' are computed in the method).
    #     :return:                    An account.move recordset, reverse of the current self.
    #     '''

    #     if not default_values_list:
    #         default_values_list = [{} for move in self]

    #     if cancel:
    #         lines = self.mapped('line_ids')
    #         # Avoid maximum recursion depth.
    #         if lines:
    #             lines.remove_move_reconcile()

    #     # p_obj.with_context(filter_order_ids=order_ids).filtered(lambda r: r.origin_id.id IN r._context['filter_order_ids'])

    #     reverse_type_map = {
    #         'entry': 'entry',
    #         'out_invoice': 'out_refund',
    #         'out_refund': 'entry',
    #         'in_invoice': 'in_refund',
    #         'in_refund': 'entry',
    #         'out_receipt': 'entry',
    #         'in_receipt': 'entry',
    #     }

    #     move_vals_list = []
    #     for move, default_values in zip(self, default_values_list):
    #         default_values.update({
    #             'type': reverse_type_map[move.type],
    #             'reversed_entry_id': move.id,
    #         })
    #         move_vals_list.append(move.with_context(
    #             move_reverse_cancel=cancel)._reverse_move_vals(default_values, cancel=cancel))

    #     reverse_moves = self.env['account.move'].create(move_vals_list)
    #     for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False)):
    #         # Update amount_currency if the date has changed.
    #         if move.date != reverse_move.date:
    #             for line in reverse_move.line_ids:
    #                 if line.currency_id:
    #                     line._onchange_currency()

    #         # reverse_move.invoice_line_ids = [(6, 0, reverse_move.invoice_line_ids.filtered(
    #         #     lambda r: r.tax_ids[0].tax_group_id.tipo_afectacion == '10').mapped('id'))]

    #         reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
    #     reverse_moves._check_balanced()

    #     # Reconcile moves together to cancel the previous one.
    #     if cancel:
    #         reverse_moves.with_context(move_reverse_cancel=cancel).post()
    #         for move, reverse_move in zip(self, reverse_moves):
    #             accounts = move.mapped('line_ids.account_id') \
    #                 .filtered(lambda account: account.reconcile or account.internal_type == 'liquidity')
    #             for account in accounts:
    #                 (move.line_ids + reverse_move.line_ids)\
    #                     .filtered(lambda line: line.account_id == account and line.balance)\
    #                     .reconcile()

    #     return reverse_moves

    ##########################################################################################
    mostrar_btn_comunicacion_baja = fields.Boolean(string="Mostrar botón comunicación baja",
        compute="compute_mostrar_btn_comunicacion_baja")


    @api.depends('estado_comprobante_electronico','journal_id','journal_id.invoice_type_code_id',
        'reversed_entry_id','reversed_entry_id.estado_comprobante_electronico','reversed_entry_id.journal_id','type')
    def compute_mostrar_btn_comunicacion_baja(self):
        for rec in self:
            rec.mostrar_btn_comunicacion_baja=False
            if rec.type in ['out_invoice','out_refund'] and rec.state in ['posted']:
                #if rec.estado_comprobante_electronico == '1_ACEPTADO' and rec.journal_id \
                #    and rec.journal_id.invoice_type_code_id in ['01','03']:
                if rec.estado_comprobante_electronico == '1_ACEPTADO':
                    ### SE AÑADEN FACTURAS ##
                    
                    rec.mostrar_btn_comunicacion_baja = True

                elif rec.estado_comprobante_electronico == '1_ACEPTADO' and rec.journal_id \
                    and rec.journal_id.invoice_type_code_id in ['07','08'] and rec.reversed_entry_id and \
                    rec.reversed_entry_id.estado_comprobante_electronico == '1_ACEPTADO' and rec.reversed_entry_id.journal_id and \
                    rec.reversed_entry_id.journal_id.invoice_type_code_id in ['01','03']:
                    
                    rec.mostrar_btn_comunicacion_baja = True
    ##########################################################################################

    def btn_comunicacion_baja(self):

        tz = self.env.user.tz or "America/Lima"

        if self.estado_comprobante_electronico == "2_ANULADO":
            raise UserError("Este comprobante ha sido Anulado.")

        if len(self.credit_note_ids) > 0 or len(self.debit_note_ids) > 0:
            raise UserError(
                "Este comprobante no puede ser anulado debido a que tiene una o más notas que hacen referencia a este documento.")

        elif re.match("^F\w{3}-\d{1,8}$", self.name):
            if self.documento_baja_id:
                ref = self.env.ref(
                    "gestionit_pe_fe.view_comunicacion_baja_form")
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "account.comunicacion_baja",
                    "target": "self",
                    "res_id": self.documento_baja_id.id,
                    "view_mode": "form",
                    "view_id": ref.id,
                }
            else:
                ref = self.env.ref(
                    "gestionit_pe_fe.view_comunicacion_baja_form_simple")
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "account.comunicacion_baja",
                    "name": "Comunicación de baja o Anulación de comprobante",
                    "target": "new",
                    "view_id": ref.id,
                    "view_mode": "form",
                    "context": {
                        'default_invoice_ids': [self.id],
                        'default_company_id': self.company_id.id,
                        'default_invoice_type_code_id': self.journal_id.invoice_type_code_id,
                        'default_date_invoice': self.invoice_date,
                        'default_voided_date': datetime.now(tz=timezone(tz))
                    }
                }
        elif re.match("^B\w{3}-\d{1,8}$", self.name):
            if self.resumen_anulacion_id:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "account.summary",
                    "name": "Anulación de comprobante",
                    "view_mode": "form",
                    "target": "self",
                    "res_id": self.resumen_anulacion_id.id
                }
            else:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "account.summary.anulacion",
                    "name": "Anulación de Comprobante",
                    "view_id": self.env.ref("gestionit_pe_fe.view_popup_account_summary_anulacion").id,
                    "view_mode": "form",
                    "target": "new",
                    "context": {
                            "default_account_invoice_id": self.id,
                            "default_company_id": self.company_id.id
                    }
                }

    def action_context_default_guia_remision(self):
        return {
            "default_documento_asociado": "comprobante_pago",
            "default_fecha_emision": datetime.now(tz=timezone("America/Lima")).date(),
            "default_fecha_inicio_traslado": datetime.now(tz=timezone("America/Lima")).date(),
            # "default_modalidad_transporte":"02",
            "default_motivo_traslado": "01",
            "default_comprobante_pago_ids": [(6, 0, [self.id])],
            "default_destinatario_partner_id": self.partner_id.id,
            "default_company_partner_id": self.partner_id.id,
            "default_company_id": self.company_id.id
        }

    def action_open_guia_remision(self):
        action = {
            "type": "ir.actions.act_window",
            "res_model": "gestionit.guia_remision",
            "context": self.action_context_default_guia_remision(),
            "target": "self",
            "view_mode": "form"
        }
        return action

    def action_view_guia_remision(self):
        context = {
            "default_documento_asociado": "comprobante_pago",
            "default_fecha_emision": fields.Date.today(),
            "default_fecha_inicio_traslado": fields.Date.today(),
            "default_modalidad_transporte": "02",
            "default_motivo_traslado": "01",
            "default_comprobante_pago_ids": [(6, 0, [self.id])],
            "default_destinatario_partner_id": self.partner_id.id,
            "default_company_partner_id": self.partner_id.id
        }
        if len(self.guia_remision_ids) == 1:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "gestionit.guia_remision",
                "target": "self",
                "view_mode": "form",
                "res_id": self.guia_remision_ids.id,
                "context": context
            }
        elif len(self.guia_remision_ids) > 1:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "gestionit.guia_remision",
                "target": "self",
                "view_mode": "tree",
                "domain": [("id", "in", self.guia_remision_ids.ids)],
                "context": context
            }

        return action

    def cron_action_send_invoice(self):
        invoices = self.env["account.move"].search([["estado_emision", "in", ["P", "N","", False]],
                                                    ["name", "not in",
                                                        [False, "/"]],
                                                    ["state", "=", "posted"],
                                                    ["estado_comprobante_electronico", "in", [False, "-", "0_NO_EXISTE"]]], order="invoice_date asc")
        invoice_ids = invoices.filtered(lambda r: r.journal_id.invoice_type_code_id in [
                                        "01"] and re.match("^F\w{3}-\d{1,8}$", r.name))

        credit_and_debit_note_ids = invoices.filtered(lambda r: r.journal_id.invoice_type_code_id in ["07", "08"] and re.match("^F\w{3}-\d{1,8}$", r.name) and (
            r.reversed_entry_id.estado_comprobante_electronico == "1_ACEPTADO" or r.debit_origin_id.estado_comprobante_electronico == "1_ACEPTADO"))

        invoices = invoice_ids + credit_and_debit_note_ids

        now = datetime.now(tz=timezone("America/Lima"))
        for inv in invoices:
            if abs((inv.invoice_date - now.date()).days) <= 3:
                try:
                    inv.action_send_invoice()
                except Exception as e:
                    _logger.info(str(e))
            self.env.cr.commit()
        return True

    @api.model
    def cron_actualizacion_estado_emision_sunat(self):
        comprobantes = self.env["account.move"].sudo().search(
            [["estado_comprobante_electronico", "=", "1_ACEPTADO"]]).mapped("current_log_status_id")
        comprobantes.sudo().write({"status": "A"})
        return True

    def action_validez_comprobante(self):
        if self.current_log_status_id:
            self.current_log_status_id.action_request_status_invoice()

    @api.model
    def cron_action_validez_comprobante(self):
        today = fields.Date.today()
        invoices = self.env["account.move"].sudo().search([("journal_id.electronic_invoice", "=", True),
                                                           ("state", "in",
                                                            ["posted"]),
                                                           ("name", "not in",
                                                            [False, "/"]),
                                                           ("invoice_date",
                                                            "<=", today),
                                                           ("journal_id.electronic_invoice",
                                                            "=", True),
                                                           ("journal_id.invoice_type_code_id", "in", [
                                                            "01", "03", "07", "08"]),
                                                           ("estado_comprobante_electronico", "in", ["-", "0_NO_EXISTE"])], limit=50, order="invoice_date asc")
        # _logger.info(invoices.mapped("name"))
        for inv in invoices:
            try:
                inv.action_validez_comprobante()
            except Exception as e:
                pass
            self.env.cr.commit()

    @api.model
    def cron_cambiar_a_no_existe(self):
        return True

    def action_reverse(self):
        if self.documento_baja_id:
            raise UserError(
                "El documento fue dado de baja y no es posible emitir una nota de crédito asociado a este documento anulado.")
        return super(AccountMove, self).action_reverse()

    def action_view_account_move_debit(self):
        if self.documento_baja_id:
            raise UserError(
                "El documento fue dado de baja y no es posible emitir una nota de débito asociado a este documento anulado.")

        return self.env.ref("account_debit_note.action_view_account_move_debit").read()[0]

    def _get_invoiced_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()

        if self.state == 'draft':
            return []

        sale_orders = self.mapped('invoice_line_ids.sale_line_ids.order_id')
        stock_move_lines = sale_orders.mapped(
            'picking_ids.move_lines.move_line_ids')

        # Get the other customer invoices and refunds.
        ordered_invoice_ids = sale_orders.mapped('invoice_ids')\
            .filtered(lambda i: i.state not in ['draft', 'cancel'])\
            .sorted(lambda i: (i.invoice_date, i.id))

        # Get the position of self in other customer invoices and refunds.
        self_index = None
        i = 0
        for invoice in ordered_invoice_ids:
            if invoice.id == self.id:
                self_index = i
                break
            i += 1

        # Get the previous invoice if any.
        previous_invoices = ordered_invoice_ids[:self_index]
        last_invoice = previous_invoices[-1] if len(
            previous_invoices) else None

        # Get the incoming and outgoing sml between self.invoice_date and the previous invoice (if any).
        self_datetime = max(self.invoice_line_ids.mapped(
            'write_date')) if self.invoice_line_ids else None
        last_invoice_datetime = max(last_invoice.invoice_line_ids.mapped(
            'write_date')) if last_invoice else None

        def _filter_incoming_sml(ml):
            if ml.state == 'done' and ml.location_id.usage == 'customer' and ml.lot_id:
                if last_invoice_datetime:
                    return last_invoice_datetime <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        def _filter_outgoing_sml(ml):
            if ml.state == 'done' and ml.location_dest_id.usage == 'customer' and ml.lot_id:
                if last_invoice_datetime:
                    return last_invoice_datetime <= ml.date <= self_datetime
                else:
                    return ml.date <= self_datetime
            return False

        incoming_sml = stock_move_lines.filtered(_filter_incoming_sml)
        outgoing_sml = stock_move_lines.filtered(_filter_outgoing_sml)

        # Prepare and return lot_values
        qties_per_lot = defaultdict(lambda: 0)
        if self.type == 'out_refund':
            for ml in outgoing_sml:
                qties_per_lot[ml.lot_id] -= ml.product_uom_id._compute_quantity(
                    ml.qty_done, ml.product_id.uom_id)
            for ml in incoming_sml:
                qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(
                    ml.qty_done, ml.product_id.uom_id)
        else:
            for ml in outgoing_sml:
                qties_per_lot[ml.lot_id] += ml.product_uom_id._compute_quantity(
                    ml.qty_done, ml.product_id.uom_id)
            for ml in incoming_sml:
                qties_per_lot[ml.lot_id] -= ml.product_uom_id._compute_quantity(
                    ml.qty_done, ml.product_id.uom_id)
        lot_values = []
        for lot_id, qty in qties_per_lot.items():
            if float_is_zero(qty, precision_rounding=lot_id.product_id.uom_id.rounding):
                continue
            lot_values.append({
                'product_id': lot_id.product_id.id,
                'product_name': lot_id.product_id.display_name,
                'quantity': qty,
                'uom_name': lot_id.product_uom_id.name,
                'lot_name': lot_id.name,
            })

        return lot_values


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    tipo_comprobante_a_rectificar = fields.Selection(
        selection=[("00", "Otros"), ("01", "Factura"), ("03", "Boleta"),("91","Comprobante de No Domiciliado")])
    journal_type = fields.Selection(
        selection=[("sale", "Ventas"), ("purchase", "Compras")], string="Tipo de diario")

    credit_note_type = fields.Selection(
        string='Tipo de Nota de Crédito', selection="_selection_credit_note_type")

    def _selection_credit_note_type(self):
        return tnc

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get(
            'active_model') == 'account.move' else self.env['account.move']

        res['refund_method'] = (
            len(move_ids) > 1 or move_ids.type == 'entry') and 'cancel' or 'refund'
        res['residual'] = len(move_ids) == 1 and move_ids.amount_residual or 0
        res['currency_id'] = len(
            move_ids.currency_id) == 1 and move_ids.currency_id.id or False
        res['move_type'] = len(move_ids) == 1 and move_ids.type or False
        res['move_id'] = move_ids[0].id if move_ids else False
        res['tipo_comprobante_a_rectificar'] = move_ids[0].journal_id.invoice_type_code_id if move_ids else False
        res['journal_type'] = move_ids[0].journal_id.type if move_ids else False

        if move_ids.exists():
            journals = self.env["account.journal"].sudo().search([('tipo_comprobante_a_rectificar', '=', res['tipo_comprobante_a_rectificar']),
                                                                  ("invoice_type_code_id","in",["07","97"]),
                                                                  ("company_id","=",self.env.company.id),
                                                                  ("type", "=", res['journal_type'])]).ids
            res['journal_id'] = journals[0] if len(journals) > 0 else False
        else:
            res['journal_id'] = False

        return res

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        res.update({"sustento_nota": self.reason,
                    "tipo_nota_credito": self.credit_note_type,
                    "invoice_type_code": self.journal_id.invoice_type_code_id or "07"})
        if self.credit_note_type in ["04"]:
            res.update({"line_ids": []})
        return res


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    debit_note_type = fields.Selection(
        string='Tipo de Nota de Débito', selection="_selection_debit_note_type")
    tipo_comprobante_a_rectificar = fields.Selection(
        selection=[("00", "Otros"), ("01", "Factura"), ("03", "Boleta")])
    journal_type = fields.Selection(
        selection=[("sale", "Ventas"), ("purchase", "Compras")], string="Tipo de diario")

    def _selection_debit_note_type(self):
        return tnd

    @api.model
    def default_get(self, fields):
        res = super(AccountDebitNote, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get(
            'active_model') == 'account.move' else self.env['account.move']
        if move_ids.exists():
            # _logger.info(move_ids)
            res.update({"journal_type": move_ids[0].journal_id.type,
                        "tipo_comprobante_a_rectificar": move_ids[0].journal_id.invoice_type_code_id})

            journals = self.env["account.journal"].sudo().search([('tipo_comprobante_a_rectificar', '=', res['tipo_comprobante_a_rectificar']),
                                                                  ("invoice_type_code_id","=", "08"),
                                                                  ("company_id","=",self.env.company.id),
                                                                  ("type", "=", res['journal_type'])]).ids
            res['journal_id'] = journals[0] if len(journals) > 0 else False

        return res

    def _prepare_default_values(self, move):
        res = super(AccountDebitNote, self)._prepare_default_values(move)
        res.update({'sustento_nota': self.reason,
                    'tipo_nota_debito': self.debit_note_type, 'invoice_type_code': '08'})
        return res


class CustomPopMessage(models.TransientModel):
    _name = "custom.pop.message"

    name = fields.Char('Message')
    accion = fields.Text(string="Accion a realizar")


class accountInvoiceSend(models.TransientModel):
    _inherit = "account.invoice.send"

    @api.onchange('template_id')
    def onchange_template_id(self):
        for wizard in self:
            if wizard.composer_id:
                attach_ids = []
                invoice = self.invoice_ids[0]
                wizard.composer_id.template_id = wizard.template_id.id
                wizard._compute_composition_mode()
                wizard.composer_id.onchange_template_id_wrapper()

                if wizard.template_id.report_template:
                    report = wizard.template_id.report_template

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = report.render_qweb_pdf([invoice.id])

                    fname = invoice.name+".pdf"
                    result = base64.b64encode(result)
                    attach_ids.append(self.env["ir.attachment"].create(
                        {"name": fname, "type": "binary", "datas": result, "mimetype": "application/pdf", "res_model": "account.move", "res_id": invoice.id, "res_name": invoice.name}).id)

                fname = invoice.name+".xml"
                cdr_fname = invoice.name+"_cdr.xml"
                if invoice.current_log_status_id != False:
                    log_status = invoice.current_log_status_id
                    data_signed_xml = log_status.signed_xml_data_without_format

                    if data_signed_xml:
                        datas = base64.b64encode(
                            data_signed_xml.encode("ISO-8859-1"))
                        attach_ids.append(invoice.env["ir.attachment"].create(
                            {"name": fname, "type": "binary", "datas": datas, "mimetype": "text/xml", "res_model": "account.move", "res_id": invoice.id, "res_name": invoice.name}).id)

                    response_xml = log_status.response_xml_without_format
                    if response_xml:
                        datas = base64.b64encode(
                            response_xml.encode("ISO-8859-1"))
                        attach_ids.append(invoice.env["ir.attachment"].create(
                            {"name": cdr_fname, "type": "binary", "datas": datas, "mimetype": "text/xml", "res_model": "account.move", "res_id": invoice.id, "res_name": invoice.name}).id)

                wizard.attachment_ids = [(4, attach_id)
                                         for attach_id in attach_ids]
