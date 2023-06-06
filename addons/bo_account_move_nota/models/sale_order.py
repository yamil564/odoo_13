from odoo import models,api,fields
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from odoo.addons.bo_backend_sale_invoice_ticket.models.number_to_letter import to_word
import json
import logging
logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    tipo_documento = fields.Selection(
        selection_add=[('100', 'Nota de pedido')], default='03', required=True)

    def emitir_nota(self):
        self.ensure_one()

        if not self.env.company.notes_journal:
            raise UserError("El diario para Notas de Venta debe ser modificado en Ajustes/FacturacionElectrónica")

        if len(self.invoice_ids) == 0:

            self.tipo_documento = "100"
            invoice = self._create_invoices(final=True)
            invoice._onchange_invoice_line_ids()
            invoice.journal_id = self.env.company.notes_journal

        return self.action_view_invoice()
