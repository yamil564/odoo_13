# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
import logging
import os
import shutil
import base64
import zipfile
import io
logger = logging.getLogger(__name__)

class AccountZipReports(models.TransientModel):
    _name = "account.zip.reports"

    file = fields.Binary(string="Reportes", readonly=True, compute="get_file")
    invoice_ids = fields.Many2many('account.move', string="Facturas")

    def get_file(self):
        route = self.env["ir.config_parameter"].sudo().search([('key', '=', 'account_report_zip_path')]).value
        path = route + 'reports-'+str(fields.Date.today())
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(path)
        for record in self.invoice_ids:
            # For XML files
            xml_name = path + '/' + record.name + '.xml'
            log_status = record.current_log_status_id
            if log_status:
                file = open(xml_name,'w')
                data_signed_xml = log_status.signed_xml_data
                file.write(str(data_signed_xml))
                file.close()
            # For PDF files
            pdf_name = path + '/' + record.name + '.pdf'
            result, format = self.env.ref('account.account_invoices').render_qweb_pdf([record.id])
            file = open(pdf_name,'wb')
            file.write(result)
            file.close()

        archivo = shutil.make_archive(route + str(fields.Date.today()), "zip", path)

        fp = io.BytesIO()
        zf = zipfile.ZipFile(fp, "w")
        try:
            for folder, subfolders, files in os.walk(path):
                for file in files:
                    zf.write(os.path.join(folder, file), os.path.relpath(os.path.join(folder,file), path), compress_type = zipfile.ZIP_DEFLATED)
            zf.close()
            self.file = base64.encodestring(fp.getvalue())
        except Exception as e:
            raise e