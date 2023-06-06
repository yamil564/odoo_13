from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
_logger = logging.getLogger(__name__)


class bonusRuleWizardTemp(models.TransientModel):
    _name = "bonus.rule.wizard.temp"

    name = fields.Char(string="Name")
    bonus_id = fields.Many2one("bonus.rule", string="Bonificaciones")
    bonus_qty = fields.Float(string="Bonus quantity", default=1)

    @api.depends('name')
    def name_get(self):
        result = []
        for record in self:
            name = "{} - (Max.: {})".format(record.bonus_id.name,
                                            str(record.bonus_qty))
            result.append((record.id, name))
        return result


class bonusRulesWizard(models.TransientModel):
    _name = "bonus.rule.wizard"

    bonus_allowed_ids = fields.Many2many(
        "bonus.rule.wizard.temp", string="Bonus permitidos")
    bonus_id = fields.Many2one(
        "bonus.rule.wizard.temp", string="Bonificaciones")
    order_id = fields.Many2one(
        "sale.order", string="Orden de venta", readonly=True)
    bonus_qty = fields.Float(string="Cant. de bonificación", default=1.0)

    @api.onchange('bonus_id')
    def _onchange_bonus_id(self):
        self.bonus_qty = self.bonus_id.bonus_qty

    @api.onchange('bonus_qty')
    def _onchange_bonus_qty(self):
        if self.bonus_id:
            if self.bonus_qty > self.bonus_id.bonus_qty:
                self.bonus_qty = self.bonus_id.bonus_qty
                raise UserError(
                    "Está asignando una cantidad mayor a la permitida, por favor revisar.")
            if self.bonus_qty < 1:
                self.bonus_qty = self.bonus_id.bonus_qty
                raise UserError(
                    "No puede asignar 0 cantidad de bonificaciones.")

    def add_bonus_product(self):
        for record in self:
            if record.bonus_qty > record.bonus_id.bonus_qty:
                record.bonus_qty = record.bonus_id.bonus_qty
                raise UserError(
                    "Está asignando una cantidad mayor a la permitida, por favor revisar.")
            elif record.bonus_qty < 1:
                record.bonus_qty = record.bonus_id.bonus_qty
                raise UserError(
                    "No puede asignar 0 cantidad de bonificaciones.")
            else:
                lines_to_update = record.env["sale.order.line"].search(
                    [('order_id', '=', record.order_id.id)])
                # Actualizo cantidades líneas input
                for bonus_line_updated in record.bonus_id.bonus_id.product_input_line:
                    for ltu in lines_to_update:
                        if ltu.product_id == bonus_line_updated.product_id:
                            ltu.qty_bonus_available -= bonus_line_updated.product_uom_qty * record.bonus_qty

                # Asigno bonificación
                for bonus_line_added in record.bonus_id.bonus_id.product_output_line:
                    _logger.info(record.bonus_id.bonus_id)
                    qty_available = bonus_line_added.product_id.virtual_available * \
                                    bonus_line_added.product_id.uom_id.factor_inv / \
                                    bonus_line_added.product_uom.factor_inv
                    line_available = qty_available >= (
                            bonus_line_added.product_uom_qty * record.bonus_qty)
                    line = record.env["sale.order.line"].create({
                        'product_id': bonus_line_added.product_id.id,
                        'order_id': record.order_id.id,
                        'bonus_id': record.bonus_id.bonus_id.id,
                        'name': bonus_line_added.product_id.name,
                        'qty_bonus_available': 0.0,
                        'product_uom_qty': bonus_line_added.product_uom_qty * record.bonus_qty,
                        'product_uom': bonus_line_added.product_uom.id,
                        'is_bonus': True,
                        'price_unit': bonus_line_added.product_price,
                        'qty_available': qty_available,
                        'line_available': line_available,
                        'tax_id': [(6, 0, record.bonus_id.bonus_id.taxes_id.ids)],
                    })


class saleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_bonus = fields.Boolean(string="Es bonificación?", default=False)
    qty_bonus_available = fields.Float(
        string="Qty. bonus available", default=1.0)
    bonus_id = fields.Many2one("bonus.rule", string="Bonificaciones")
    product_uom_clone = fields.Many2one(
        'uom.uom', string='Unit of Measure', required=True, related="product_uom")
    qty_available = fields.Float("Cnt. disp. actual")
    line_available = fields.Boolean("Disponible")

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

    @api.onchange('product_id', 'product_uom_qty', 'product_uom')
    def _onchange_product_qty_available(self):
        for record in self:
            if record.product_id and record.product_uom_qty and record.product_uom:
                # if not record.product_id.is_combo:
                record.qty_available = record.product_id.virtual_available * \
                                        record.product_id.uom_id.factor_inv / record.product_uom.factor_inv
                record.line_available = record.qty_available >= record.product_uom_qty
                # else:
                #     _min = 1000000000
                #     for pr in record.product_id.combo_product_id:
                #         cantidad_disponible = pr.product_quantity * \
                #                               pr.uom_id.factor_inv / pr.product_id.uom_id.factor_inv
                #         cantidad_combos_por_producto = pr.product_id.virtual_available / cantidad_disponible
                #         _min = min(_min, cantidad_combos_por_producto)

                #     record.qty_available = _min
                #     record.line_available = record.qty_available >= record.product_uom_qty


