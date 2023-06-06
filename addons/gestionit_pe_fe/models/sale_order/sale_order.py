# -*- coding: utf-8 -*-
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
from odoo import fields, models, api, _
from odoo.tools.profiler import profile
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from itertools import groupby
from datetime import datetime, timedelta
from pytz import timezone
from werkzeug.urls import url_encode
from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tdi
from odoo.addons.gestionit_pe_fe.models.number_to_letter import to_word
import json
import time
import uuid
import os
import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_by_location = fields.Char(compute="_compute_qty_by_location")

    @api.onchange('product_id')
    def _compute_qty_by_location(self):
        for record in self:
            if record.product_id.exists() and record.display_type is False:
                self.env.cr.execute("""select complete_name as name,sq.quantity as quantity from stock_location as sl 
                                            left join stock_quant as sq on sq.location_id = sl.id and sq.product_id={}
                                            where sl.usage = 'internal' and sl.active=True""".format(record.product_id.id))
                result = self.env.cr.dictfetchall()
                record.qty_by_location = json.dumps(result)
            else:
                record.qty_by_location = 0


class SalePaymenttermLine(models.Model):
    _name = "sale.paymentterm.line"
    _order = "date_due ASC"
    _description = "Líneas de término de pago de ventas"

    currency_id = fields.Many2one(
        "res.currency", related="order_id.currency_id")
    order_id = fields.Many2one("sale.order", "Sale order")
    date_due = fields.Date("Fecha de vencimiento estimada")
    amount = fields.Float("Monto")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # * INICIO: Cuotas de pago en orden de venta
    paymentterm_line = fields.One2many("sale.paymentterm.line", "order_id")
    payment_term_type = fields.Char(compute="_compute_payment_term_type")
    date_due = fields.Date('Fecha de Vencimiento', compute='_get_date_due')

    residual_credit_paymentterm = fields.Monetary(
        "Saldo restante de plazos de pago a crédito", compute="_compute_residual_credit_paymentterm")

    @api.depends('payment_term_id')
    def _get_date_due(self):
        for record in self:
            if record.payment_term_id and record.date_order:
                self.date_due = record.payment_term_id.compute(0, date_ref=record.date_order, currency=record.company_id.currency_id)[0][0]
            else:
                self.date_due = False

    ########################## RESTRICCIÓN PARA FECHAS EN CUOTAS DE PAGO DE COTIZACIONES ###########
    @api.constrains('date_due','paymentterm_line','paymentterm_line.date_due')
    def check_date_cuotas_vs_date_due(self):
        for rec in self:
            list_date_due = list(rec.paymentterm_line.mapped('date_due'))
            if rec.paymentterm_line and rec.date_due and list_date_due:
                max_date_due = max(list_date_due)
                if max_date_due>rec.date_due:
                    raise UserError("La Fecha de las cuotas no puede ser mayor a la fecha de vencimiento de la cotización !!")   

    ##########################################################################################


    @api.depends("paymentterm_line",
                 "paymentterm_line.amount",
                 "amount_total")
    def _compute_residual_credit_paymentterm(self):
        for order in self:
            order.residual_credit_paymentterm = round(
                self.amount_total - sum(order.paymentterm_line.mapped("amount")), 2)

    @api.depends("payment_term_id")
    def _compute_payment_term_type(self):
        for record in self:
            record.payment_term_type = "Contado"
            if record.payment_term_id:
                record.payment_term_type = record.payment_term_id.type


    @api.onchange("pricelist_id")
    def onchange_pricelist(self):
        for line in self.order_line:
            line.product_id_change()
            
    def check_paymenttermn_lines(self):
        for record in self:
            if record.payment_term_id:
                if record.payment_term_type == "Credito":
                    amount_total = round(
                        sum(record.paymentterm_line.mapped("amount")), 2)

                    if amount_total != round(record.amount_total, 2):
                        raise UserError(
                            "El monto total de los plazos de pago debe ser igual al total de la venta.")
                    if record.date_order:
                        if min(record.paymentterm_line.mapped("date_due")) < record.date_order.date():
                            raise UserError(
                                "La fecha de vencimiento de la cuota debe ser mayor o igual a la fecha de la venta")
                    else:
                        if min(record.paymentterm_line.mapped("date_due")) < datetime.now(tz=timezone("America/Lima")).date():
                            raise UserError(
                                "La fecha de vencimiento de la cuota debe ser mayor o igual a la fecha de la venta")

    def action_confirm(self):
        self.check_paymenttermn_lines()
        res = super(SaleOrder, self).action_confirm()
        return res

    # * FIN: Cuotas de pago en orden de venta

    def to_word(self, monto, moneda):
        return to_word(monto, moneda)

    tipo_documento_identidad = fields.Selection(
        selection="_selection_tipo_documento_identidad")

    def _selection_tipo_documento_identidad(self):
        return tdi

    tipo_documento = fields.Selection(
        string="Tipo de Documento",
        selection=[('01', 'Factura'), ('03', 'Boleta')],
        default="01",
        required=True)

    @api.onchange("tipo_documento_identidad")
    def _onchange_tipo_documento_identidad(self):
        if self.tipo_documento_identidad == "6":
            self.tipo_documento = "01"
        else:
            self.tipo_documento = "03"

    apply_same_discount_on_all_lines = fields.Boolean("Aplicar el mismo descuento en todas las líneas?", states={
                                                      'draft': [('readonly', False)]}, readonly=True)
    discount_on_all_lines = fields.Integer(
        "Descuento (%)", states={'draft': [('readonly', False)]}, readonly=True)

    def action_apply_same_discount_on_all_lines(self):
        self.order_line = [
            (1, line.id, {"discount": self.discount_on_all_lines}) for line in self.order_line]

    def order_lines_layouted(self):
        """
        Returns this order lines classified by sale_layout_category and separated in
        pages according to the category pagebreaks. Used to render the report.
        """
        self.ensure_one()
        report_pages = [[]]
        #print(list(groupby(self.order_line, lambda l: l.layout_category_id)))
        for category, lines in groupby(self.order_line, lambda l: l.layout_category_id):

            if report_pages[-1] and report_pages[-1][-1]['pagebreak']:
                report_pages.append([])
            report_pages[-1].append({
                'parent': category.parent.name,
                'name': category and category.name or _('Uncategorized'),
                'subtotal': category and category.subtotal,
                'pagebreak': category and category.pagebreak,
                'lines': list(lines)
            })

        return report_pages

    @api.model
    def _get_default_warehouse_ids(self):
        _logger.info(self._context)
        user = self.env.user
        wh_ids = user.sudo().warehouse_ids.filtered(lambda r: r.company_id.id in  self._context.get("allowed_company_ids",[]))
        if len(wh_ids) > 0:
            return wh_ids.ids
        else:
            raise UserError("Para crear una venta su usuario debe estar asociado a un almacén de la compañia. Comuníquese con su administrador.")
        
    warehouses_allowed_ids = fields.Many2many("stock.warehouse", string="Almacenes Permitidos", default=_get_default_warehouse_ids)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            user = self.env.user
            warehouse_ids = user.warehouse_ids.filtered(lambda r: r.company_id.id in self._context.get("allowed_company_ids",[]))
            if warehouse_ids.exists():
                self.warehouse_id = warehouse_ids[0].id
            else:
                self.warehouse_id = False


    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()

        paymentterm_lines = []
        for pl in self.paymentterm_line:
            paymentterm_lines.append(self.env['paymentterm.line'].create(
                {'currency_id': pl.currency_id, 'date_due': pl.date_due, 'amount': pl.amount}).id)

        res.update({
            "invoice_type_code": self.tipo_documento,
            "descuento_global": self.descuento_global,
            "apply_global_discount": True if self.descuento_global > 0 else False,
            "apply_same_discount_on_all_lines": self.apply_same_discount_on_all_lines,
            "discount_on_all_lines": self.discount_on_all_lines,
            "paymentterm_line": [(6, 0, paymentterm_lines)],
        })

        warehouse_id = self.warehouse_id
        if warehouse_id:
            res["warehouse_id"] = warehouse_id.id
            journals = self.env["stock.warehouse"].browse(warehouse_id.id).journal_ids.filtered(
                lambda r: r.invoice_type_code_id == self.tipo_documento and r.type == "sale")
            if len(journals) > 0:
                res["journal_id"] = journals[0].id
            else:
                raise UserError(
                    "Debe configurar Diarios disponibles en sus almacénes. Contacte con su administrador.")
        else:
            raise UserError(
                "Su usuario no tiene almacenes disponibles. Contacte con su administrador.")

        return res

    total_venta_gravado = fields.Monetary(
        string="Gravado",
        default=0.0,
        compute="_amount_all",
        currency_field='currency_id')
    total_venta_inafecto = fields.Monetary(
        string="Inafecto",
        default=0.0,
        compute="_amount_all")
    total_venta_exonerada = fields.Monetary(
        string="Exonerado",
        default=0.0,
        compute="_amount_all",
        currency_field='currency_id')
    total_venta_gratuito = fields.Monetary(
        string="Gratuita",
        default=0.0,
        compute="_amount_all",
        currency_field='currency_id', store=True)
    total_descuentos = fields.Monetary(
        string="Total Descuentos",
        default=0.0,
        compute="_amount_all",
        currency_field='currency_id')

    total_igv = fields.Monetary(
        string="IGV",
        default=0.0,
        compute="_amount_all",
        currency_field='currency_id')

    descuento_global = fields.Float(
        string="Descuento Global (%)",
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=0.0)

    total_descuento_global = fields.Monetary(
        string="Total Descuentos Global",
        default=0.0,
        compute="_amount_all",
        currency_field='currency_id')

    @api.depends('order_line', 'order_line.product_id', 'order_line.price_unit', 'order_line.product_uom_qty', 'order_line.tax_id', 'order_line.discount', 'descuento_global')
    def _amount_all(self):
        for order in self:
            total_descuento_global = sum(
                [
                    line.price_subtotal
                    for line in order.order_line
                    if len([line.price_subtotal for line_tax in line.tax_id
                            if line_tax.tax_group_id.tipo_afectacion not in ["31", "32", "33", "34", "35", "36"]])
                ])*order.descuento_global/100.0

            total_venta_gravado = sum(
                [
                    line.price_subtotal
                    for line in order.order_line
                    if len([line.price_subtotal for line_tax in line.tax_id if line_tax.tax_group_id.tipo_afectacion in ["10"]]) or len(line.tax_id) == 0

                ])*(1-order.descuento_global/100.0)

            total_venta_inafecto = sum(
                [
                    line.price_subtotal
                    for line in order.order_line
                    if len(
                        [line.price_subtotal for line_tax in line.tax_id
                         if line_tax.tax_group_id.tipo_afectacion in ["40", "30"]])
                ])*(1-order.descuento_global/100.0)

            total_venta_exonerada = sum(
                [
                    line.price_subtotal
                    for line in order.order_line
                    if len(
                        [line.price_subtotal for line_tax in line.tax_id
                         if line_tax.tax_group_id.tipo_afectacion in ["20"]])
                ])*(1-order.descuento_global/100.0)

            total_venta_gratuito = sum(
                [
                    line.price_unit*line.product_uom_qty
                    for line in order.order_line
                    if len([line.price_subtotal for line_tax in line.tax_id
                            if line_tax.tax_group_id.tipo_afectacion in ["31", "32", "33", "34", "35", "36"]])
                ])

            total_descuentos = sum(
                [
                    ((line.price_subtotal / (1-(line.discount/100.0))) * line.discount/100.0)
                    for line in order.order_line
                        if line.discount < 100
                ]) + total_descuento_global

            # amount_tax = (sum(
            #     [line.price_tax for line in order.order_line])+total_venta_gratuito)*(1-order.descuento_global/100)

            total_igv = (
                sum([line.price_tax for line in order.order_line]))*(1-order.descuento_global/100)

            order.update({
                'total_descuento_global': total_descuento_global,
                'total_venta_gravado': total_venta_gravado,
                'total_venta_inafecto': total_venta_inafecto,
                'total_venta_exonerada': total_venta_exonerada,
                'total_venta_gratuito': total_venta_gratuito,
                'total_descuentos': total_descuentos,
                'total_igv': total_igv,
                'amount_untaxed': total_venta_gravado + total_venta_exonerada + total_venta_inafecto,
                'amount_total': total_venta_gravado + total_venta_exonerada + total_venta_inafecto + total_igv
            })

    guia_remision_ids = fields.Many2many("gestionit.guia_remision")

    def so_action_context_default_guia_remision(self):
        return {
            "default_documento_asociado": "orden_venta",
            "default_fecha_emision": fields.Date.today(),
            "default_fecha_inicio_traslado": fields.Date.today(),
            # "default_modalidad_transporte":"01",
            "default_motivo_traslado": "01",
            "default_sale_order_ids": [(6, 0, [self.id])],
            "default_destinatario_partner_id": self.partner_id.id,
            "default_company_partner_id": self.partner_id.id
        }

    def so_action_open_guia_remision(self):
        guia_remision_ids = self.guia_remision_ids + \
            self.invoice_ids.mapped("guia_remision_ids")
        if len(guia_remision_ids) > 1:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "gestionit.guia_remision",
                "domain": [("id", "in", guia_remision_ids.mapped("id"))],
                "target": "self",
                "view_mode": "tree"
            }
        else:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "gestionit.guia_remision",
                "context": self.so_action_context_default_guia_remision(),
                "target": "self",
                "view_mode": "form"
            }
        return action
