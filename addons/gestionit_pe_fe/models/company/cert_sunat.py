# -*- coding: utf-8 -*-
from odoo import api, models, fields


class CertSunat(models.Model):
    _name = "cert.sunat"
    _description = "Certificado de SUNAT"

    key_public = fields.Text("Cert. PUBLIC",required=True)
    key_private = fields.Text("Cert. PRIVATE",required=True)
    expiration_date = fields.Date(string='Fecha de expiración',required=True)
    issue_date = fields.Date(string='Fecha de emisión',required=True)
    active = fields.Boolean(string="Activo", default=True)
    company_id = fields.Many2one("res.company",default=lambda self:self.env.company.id)

    def name_get(self):
        result = []
        for cert in self:
            name = "Certificado Digital Emisión:{} - Exp:{}".format(cert.issue_date,cert.expiration_date) 
            result.append((cert.id,name))
            
        return result