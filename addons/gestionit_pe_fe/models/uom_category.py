from odoo import models,fields,api

class UoMCategory(models.Model):
    _inherit = 'uom.category'

    measure_type = fields.Selection(selection_add=[('energy','Default Energy'),
                                                    ('area','Default Area')])
    