class saleOrder(models.Model):
    _inherit = "sale.order"

    bonus_allowed_ids = fields.Many2many(
        "bonus.rule.wizard.temp", string="Bonus temp")
    order_bonus_line = fields.One2many("sale.order.line", "order_id", domain=[
        ("is_bonus", "=", True)])
    order_line_clone = fields.One2many('sale.order.line', 'order_id', string='Order Lines', states={'cancel': [(
        'readonly', True)], 'done': [('readonly', True)]}, copy=False, auto_join=True,
                                       domain=[("is_bonus", "=", False)])

    @api.constrains('order_line_clone')
    def _check_exist_product_in_line(self):
        for sale in self:
            exist_product_list = []
            for line in sale.order_line_clone:
                if line.product_id.id in exist_product_list:
                    raise ValidationError(
                        'El producto: [%s], se encuentra registrado más de una vez en el pedido. Por favor revise su orden de venta.' % (
                            line.product_id.name))
                    # raise ValidationError("El Producto %s no puede ser menor al precio"%(line.product_id.name))
                exist_product_list.append(line.product_id.id)

    @api.depends('order_bonus_line')
    def _compute_has_bonus(self):
        for record in self:
            record.has_bonus = len(record.order_bonus_line) > 0

    has_bonus = fields.Boolean(compute=_compute_has_bonus)

    def action_assign_bonus(self):
        temp_bonus_groups = []
        final_bonus_groups = []
        a = []

        bonus_rules = self.env['bonus.rule'].search(
            [('state', '=', 'production')])
        order_lines_valid = self.env['sale.order.line'].search(
            [('id', 'in', self.order_line.mapped('id')), ('is_bonus', '=', False)]).mapped('product_id')

        for bg in bonus_rules.filtered(lambda r: r.bonus_type == "product_group"):
            if len(bg.product_input_line) <= len(order_lines_valid):
                check = all(
                    item in order_lines_valid for item in bg.product_input_line.mapped('product_id'))
                if check:
                    temp_bonus_groups.append(bg)

        # supplier_ids = self.order_line.filtered(
        #     lambda r: not r.is_bonus).mapped("product_id.supplier_id")
        for bg in bonus_rules.filtered(lambda r: r.bonus_type == "supplier"):
            amount_total_supplier = sum(self.order_line.filtered(
                lambda r: not r.is_bonus and r.product_id.supplier_id == bg.supplier_id).mapped("price_total"))
            if amount_total_supplier >= bg.min_amount:
                temp_bonus_groups.append(bg)

        for rule in temp_bonus_groups:
            temp = []

            bonus_product_lines = self.order_line.filtered(
                lambda r: r.is_bonus)
            # bonus_product_lines = self.bonus_line
            # amount_total_supplier = sum(self.order_line.filtered(
            #     lambda r: not r.is_bonus).mapped("price_total"))

            if rule.bonus_type == "product_group":
                for olp in self.order_line.filtered(lambda r: not r.is_bonus):
                    # for olp in self.order_line:

                    qty_bonus_available = olp.product_uom_qty

                    if len(bonus_product_lines) > 0:
                        for bpl in bonus_product_lines:
                            if bpl.bonus_id.bonus_type == "product_group":
                                for ibpl in bpl.bonus_id.product_input_line:
                                    if ibpl.product_id == olp.product_id:
                                        qty_bonus_available -= bpl.product_uom_qty * ibpl.product_uom_qty
                            elif bpl.bonus_id.bonus_type == "supplier":
                                if olp.product_id.supplier_id == bpl.bonus_id.supplier_id:
                                    cnt_lines = len(self.order_line.filtered(
                                        lambda r: r.product_id.supplier_id == bpl.bonus_id.supplier_id))
                                    # Qtyarestar = (Total de A - montoderegla/cantidadlineasdeventapararegla)/preciounitariodelinea
                                    qty_prorrateada = (
                                                              bpl.bonus_id.min_amount * bpl.product_uom_qty / cnt_lines) / olp.price_unit
                                    qty_bonus_available -= qty_prorrateada

                    exists_input_line = rule.product_input_line.filtered(
                        lambda r: r.product_id == olp.product_id)
                    if len(exists_input_line) > 0:
                        res = qty_bonus_available % exists_input_line[0].product_uom_qty
                        max_value = (qty_bonus_available - res) / \
                                    exists_input_line[0].product_uom_qty
                        temp.append({"product_id": olp.product_id,
                                     "max_value_for_rule": max_value})

                seq = [x['max_value_for_rule'] for x in temp]

                if min(seq) > 0:
                    final_bonus_groups.append(rule)
                    a.append(self.env["bonus.rule.wizard.temp"].create(
                        {'bonus_id': rule.id, 'bonus_qty': min(seq)}).id)

            elif rule.bonus_type == "supplier":
                # Considerarar por cantidad y por monto
                amount_for_rule = sum(self.order_line.filtered(
                    lambda r: not r.is_bonus and r.product_id.supplier_id == rule.supplier_id).mapped("price_total"))

                for olp in self.order_line.filtered(lambda r: not r.is_bonus):
                    if len(bonus_product_lines) > 0:
                        for bpl in bonus_product_lines:
                            if bpl.bonus_id.bonus_type == "product_group":
                                for ibpl in bpl.bonus_id.product_input_line:
                                    if ibpl.product_id == olp.product_id:
                                        amount_for_rule -= (bpl.product_uom_qty *
                                                            ibpl.product_uom_qty) * olp.price_unit
                for bpl in bonus_product_lines:
                    if bpl.bonus_id.bonus_type == "supplier":
                        amount_for_rule -= bpl.bonus_id.min_amount * bpl.product_uom_qty
                    # if olp.product_id.supplier_id == bpl.bonus_id.supplier_id:
                    #     cnt_lines = len(self.order_line.filtered(
                    #         lambda r: r.product_id.supplier_id == bpl.bonus_id.supplier_id))
                    #     # Qtyarestar = (Total de A - montoderegla/cantidadlineasdeventapararegla)/preciounitariodelinea
                    #     amount_prorrateada = (
                    #         bpl.bonus_id.min_amount/cnt_lines)
                    #     amount_for_rule -= amount_prorrateada

                if amount_for_rule >= rule.min_amount:
                    a.append(self.env["bonus.rule.wizard.temp"].create(
                        {'bonus_id': rule.id, 'bonus_qty': amount_for_rule // rule.min_amount}).id)
                # for olp in lines_for_rule:
                #     qty_restar = (olp.price_total -
                #                   rule.min_amount/len(lines_for_rule))/olp.price_unit

                #     _logger.info("Cantidad a restar")
                #     _logger.info(qty_restar)
                # pass
                # qty_bonus * product_uoimqty_restar

        self.bonus_allowed_ids = [(6, 0, a)]

        ref = self.env.ref("sales_bonus_rules.assign_bonus_wizard")
        return {
            "type": "ir.actions.act_window",
            "res_model": "bonus.rule.wizard",
            "target": "new",
            "view_id": ref.id,
            "view_mode": "form",
            "context": {
                "default_bonus_allowed_ids": self.bonus_allowed_ids.mapped('id'),
                "default_order_id": self.id,
            }
        }

    def lines_update(self):
        return
    # @api.depends('order_line_clone', 'order_line_clone.product_id', 'order_line_clone.price_unit', 'order_line_clone.product_uom_qty', 'order_line_clone.tax_id', 'order_line_clone.discount', 'descuento_global')
    # def _amount_all_clone(self):
    #     self._amount_all()
