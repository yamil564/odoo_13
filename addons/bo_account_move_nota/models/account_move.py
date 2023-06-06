from odoo import models,api,fields
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from odoo.addons.bo_backend_sale_invoice_ticket.models.number_to_letter import to_word
import json
import logging
logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_type_code = fields.Selection(selection_add=[('100', 'Nota de pedido')])
