from odoo import models, api, fields, _

class SummarySequence(models.Model):
    _name = "summary.sequence"
    _description = "Secuencia de Resumen diario"

    type = fields.Selection(selection=[('RA','RA'),('RC','RC')])
    next_number = fields.Integer("Siguiente Número",default=1)
    date = fields.Date("Fecha")
    company_id = fields.Many2one("res.company",default=lambda self:self.env.company.id)

    @api.model
    def get_next_number(self,date,type,company_id):
        seq = self.search([("type","=",type),("company_id","=",company_id),("date","=",date)])
        if seq.exists():
            seq.next_number = seq.next_number + 1
        else:
            seq = self.create({"type":type,"company_id":company_id,"date":date})

        return seq.next_number