# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'barcodes.barcode_events_mixin']

    def on_barcode_scanned(self, barcode):
        product = self.env['product.product'].search(
            ['|',('barcode', '=', barcode),('default_code', '=', barcode)]
            , limit=1)
        if product:
            order_lines = self.order_line.filtered(
                lambda r: r.product_id == product)
                
            if len(order_lines) > 0:
                seq = order_lines[0].sequence
            else: 
                seq = 500

            if order_lines:
                order_line = order_lines[0]
                qty = order_line.product_uom_qty
                order_line.product_uom_qty = qty + 1
                order_line.sequence = seq -1
            else:
                newId = self.order_line.new({
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': product.lst_price,
                    'sequence':seq-1
                })
                self.order_line += newId
                newId.product_id_change()
        else:
            raise UserError(
                _('El código de barras escaneado %s no esta relacionado a ningún producto.') %
                barcode)
