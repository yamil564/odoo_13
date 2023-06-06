# -*- coding: utf-8 -*-
from . import number_to_letter
from odoo import models, api


# class AccountReportInvoiceWithPayments(models.AbstractModel):
#     _name = 'report.account.report_invoice_with_payments'

#     @api.model
#     def get_report_values(self, docids, data=None):
#         #report_obj = self.env['report']
#         #report = report_obj._get_report_from_name('account.report_invoice')
#         docs = self.env["account.move"].browse(docids)

#         def generate_text_qr(invoice):
#             ruc_emisor = invoice.company_id.partner_id.vat
#             tipo_comprobante = invoice.journal_id.invoice_type_code_id
#             serie = invoice.journal_id.code
#             numero = invoice.name
#             monto_total_igv = invoice.amount_igv
#             monto_total = invoice.amount_total
#             fecha = invoice.invoice_date
#             tipo_documento_adquirente = invoice.partner_id.l10n_latam_identification_type_id if invoice.partner_id.l10n_latam_identification_type_id else "-"
#             numero_documento = invoice.partner_id.vat if invoice.partner_id.vat else "-"
#             digest_value = invoice.digest_value if invoice.digest_value else "-"
#             s = ruc_emisor+"|"+tipo_comprobante+"|"+serie+"|"+numero.split("-")[1]+"|"+str(monto_total_igv)+"|"+str(
#                 monto_total)+"|"+fecha+"|"+tipo_documento_adquirente+"|"+numero_documento+"|"+digest_value
#             return s

#         return {
#             'doc_ids': docids,
#             'doc_model': "account.move",
#             'docs': docs,
#             'data': data,
#             "generate_text_qr": generate_text_qr,
#             'to_word': number_to_letter.to_word,
#         }


class AccountReportInvoice(models.Model):
    # _name = 'report.account.report_invoice'
    _inherit = "account.move"

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     #report_obj = self.env['report']
    #     #report = report_obj._get_report_from_name('account.report_invoice')
    #     docs = self.env["account.move"].browse(docids)
    def to_word(self, monto, moneda):
        return number_to_letter.to_word(monto, moneda)

    def generate_text_qr(self, invoice):
        ruc_emisor = invoice.company_id.partner_id.vat
        tipo_comprobante = invoice.journal_id.invoice_type_code_id
        serie = invoice.journal_id.code
        numero = invoice.name
        monto_total_igv = invoice.amount_igv
        monto_total = invoice.amount_total
        fecha = invoice.invoice_date
        tipo_documento_adquirente = invoice.partner_id.l10n_latam_identification_type_id.name if invoice.partner_id.l10n_latam_identification_type_id.name else "-"
        numero_documento = invoice.partner_id.vat if invoice.partner_id.vat else "-"
        digest_value = invoice.digest_value if invoice.digest_value else "-"
        s = ruc_emisor+"|"+tipo_comprobante+"|"+serie+"|"+numero.split("-")[1]+"|"+str(monto_total_igv)+"|"+str(
            monto_total)+"|"+str(fecha)+"|"+tipo_documento_adquirente+"|"+numero_documento+"|"+digest_value
        return s

        # return {
        #     'doc_ids': docids,
        #     'doc_model': "account.move",
        #     'docs': docs,
        #     'data': data,
        #     "generate_text_qr": generate_text_qr,
        #     'to_word': number_to_letter.to_word,
        # }
        # return report_obj.render('account.report_invoice', docargs)
