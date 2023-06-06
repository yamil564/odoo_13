from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class BonusRule(models.Model):
    _name = "bonus.rule"

    name = fields.Char(string="Nombre")
    bonus_type = fields.Selection(string="Tipo de regla", selection=[(
        'product_group', 'Por grupo producto'), ('supplier', 'Por proveedor')])
    min_amount = fields.Float(string="Monto", default=0.0)
    supplier_id = fields.Many2one('res.partner', string='Proveedor')
    product_input_line = fields.One2many(
        'bonus.rule.input', 'bonus_id', string='Productos', copy=True)
    product_output_line = fields.One2many(
        'bonus.rule.output', 'bonus_id', string='Bonificación', copy=True)
    taxes_id = fields.Many2many('account.tax', string='Impuesto de bonificación', domain=[
        ('type_tax_use', '=', 'sale')])
    active = fields.Boolean(string="Activo", default=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('production', 'Producción'),
    ], string='Estado', readonly=True, copy=False, index=True, default='draft')

    def action_to_production(self):
        for record in self:
            record.state = 'production'

    @api.depends('name')
    def name_get(self):
        result = []
        for record in self:
            for product in record.product_output_line:
                result.append((record.id, record.name))
        return result


class BonusRuleInputProduct(models.Model):
    _name = "bonus.rule.input"

    bonus_id = fields.Many2one(
        'bonus.rule', string='Bonus id', required=True, ondelete='cascade', copy=False)
    product_id = fields.Many2one(
        'product.product', string='Producto', required=True)
    product_uom_qty = fields.Float(string='Cantidad', digits=dp.get_precision(
        'Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one(
        'uom.uom', string='Unidad de medida', required=True)
    product_price = fields.Float(
        string='Precio', related='product_id.lst_price')
    product_total = fields.Float(
        string='Precio total', compute='_compute_product_price_total')

    @api.onchange("product_id")
    def _onchange_product(self):
        for record in self:
            record.product_uom = record.product_id.uom_id.id

    @api.depends("product_price", "product_uom_qty")
    def _compute_product_price_total(self):
        for record in self:
            record.product_total = record.product_price * record.product_uom_qty


class BonusRuleOutputProduct(models.Model):
    _name = "bonus.rule.output"

    bonus_id = fields.Many2one(
        'bonus.rule', string='Bonus id', required=True, ondelete='cascade', copy=False)
    product_id = fields.Many2one(
        'product.product', string='Producto', required=True)
    product_uom_qty = fields.Float(string='Cantidad', digits=dp.get_precision(
        'Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one(
        'uom.uom', string='Unidad de medida', required=True)
    product_price = fields.Float(string='Precio')
    product_total = fields.Float(
        string='Precio total', compute='_compute_product_price_total')

    @api.onchange("product_id")
    def _onchange_product(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id
            self.product_price = self.product_id.lst_price

    @api.onchange("product_uom")
    def _onchange_product_uom(self):
        if self.product_id and self.product_uom:
            last_ratio = self.product_id.uom_id.factor_inv
            new_ratio = self.product_uom.factor_inv
            self.product_price = (self.product_price / last_ratio) * new_ratio * self.product_uom_qty

    @api.depends("product_price", "product_uom_qty")
    def _compute_product_price_total(self):
        for record in self:
            record.product_total = record.product_price * record.product_uom_qty
