from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning, RedirectWarning
import re
import logging


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"


    property_account_payable_fees_id=fields.Many2one('account.account.template',
        string="Cuenta Recibo Honorarios por Pagar")

    property_account_payable_me_fees_id=fields.Many2one('account.account.template',
        string="Cuenta Recibo Honorarios por Pagar ME")

    property_account_receivable_me_id=fields.Many2one('account.account.template',
        string="Cuenta por cobrar ME")
    
    property_account_payable_me_id=fields.Many2one('account.account.template',
        string="Cuenta por pagar ME")


    def generate_properties(self, acc_template_ref, company):

        res = super(AccountChartTemplate,self).generate_properties()

        self.ensure_one()

        PropertyObj = self.env['ir.property']

        todo_list = [
            ('property_account_receivable_me_id', 'res.partner', 'account.account'),
            ('property_account_payable_me_id', 'res.partner', 'account.account'),
            ('property_account_payable_fees_id', 'res.partner', 'account.account'),
            ('property_account_payable_me_fees_id', 'res.partner', 'account.account'),
        ]
        for record in todo_list:
            account = getattr(self, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record[0]),
                    ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                vals = {
                    'name': record[0],
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }
                properties = PropertyObj.search([('name', '=', record[0]), ('company_id', '=', company.id)])
                if properties:
                    #the property exist: modify it
                    properties.write(vals)
                else:
                    #create the property
                    PropertyObj.create(vals)

        return res