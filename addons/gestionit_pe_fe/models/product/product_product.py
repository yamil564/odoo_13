from odoo import fields,models,api
from odoo.exceptions import UserError
import re

class ProductProduct(models.Model):
    _inherit = "product.product"
    
    is_charge_or_discount = fields.Boolean(related="product_tmpl_id.is_charge_or_discount")
    type_charge_or_discount_id = fields.Many2one("sunat.catalog.53",related="product_tmpl_id.type_charge_or_discount_id",readonly=False)
    sunat_code = fields.Char("Código de Producto SUNAT",related="product_tmpl_id.sunat_code")

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    is_charge_or_discount = fields.Boolean("Es un cargo, descuento u otra deducción?",default=False)
    type_charge_or_discount_id = fields.Many2one("sunat.catalog.53",string="Código de Cargo, Descuento u Otra Deducción",readonly=False)
    sunat_code = fields.Char("Código de Producto SUNAT")
    
    @api.constrains("sunat_code")
    def _check_sunat_code(self):
        if bool(self.sunat_code) and not bool(re.compile("\d{8}$").match(self.sunat_code or "")):
            raise UserError("El código de producto sunat es inválido. El código es un número entero de 8 dígitos.")