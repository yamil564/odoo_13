from odoo import models,fields

class BlogPost(models.Model):
    _inherit = "blog.post"
    type_text_editor = fields.Selection(selection=[("quill_editor","Quill"),("odoo_editor","Odoo")],string="Tipo de Editor de Texto",default="quill_editor")