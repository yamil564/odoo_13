from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def has_ei_xml(self):
        account_invoice_log = self.account_log_status_ids
        if account_invoice_log.exists():
            account_invoice_log = account_invoice_log[len(account_invoice_log)-1]

        return True if account_invoice_log.signed_xml_data_without_format else False

    def has_ei_cdr(self):
        account_invoice_log = self.account_log_status_ids
        if account_invoice_log.exists():
            account_invoice_log = account_invoice_log[len(account_invoice_log)-1]

        return True if account_invoice_log.response_xml_without_format else False