# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.profiler import profile
from odoo.exceptions import UserError, ValidationError

import logging
log = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    tipo_afectacion_igv_type = fields.Char("Tipo Afectación IGV - Tipo")
    tipo_afectacion_igv_code = fields.Char("Tipo Afectación IGV - Código")
    tipo_afectacion_igv_name = fields.Char("Tipo Afectación IGV - Nombre")
    no_onerosa = fields.Boolean("No onerosa", compute="_compute_afectacion")
    descuento_unitario = fields.Float("Descuento Unitario")

    is_charge_or_discount = fields.Boolean(
        string="Es Cargo/Descuento/Deducción?")
    type_charge_or_discount_code = fields.Char(
        "Código de cargo, descuento u otra deducción")

    lot_name = fields.Char(string="Lot/Serie")

    @api.onchange('discount')
    def _onchange_discount(self):
        for record in self:
            if record.discount >= 100:
                record.discount = 0

    @api.onchange('name')
    def _onchange_name(self):
        for record in self:
            if record.name:
                record.name = record.name.strip()
                record.name = record.name.replace("\n", " ")

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount

        # Compute 'price_total'.
        if taxes:
            if not all(tax in ["31", "32", "33", "34", "35", "36", "37"] for tax in taxes.mapped("tax_group_id.tipo_afectacion")):
                taxes_res = taxes._origin.compute_all(price_unit_wo_discount, quantity=quantity, currency=currency,
                                                      product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                res['price_subtotal'] = taxes_res['total_excluded']
                res['price_total'] = taxes_res['total_included']
            else:
                res['price_subtotal'] = 0
                res['price_total'] = 0
                return res
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}

        # log.info(res)
        return res

    def _compute_afectacion(self):
        for line in self:
            line.no_onerosa = line.tax_ids[0].tax_group_id.no_onerosa if len(
                line.tax_ids) > 0 else False

    # @profile
    @api.onchange("tax_ids")
    def _afectacion_igv(self):
        self.tipo_afectacion_igv_type = self.tax_ids[0].tax_group_id.tipo_afectacion if self.tax_ids else False
        self.tipo_afectacion_igv_code = self.tax_ids[0].tax_group_id.codigo if self.tax_ids else False
        self.tipo_afectacion_igv_name = self.tax_ids[0].tax_group_id.descripcion if self.tax_ids else False

    
    @api.constrains("tax_ids")
    def check_type_tax_ids(self):
        for record in self:
            if record.tax_ids:
                group_igv = len([line_tax for line_tax in record.tax_ids 
                    if line_tax.tax_group_id.tipo_afectacion in ["10"]])

                if group_igv>1:
                    raise UserError("No se puede incluir mas de un impuesto del Tipo IGV !!")      
