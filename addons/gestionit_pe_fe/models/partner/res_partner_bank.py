from odoo import fields, models, api


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    is_national_bank_detraction = fields.Boolean(
        "Banco de la Nación para Detracciones")
    description = fields.Char(string="Descripción")
    show_report_sale = fields.Boolean("Mostrar en ventas",default=True)
