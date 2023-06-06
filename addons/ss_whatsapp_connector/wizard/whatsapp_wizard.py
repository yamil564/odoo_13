from odoo import api, fields, models
import html2text
import logging
_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    for_wsp = fields.Boolean(string="Para whatsapp")


class WhatsappSendMessage(models.TransientModel):
    _name = 'whatsapp.message.wizard'

    user_id = fields.Many2one('res.partner', string="Receptor")
    # mobile_number = fields.Char(related='user_id.mobile', required=True)
    mobile_number = fields.Char(
        readonly=True, default=lambda x: x.user_id.mobile)
    message = fields.Text(string="Message")
    model = fields.Char('mail.template.model_id')
    template_id = fields.Many2one('mail.template', 'Use template', index=True)

    send_to = fields.Selection(
        [('contact', 'Contacto'), ('other', 'Otro'), ], string='Enviar a', default="contact")
    phone_or_mobile = fields.Selection(
        [('phone', 'Teléfono'), ('mobile', 'Móvil'), ], string='Usar', default="mobile")

    recipient_name = fields.Char(string="Receptor")
    recipient_number = fields.Char(string="Número Whatsapp")

    @api.onchange('phone_or_mobile')
    def onchange_phone_or_mobile(self):
        if self.phone_or_mobile == 'mobile':
            self.mobile_number = self.user_id.mobile
        else:
            self.mobile_number = self.user_id.phone

    @api.onchange('recipient_name')
    def onchange_recipient_name(self):
        self.onchange_template_id_wrapper()

    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        res_id = self._context.get('active_id') or 1
        values = self.onchange_template_id(
            self.template_id.id, self.model, res_id)['value']
        for fname, value in values.items():
            setattr(self, fname, value)

    def onchange_template_id(self, template_id, model, res_id):
        if template_id:
            values = self.generate_email_for_composer(
                template_id, [res_id])[res_id]
        else:
            default_values = self.with_context(default_model=model, default_res_id=res_id).default_get(
                ['model', 'res_id', 'partner_ids', 'message'])
            values = dict((key, default_values[key]) for key in
                          ['body', 'partner_ids']
                          if key in default_values)
        values = self._convert_to_write(values)
        return {'value': values}

    def generate_email_for_composer(self, template_id, res_ids, fields=None):
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]
        if fields is None:
            fields = ['body_html']
        returned_fields = fields + ['partner_ids']
        values = dict.fromkeys(res_ids, False)
        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(
            template_id).generate_email(res_ids, fields=fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if
                                 template_values[res_id].get(field))
            res_id_values['message'] = html2text.html2text(
                res_id_values.pop('body_html', ''))
            values[res_id] = res_id_values

        return multi_mode and values or values[res_ids[0]]

    def send_message(self):
        # if self.message and self.mobile_number:
        _logger.info({'MOBILE NUMBER': self.mobile_number})
        message_string = ''
        message = ''
        line_message = self.message.split('\n')
        for msg in line_message:
            message = message+msg+'%0A'
        message = message[:(len(message) - 3)]
        # message = self.message.split(' ')
        message = message.split(' ')
        for msg in message:
            message_string = message_string + msg + '%20'
        message_string = message_string[:(len(message_string) - 3)]
        # number = self.user_id.mobile
        if self.send_to == 'other':
            number = self.recipient_number
        else:
            if self.phone_or_mobile == 'phone':
                number = self.user_id.phone
            else:
                number = self.user_id.mobile
        # link = "https://web.whatsapp.com/send?phone=" + number
        link = "https://api.whatsapp.com/send?phone=" + number

        # https://api.whatsapp.com/send?phone=920484302&text=HOla,%20mensaje%20de%20prueba
        send_msg = {
            'type': 'ir.actions.act_url',
            'url': link + "&text=" + message_string,
            'target': 'new',
            'res_id': self.id,
        }

        res_id = self._context.get('active_id') or 1
        record = self.env[self.model].browse(res_id)
        note_msg = """
            Mensaje Wstp enviado a: {} <br/>
            Mensaje: <br/>
            {}
        """.format(number, message_string.replace('%0A', '<br/>'))
        record.message_post(body=note_msg)

        return send_msg
