# -*- coding: utf-8 -*-
###############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-TODAY Odoo Peru(<http://www.odooperu.pe>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api
import os
import json

class CountryState(models.Model):
    _description = "Country state"
    _inherit = 'res.country.state'
    
    code = fields.Char('Country Code', size=9,
            help='The ISO country code in two chars.\n'
            'You can use this field for quick search.')
    state_id = fields.Many2one('res.country.state', 'Departamento')
    state_name = fields.Char(related="state_id.name")
    province_id = fields.Many2one('res.country.state', 'Provincia')
    province_name = fields.Char(related = "province_id.name")
    
    
    # @api.model
    # def default_get(self, fields):
    #     res = super(CountryState, self).default_get(fields)
    #     return res
        
    
    # @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('ubigeo_search', False):
                if record.code != False and record.country_id != False and record.state_id !=  False and record.province_id != False:
                    if record.country_id.id == 173:
                        name = "[{}] {} > {} > {}".format(record.code,record.state_id.name,record.province_id.name,record.name)
                        result.append((record.id, name))
            else:
                result.append((record.id, record.name))
                
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self.env.context.get('ubigeo_search', False):
            name_list = name.split(" ")
            name_list = [name.strip() for name in name_list]
            records = self
            for name in name_list:
                records = records.search(["|","|","|",("code","ilike",name),("name","ilike",name),("state_name","ilike",name),("province_name",'ilike',name),("state_id","!=",False),("province_id",'!=',False)],limit=25)
            return records.name_get()
        else:
            return super(CountryState,self).name_search(name,args,operator,limit)
    
    

    
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

