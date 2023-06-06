# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    sunat_provider = fields.Selection(selection=[("sunat","SUNAT"),("efact","Efact")],default="sunat")

    sunat_user = fields.Char(
        "USUARIO SUNAT", help="Nombre del usuario secundario con permiso para emisión de comprobantes electrónicos.")
    sunat_pass = fields.Char(
        "CLAVE SUNAT", help="Password del usuario secundario con permiso para emisión de comprobantes electrónicos.")
    tipo_envio = fields.Selection(
        selection=[("0", "0 - Pruebas"), ("1", "1 - Producción")], default="0")

    cert_id = fields.Many2one("cert.sunat", string="Certificados digitales")

    website_invoice_search = fields.Char("Web de consulta de comprobante")
    default_national_bank_account_id = fields.Many2one(
        "res.partner.bank", string="Cuenta de detracciones del Banco de la Nación", domain=[("is_national_bank_detraction", "=", True)])
    # default_product_global_discount_id = fields.Many2one("product.product",domain=[('is_charge_or_discount','=',True),('type_charge_or_discount_id','in',['02'])])
    default_product_global_discount_id = fields.Many2one(
        "product.product", domain=[('is_charge_or_discount', '=', True)])
    default_account_account_retention_id = fields.Many2one("account.account")

    calc_peso = fields.Boolean(string="Calcular peso")

    def get_username_sunat(self):
        return "{}{}".format(self.vat, self.sunat_user or "")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_global_discount_id = fields.Many2one("product.product",
                            related="company_id.default_product_global_discount_id",readonly=False)
    account_account_retention_id = fields.Many2one("account.account",related="company_id.default_account_account_retention_id",readonly=False)

    calc_peso = fields.Boolean(string="Calcular peso automáticamente", related="company_id.calc_peso", readonly=False)