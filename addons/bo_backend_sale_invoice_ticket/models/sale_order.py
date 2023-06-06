from datetime import datetime, timedelta
import re
from odoo import models, fields, api, _
from odoo.http import request
import logging
from odoo.addons.bo_backend_sale_invoice_ticket.models.number_to_letter import to_word
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Order'

    @api.model
    def check_user_group(self):
        uid = request.session.uid
        # user = self.env['res.users'].sudo().search([('id', '=', uid)], limit=1)
        # if user.has_group('bo_denuncia_ec.group_denuncia_resp'):
        #     return True
        # else:
        #     return False
        return True

    def btn_ticket(self):
        return {
            'name': 'Imprimir Ticket',
            'tag': 'invoice_ticket',
            'type': 'ir.actions.client',
            'params': {
                'ticket_id': self.id,
                'model_id': 'sale.order'
            }
        }

    @api.model
    def ticket_data(self, ticket_id):
        # _logger.info("----- ticket_data -----")
        env = self.browse(ticket_id)
        if env:
            company_env = self.env['res.company'].browse(env.company_id.id)
            fields_company = {'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone',
                              'partner_id', 'country_id', 'state_id', 'city',
                              'tax_calculation_rounding_method', 'street', 'website_invoice_search'}
            company = company_env.read(fields_company)[0]

            fields_move = {'name', 'date_order', 'partner_id', 'total_venta_gravado',
                           'total_igv', 'total_venta_inafecto', 'total_venta_exonerada', 'total_venta_gratuito',
                           'total_descuento_global', 'total_descuentos', 'amount_total', 'user_id',
                           'payment_term_id'}
            sale = env.read(fields_move)[0]
            _logger.info(sale)

            # journal_env = self.env['account.journal'].browse(env.journal_id.id)
            # fields_journal = {'code', 'invoice_type_code_id'}
            # journal = journal_env.read(fields_journal)[0]

            partner_env = self.env['res.partner'].browse(env.partner_id.id)
            fields_partner = {'name', 'vat', 'street',
                              'phone', 'l10n_latam_identification_type_id'}
            partner = partner_env.read(fields_partner)[0]

            l10n_latam_env = self.env['l10n_latam.identification.type'].browse(
                partner_env.l10n_latam_identification_type_id.id)
            fields_l10n_latam = {'name', 'l10n_pe_vat_code'}
            l10n_latam = l10n_latam_env.read(fields_l10n_latam)[0]

            lines_env_ids = self.env['sale.order.line'].search(
                [('order_id', '=', env.id)])
            fields_line = {'product_id', 'product_uom_qty',
                           'price_unit', 'price_subtotal', 'display_type', 'price_total'}
            lines_ids = lines_env_ids.read(fields_line)

            # _logger.info("lines_ids: %s" % str(lines_ids))

            json_lines = []
            for line in lines_ids:
                # _logger.info("line: %s" % str(line))
                if line['display_type'] not in ['line_section', 'line_note']:
                    line.update({'product_name': line['product_id'][1]})
                    line.update({'quantity': line['product_uom_qty']})
                    json_lines.append(line)

            # _logger.info("company_env: %s" % str(company_env.read(fields_company)))

            # _logger.info("sale: %s" % str(sale))
            # _logger.info("move_env-read: %s" % str(move.read()))

            # _logger.info("company: %s" % company)

            data = {
                'name': sale['name'],
                'invoice_date': sale['date_order'],
                'payment_id': sale['payment_term_id'] and sale['payment_term_id'][1] or "Contado",
                # 'cashier': sale['user_id'][1],
                'cashier': sale.get("user_id", "-")[1] if sale.get("user_id", False) else "",
                # 'invoice_type_code': sale['invoice_type_code'],
                'total_venta_gravado': sale['total_venta_gravado'],
                'amount_igv': sale['total_igv'],
                'total_venta_inafecto': sale['total_venta_inafecto'],
                'total_venta_exonerada': sale['total_venta_exonerada'],
                'total_venta_gratuito': sale['total_venta_gratuito'],
                'total_descuento_global': sale['total_descuento_global'],
                'total_descuentos': sale['total_descuentos'],
                'amount_total': sale['amount_total'],
                # 'digest_value': sale['digest_value'],
                'son': to_word(sale['amount_total']).upper() + " SOLES",
                'partner': {
                    'name': partner['name'],
                    'vat_label': l10n_latam['name'],
                    'vat': partner['vat'],
                    'street': partner['street'],
                    'phone': partner['phone'],
                    'identification_type_id': partner['l10n_latam_identification_type_id'] and partner['l10n_latam_identification_type_id'][0] or self.env.ref("l10n_pe.it_NDTD").id
                },
                'orderlines': json_lines,
                'precision': {
                    'price': 2,
                    'money': 2,
                    'quantity': 3
                },
                'company': {
                    'email': company['email'],
                    'website': company['website'],
                    'website_invoice_search': company['website_invoice_search'],
                    'company_registry': company['company_registry'],
                    'contact_address': company['partner_id'][1],
                    'vat': company['vat'],
                    'vat_label': "RUC",
                    'name': company['name'],
                    'street': company['street'],
                    'state_id': company['state_id'] and company['state_id'][1] or "",
                    'city': company['city'],
                    'country_id': company['country_id'] and company['country_id'][1] or "",
                    'phone': company['phone'],
                    'logo':  '/web/image?model=res.company&id={}&field=logo'.format(company['id'])
                }
            }
            # Generar QR
            # qr_string = (
            #     data['company']['vat'],
            #     data['name'].split("-")[0],
            #     data['name'].split("-")[1],
            #     str(data['amount_igv']),
            #     str(data['amount_total']),
            #     l10n_latam['l10n_pe_vat_code']
            #     )
            # _logger.info("qr_string: %s" % str(qr_string))
            # data.update({'qr_string': "|".join(qr_string)})
            # _logger.info("data: %s" % str(data))
            return data
        else:
            return {}
