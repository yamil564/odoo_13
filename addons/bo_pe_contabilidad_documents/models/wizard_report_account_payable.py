from odoo import tools
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError , ValidationError

class WizardReportAccountPayable(models.TransientModel):
    _name = "wizard.report.account.payable"
    _description = "Reporte de Cuentas por Pagar a la Fecha"

    #######################################
    type_report = fields.Selection(
        selection=[('partner','Agrupado por Socio'),('account','Agrupado por Cuenta'),('account_partner','Agrupado por Cuenta-Socio'),('partner_account','Agrupado por Socio-Cuenta')],
        string="Criterio",default='partner',required=True)
    #######################################

    def get_query_account_payable(self):
        query="""
            select aml.id   
                from account_move_line as aml 
            join account_move am on am.id=aml.move_id
            join account_account acac on acac.id = aml.account_id 
            where acac.internal_type ='payable' and 
                am.state='posted' and 
                (aml.amount_residual != 0.00 or aml.amount_residual_currency != 0.00)"""

        return query



    def button_view_tree_account_payable(self):
        self.ensure_one()
        view = self.env.ref('bo_pe_contabilidad_documents.view_move_line_document_details_tree')

        query_2 = self.get_query_account_payable()
        self.env.cr.execute(query_2)
        records_2 = self.env.cr.dictfetchall()

        if records_2:
            if self.type_report=='partner':
                diccionario = {
                    'name': 'Cuentas por Pagar a la Fecha',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.move.line',
                    'view_id': view.id,
                    'views': [(view.id,'tree')],
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', [i['id'] for i in records_2] or [])],
                    'context':{
                        'search_default_filter_socio':1,
                        }}
                return diccionario

            elif self.type_report=='account':
                diccionario = {
                    'name': 'Cuentas por Pagar a la Fecha',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.move.line',
                    'view_id': view.id,
                    'views': [(view.id,'tree')],
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', [i['id'] for i in records_2] or [])],
                    'context':{
                        'search_default_filter_cuenta':1,
                        }
                }
                return diccionario

            elif self.type_report=='account_partner':
                diccionario = {
                    'name': 'Cuentas por Pagar a la Fecha',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.move.line',
                    'view_id': view.id,
                    'views': [(view.id,'tree')],
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', [i['id'] for i in records_2] or [])],
                    'context':{
                        'search_default_filter_cuenta':1,
                        'search_default_filter_socio':1,
                        }
                }
                return diccionario

            elif self.type_report=='partner_account':
                diccionario = {
                    'name': 'Cuentas por Pagar a la Fecha',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.move.line',
                    'view_id': view.id,
                    'views': [(view.id,'tree')],
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', [i['id'] for i in records_2] or [])],
                    'context':{
                        'search_default_filter_socio':1,
                        'search_default_filter_cuenta':1,
                        }
                }
                return diccionario