from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning, RedirectWarning
import re
import logging

from odoo.addons.gestionit_pe_fe.models.parameters.catalogs import tdc


_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"


    #prefix_code=fields.Char(string="Serie del Comprobante")
    #invoice_number=fields.Char(string="Correlativo del Comprobante")

    #type_document_id = fields.Selection(string="Tipo de Documento",selection="_selection_invoice_type",
    #    compute="compute_campo_type_document_id",store=True)

    flag_length_document_number = fields.Boolean(string="Correlativo tiene mas de 8 dígitos",
        compute="compute_flag_length_document_number")


    @api.depends('journal_id','invoice_number','type')
    def compute_flag_length_document_number(self):
        for rec in self:
            rec.flag_length_document_number = False
            type_document_id = False

            if rec.journal_id and rec.journal_id.invoice_type_code_id and \
                rec.invoice_number and rec.type in ['in_invoice','in_refund']:

                type_document_id = rec.journal_id.invoice_type_code_id

                if type_document_id not in ['91','97','98'] and len(rec.invoice_number or '')>8:
                    rec.flag_length_document_number = True
                else:
                    rec.flag_length_document_number = False
            else:
                rec.flag_length_document_number = False
