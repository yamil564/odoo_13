from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
import logging
import os
import shutil
import base64
import zipfile
logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"
    
    def reports_to_zip(self):
        route = self.env["ir.config_parameter"].sudo().search([('key', '=', 'account_report_zip_path')]).value
        path = route + 'reports-'+str(fields.Date.today())
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(path)
        for record in self:
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
            pdf = base64.b64encode(result).decode('utf-8')
            file = open(pdf_name,'w')
            file.write(str(pdf))
            file.close()

        archivo_zip = shutil.make_archive(route + str(fields.Date.today()), "zip", path)
        ctx = {
            'default_file':archivo_zip,
        }
        logger.info('estoy acxa')
        return archivo_zip
        return {
			'name': 'Descarga de ZIP',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'account.zip.reports',
			'target':'new',
			'context':ctx
			}
