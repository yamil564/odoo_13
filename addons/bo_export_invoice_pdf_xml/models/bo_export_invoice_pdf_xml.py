from odoo import tools
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError , ValidationError

class BoExportInvoicePdfXml(models.TransientModel):
    _name = "bo.export.invoice.pdf.xml"
    _description = "Exportación Masiva de XML y PDF de Comprobantes Electrónicos"

    ######################
    company_id = fields.Many2one('res.company',
        string="Compañia", 
        default=lambda self: self.env['res.company']._company_default_get('account.invoice'),
        domain = lambda self: [('id', 'in',[i.id for i in self.env['res.users'].browse(self.env.user.id).company_ids] )],readonly=True)
    
    partner_id=fields.Many2one("res.partner",string="Cliente")

    rango_fechas=fields.Boolean(string="Rango de Fechas",default=False)

    fecha_inicio=fields.Date(string="Fecha Inicio",default=datetime.now().date())
    fecha_fin=fields.Date(string="Fecha Fin",default=datetime.now().date())

    nro_maximo_exportacion = fields.Integer(string="Número Maximo de Documentos a Exportar",
        default=lambda self:self.env['res.company']._company_default_get().nro_maximo_exportacion)
    ######################

    def action_download_zip_massive(self):
        ### Here code
        return True
        
