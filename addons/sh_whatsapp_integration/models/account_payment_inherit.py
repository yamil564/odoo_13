# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid


class AccountInvoice(models.Model):
    _inherit = "account.payment"

    text_message = fields.Text("Message", compute="get_message_detail_ap")
    report_token = fields.Char("Access Token")
    payment_url = fields.Text("Url")

    def action_quotation_send_wp(self):

        if not self.partner_id.mobile:
            raise UserError("Partner Mobile Number Not Exist !")

        '''
        This function opens a window to compose an email, with the edi Payment template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        template = self.env.ref(
            'sh_whatsapp_integration.mail_template_data_payment_receipt_custom')
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'account.payment',
            'active_model': 'account.payment',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'default_is_wp': True,
        })

        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(
                ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_template(
                    template.lang, ctx['default_model'], ctx['default_res_id'])

        self = self.with_context(lang=lang)

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.name:
            return 'Payment Receipt %s' % (self.name)
        else:
            return 'Payment Receipt'

    def _get_token(self):
        """ Get the current record access token """
        if self.report_token:
            return self.report_token
        else:
            report_token = str(uuid.uuid4())
            self.write({'report_token': report_token})
            return report_token

    def get_download_report_url(self):
        url = ''
        if self.id:
            self.ensure_one()
            url = '/download/pay/' + '%s?access_token=%s' % (
                self.id,
                self._get_token()
            )
        return url

    @api.depends('partner_id', 'currency_id', 'company_id')
    def get_message_detail_ap(self):
        for inv in self:
            txt_message = ""
            if inv and inv.payment_type == 'inbound':
                txt_message = ""
                if inv.company_id.invoice_order_information_in_message and inv.partner_id and inv.currency_id and inv.company_id:
                    txt_message += "Estimado " + \
                        str(inv.partner_id.name)+","+"%0A%0A"
                    txt_message += "Acontinuación Ud. puede ver los datos de su pago "+'*' + \
                        str('{:.2f}'.format(inv.amount))+""+str(inv.currency_id.symbol)+'*'+""
                    txt_message += " Emitido por la empresa  "+'*'+str(inv.journal_id.name)+'*'
                    if inv.name:
                        txt_message += ". Referencia No :"+str(inv.name)
                    txt_message += "%0A%0A" + "¡¡¡Gracias por su preferencia!!!."+"%0A%0A"

                if inv.company_id.inv_send_pdf_in_message:
                    base_url = self.env['ir.config_parameter'].sudo(
                    ).get_param('web.base.url')
                    inv_url = "%0A%0A Puede Descargar su comprobante en el siguiente enlace : %0A" + \
                        base_url+inv.get_download_report_url()
                    txt_message += inv_url
                    self.write(
                        {'payment_url': base_url+inv.get_download_report_url()})

                if inv.company_id.invoice_signature and inv.env.user.sign:
                    txt_message += "%0A%0A"+str(inv.env.user.sign)
            inv.text_message = txt_message.replace('&', '%26')

            if inv and inv.payment_type == 'outbound':
                txt_message = ""
                if inv.company_id.invoice_order_information_in_message and inv.partner_id and inv.currency_id and inv.company_id:
                    txt_message += "Estimado " + \
                        str(inv.partner_id.name)+","+"%0A%0A"
                    txt_message += "Acontinuación Ud. puede ver los datos de su pago "+'*' + \
                        str('{:.2f}'.format(inv.amount))+""+str(inv.currency_id.symbol)+'*'+""
                    txt_message += " Emitido por la empresa  "+'*'+str(inv.journal_id.name)+'*'
                    if inv.name:
                        txt_message += ". Referencia No :" + \
                            str(inv.name)+"%0A%0A"
                    txt_message += "¡¡¡Gracias por su preferencia!!!."+"%0A%0A"

                if inv.company_id.inv_send_pdf_in_message:
                    base_url = self.env['ir.config_parameter'].sudo(
                    ).get_param('web.base.url')
                    inv_url = "%0A%0A Puede Descargar su comprobante en el siguiente enlace : %0A" + \
                        base_url+inv.get_download_report_url()
                    txt_message += inv_url
                    self.write(
                        {'payment_url': base_url+inv.get_download_report_url()})

                if inv.company_id.invoice_signature and inv.env.user.sign:
                    txt_message += "%0A%0A"+str(inv.env.user.sign)
            inv.text_message = txt_message.replace('&', '%26')

    #@api.multi

    def send_by_whatsapp_direct_to_ci(self):
        if self:
            for rec in self:
                if rec.company_id.invoice_display_in_message:
                    message = ''
                    if rec.text_message:
                        message = str(rec.text_message).replace(
                            '*', '').replace('_', '').replace('%0A', '<br/>').replace('%20', ' ').replace('%26', '&')
                    self.env['mail.message'].create({
                                                    'partner_ids': [(6, 0, rec.partner_id.ids)],
                                                    'model': 'account.payment',
                                                    'res_id': rec.id,
                                                    'author_id': self.env.user.partner_id.id,
                                                    'body': message or False,
                                                    'message_type': 'comment',
                                                    })

                if self.partner_id.mobile:
                    return {
                        'type': 'ir.actions.act_url',
                        'url': "https://web.whatsapp.com/send?l=&phone="+self.partner_id.mobile+"&text=" + self.text_message,
                        'target': 'new',
                        'res_id': self.id,
                    }
                else:
                    raise UserError("Partner Mobile Number Not Exist")
