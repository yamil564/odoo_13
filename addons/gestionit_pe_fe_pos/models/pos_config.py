from odoo import models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    anonymous_id = fields.Many2one('res.partner', string='Cliente Anónimo')
    module_account_invoicing = fields.Boolean("Habilitar múltiples series")
    invoice_journal_ids = fields.Many2many("account.journal",
                                           string="Series disponibles",
                                           domain=[("invoice_type_code_id", "in", ["01", "03", "07"])])

    receipt_show_logo = fields.Boolean("Mostrar logo en ticket", default=True)
    receipt_show_default_code = fields.Boolean(
        "Mostrar Ref.Interna en Ticket", default=False)
    products_show_default_code = fields.Boolean(
        "Mostrar Ref.Interna en Lista de Productos", default=False)
    required_journal = fields.Boolean(
        "Solicitar diario obligatorio", default=False)

    iface_credit_note = fields.Boolean("Permitir Emitir Nota de crédito")
