# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid


class AccountInvoice(models.Model):
    _inherit = "account.move"

    report_token = fields.Char("Access Token")
    text_message = fields.Text("Message", compute="get_message_detail_so")
    invoice_url = fields.Text("Url")

    def action_quotation_send_wp(self):

        if not self.partner_id.mobile:
            raise UserError("Customer Mobile Number Not Exist !")

        '''
        This function opens a window to compose an email, with the edi Invoice template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        template = self.env.ref(
            'sh_whatsapp_integration.email_template_edi_invoice_custom')
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'account.move',
            'active_model': 'account.move',
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
            url = '/download/inv/' + '%s?access_token=%s' % (
                self.id,
                self._get_token()
            )
        return url

    @api.depends('partner_id', 'currency_id', 'company_id')
    def get_message_detail_so(self):
        if self:
            for inv in self:
                if inv.type in ['out_invoice', 'out_refund']:
                    txt_message = ""
                    if inv.company_id.invoice_order_information_in_message and inv.partner_id and inv.currency_id and inv.company_id:
                        txt_message += "Estimado " + \
                            str(inv.partner_id.name)+","+"%0A%0A"

                        if inv.name and inv.state != "draft":
                            txt_message += "A continuación Ud. puede ver los detalles de su comprobante " + \
                                '*'+str(inv.name)+'*'+""
                        else:
                            txt_message += "A continuación Ud. puede ver los detalles de su comprobante "+""
                        txt_message += " Con un monto de "+'*' + str(inv.currency_id.symbol) + "" + str('{:.2f}'.format(inv.amount_total))+'*' + " Emitido por la empresa "+inv.company_id.name+"."
                        if inv.state == "paid":
                            txt_message += "Esta factura ya está pagada."+"%0A%0A"
                        else:
                            txt_message += "Por favor, remita el pago a la mayor brevedad posible."+"%0A%0A"
                    if inv.company_id.invoice_product_detail_in_message:
                        txt_message += "Con los siguientes detalles."+"%0A"
                        if inv.invoice_line_ids:
                            for invoices_line in inv.invoice_line_ids:
                                if invoices_line.product_id:
                                    if invoices_line.product_id and invoices_line.quantity and invoices_line.price_unit:
                                        txt_message += "%0A"+"*"+invoices_line.product_id.display_name+"*"+"%0A"+"*Cantidad:* " + \
                                            str(invoices_line.quantity)+"%0A"+"*Precio:* "+str(invoices_line.move_id.currency_id.symbol)+" "+str('{:.2f}'.format(invoices_line.price_unit))+"%0A"
                                    else:
                                        txt_message += "%0A"+"*"+invoices_line.name+"*"+"%0A"+"*Cantidad:* "+str(invoices_line.quantity)+"%0A"+"*Price:* "+str(invoices_line.move_id.currency_id.symbol)+""+str('{:.2f}'.format(invoices_line.price_unit))+"%0A"
                                    if invoices_line.discount > 0.00:
                                        txt_message += "*Descuento:* " + \
                                            str('{:.2f}'.format(invoices_line.discount)) + \
                                            "%25"+"%0A"
                                    txt_message += "________________________"+"%0A"
                        txt_message += "*"+"Monto Grabado:"+"*"+"%20" + str(inv.currency_id.symbol)+ " " + str('{:.2f}'.format(inv.amount_untaxed))+"%0A"
                        txt_message += "*"+"Impuestos:"+"*"+"%20" + str(inv.currency_id.symbol)+ " " + str('{:.2f}'.format(inv.amount_tax))+"%0A"
                        txt_message += "*"+"Monto Total:"+"*"+"%20" + str(inv.currency_id.symbol)+ " " + str('{:.2f}'.format(inv.amount_total))+"%0A"
                        

                    if inv.company_id.inv_send_pdf_in_message:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        inv_url = "%0A%0A Puede Descargar su comprobante en el siguiente enlace: %0A" + base_url+inv.get_download_report_url()
                        self.write({'invoice_url': base_url+inv.get_download_report_url()})
                        txt_message += "%0A%0A ¡¡¡Muchas Gracias por su preferencia!!! %0A"
                        txt_message += inv_url
                    if inv.company_id.invoice_signature and inv.env.user.sign:
                        txt_message += "%0A%0A%0A"+str(inv.env.user.sign)
                    inv.text_message = txt_message.replace('&', '%26')

                elif inv.type in ['in_invoice', 'in_refund']:
                    txt_message = ""
                    if inv.company_id.invoice_order_information_in_message and inv.partner_id and inv.currency_id and inv.company_id:
                        txt_message += "Estimado " + \
                            str(inv.partner_id.name)+","+"%0A%0A"
                        if inv.name and inv.state != "draft":
                            txt_message += "A continuación Ud. puede ver los detalles de su comprobante " + \
                                '*'+str(inv.name)+'*'+""
                        else:
                            txt_message += "A continuación Ud. puede ver los detalles de su comprobante "+""
                        txt_message += " Con un monto de "+'*' + str(inv.currency_id.symbol) + "" + str('{:.2f}'.format(inv.amount_total))+'*' + " Emitido por la Empresa "+inv.company_id.name+"."
                        if inv.state == "paid":
                            txt_message += "Esta factura ya está pagada."+"%0A%0A"
                        else:
                            txt_message += "Por favor, remita el pago a la mayor brevedad posible."+"%0A%0A"
                    if inv.company_id.invoice_product_detail_in_message:
                        txt_message += "Con los siguientes detalles."+"%0A"
                        if inv.invoice_line_ids:
                            for invoices_line in inv.invoice_line_ids:
                                if invoices_line.product_id:
                                    if invoices_line.product_id and invoices_line.quantity and invoices_line.price_unit:
                                        txt_message += "%0A"+"*"+invoices_line.product_id.display_name+"*"+"%0A"+"*Cantidad:* " + str(invoices_line.quantity)+"%0A"+"*Precio:* "+str(invoices_line.move_id.currency_id.symbol)+""+str('{:.2f}'.format(invoices_line.price_unit))+"%0A"
                                    else:
                                        txt_message += "%0A"+"*"+invoices_line.name+"*"+"%0A"+"*Cantidad:* "+str(invoices_line.quantity)+"%0A"+"*Precio:* "+str(invoices_line.move_id.currency_id.symbol)+""+str('{:.2f}'.format(invoices_line.price_unit))+"%0A"

                                    if invoices_line.discount > 0.00:
                                        txt_message += "*Descuento:* " + str('{:.2f}'.format(invoices_line.discount)) + "%25"+"%0A"
                                    txt_message += "________________________"+"%0A"
                        txt_message += "*"+"Monto Grabado:"+"*"+"%20" + str(inv.currency_id.symbol)+ " " + str('{:.2f}'.format(inv.amount_untaxed))+"%0A"
                        txt_message += "*"+"Impuestos:"+"*"+"%20" + str(inv.currency_id.symbol)+ " " + str('{:.2f}'.format(inv.amount_tax))+"%0A"
                        txt_message += "*"+"Monto Total:"+"*"+"%20" + str(inv.currency_id.symbol) + "" + str('{:.2f}'.format(inv.amount_total))+"%0A"
                            
                    if inv.company_id.inv_send_pdf_in_message:
                        base_url = self.env['ir.config_parameter'].sudo(
                        ).get_param('web.base.url')
                        inv_url = "%0A%0A Puede Descargar su comprobante en el siguiente enlace : %0A" + base_url+inv.get_download_report_url()
                        self.write({'invoice_url': base_url+inv.get_download_report_url()})
                        txt_message += "%0A%0A ¡¡¡Muchas Gracias por su preferencia!!! %0A"
                        txt_message += inv_url
                    if inv.company_id.invoice_signature and inv.env.user.sign:
                        txt_message += "%0A%0A%0A"+str(inv.env.user.sign)
                    inv.text_message = txt_message.replace('&', '%26')
                else:
                    inv.text_message = ''

    def send_by_whatsapp_direct_to_ci(self):
        if self:
            for rec in self:
                if rec.company_id.invoice_display_in_message:
                    message = ''
                    if rec.text_message:
                        message = str(self.text_message).replace(
                            '*', '').replace('_', '').replace('%0A', '<br/>').replace('%20', ' ').replace('%26', '&')
                    self.env['mail.message'].create({
                                                    'partner_ids': [(6, 0, rec.partner_id.ids)],
                                                    'model': 'account.move',
                                                    'res_id': rec.id,
                                                    'author_id': self.env.user.partner_id.id,
                                                    'body': message or False,
                                                    'message_type': 'comment',
                                                    })

                if rec.partner_id.mobile and rec.text_message:
                    return {
                        'type': 'ir.actions.act_url',
                        'url': "https://web.whatsapp.com/send?l=&phone="+rec.partner_id.mobile+"&text=" + rec.text_message,
                        'target': 'new',
                        'res_id': rec.id,
                    }
                else:
                    raise UserError("Partner Mobile Number Not Exist")
