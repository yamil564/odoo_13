from odoo import models, fields, api, _
from odoo.exceptions import UserError

import uuid
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def contacts_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_user_id': self.id,
                'default_model': self._name
            },
        }


class WhatsappCrm(models.Model):
    _inherit = 'crm.lead'

    def crm_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_user_id': self.partner_id.id,
                'default_model': self._name
            },
        }


class WhatsappInvoice(models.Model):
    _inherit = 'account.move'


    invoice_url = fields.Text("Url", compute="get_download_report_url")

    def get_download_report_url(self):
        url = ''
        if self.id:
            self.ensure_one()
            url = self.get_portal_url()
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')

        self.invoice_url = base_url + url

    def invoice_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_template_id': self.env.ref('ss_whatsapp_connector.whatsapp_invoice_template').id,
                'default_model': self._name
            },
        }


class WhatsappPurchase(models.Model):
    _inherit = 'purchase.order'

    def purchase_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_template_id': self.env.ref('ss_whatsapp_connector.whatsapp_purchase_template').id,
                'default_model': self._name
            },
        }


class WhatsappSale(models.Model):
    _inherit = 'sale.order'

    sale_url = fields.Text("Url", compute="get_download_report_url")

    def get_download_report_url(self):
        url = ''
        if self.id:
            self.ensure_one()
            url = self.get_portal_url()
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')

        self.sale_url = base_url + url
        # return url

    def sale_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_template_id': self.env.ref('ss_whatsapp_connector.whatsapp_sales_template').id,
                'default_model': self._name
            },
        }


class WhatsappPicking(models.Model):
    _inherit = 'stock.picking'

    def stock_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_user_id': self.partner_id.id,
                'default_model': self._name
            },
        }


class WhatsappPayment(models.Model):
    _inherit = 'account.payment'

    def payment_whatsapp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Whatsapp Message'),
            'res_model': 'whatsapp.message.wizard',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_user_id': self.partner_id.id,
                'default_model': self._name
            },
        }
