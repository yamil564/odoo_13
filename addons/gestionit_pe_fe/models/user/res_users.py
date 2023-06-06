# -*- coding: utf-8 -*-
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)

class Users(models.Model):
    _inherit = "res.users"

    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Almacenes permitidos')

    
    @api.model
    def create(self, values):
        company_ids = values.get("company_ids",[])
        if len(company_ids) > 0:
            warehouse_ids = self.env["stock.warehouse"].search([("company_id","in",company_ids[0][2])]).ids
            values["warehouse_ids"] = [(6,0,warehouse_ids)]
        return super(Users, self).create(values)
    
    
    def write(self, values):
        # _logger.info(self._context)
        company_ids = values.get("company_ids",[])
        if self._context.get("params",False):
            if self._context["params"].get("model",False) != "res.users":
                return super(Users, self).write(values)


        # if len(company_ids) > 0:
        #     _logger.info(company_ids)
        #     warehouse_ids = self.env["stock.warehouse"].search([("company_id","in",company_ids[0][2])]).ids
        #     values["warehouse_ids"] = [(6,0,warehouse_ids)]
        return super(Users, self).write(values)
        
    