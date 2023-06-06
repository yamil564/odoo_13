from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning, RedirectWarning
import re
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    force_destination_account_id = fields.Many2one('account.account',string="Cuenta Contrapartida",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")

    operation_number = fields.Char(string="Número de Operación")


    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id','force_destination_account_id')
    def _compute_destination_account_id(self):
        super(AccountPayment,self)._compute_destination_account_id()
        ##########################################
        for payment in self:
            if payment.force_destination_account_id:
                payment.destination_account_id = payment.force_destination_account_id