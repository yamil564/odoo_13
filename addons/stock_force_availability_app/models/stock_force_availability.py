# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockPicking(models.Model):
	_inherit = "stock.picking"

	def one_click_force_avail(self):

		for picking in self:
			for order in picking.move_ids_without_package:

				if order.product_id.type == "product" and order.product_id.tracking == "none":

					order.update({'quantity_done' : order.product_uom_qty })

				elif order.product_id.type == "product" and order.product_id.tracking == "lot":
					unique_lot_id = self.env['stock.production.lot'].sudo().create({'product_id' : order.product_id.id,
																					'company_id' : picking.env.user.company_id.id,
																					'product_qty':order.product_uom_qty})

					stcok_move_line = self.env['stock.move.line'].sudo().create({'lot_id' : unique_lot_id.id , 'qty_done' : order.product_uom_qty ,
														'product_uom_id' : order.product_id.uom_id.id  , 'location_id' : picking.location_id.id ,'picking_id' : picking.id,
														'location_dest_id' : picking.location_dest_id.id , 'move_id': order.id , 'product_id' : order.product_id.id})

				elif order.product_id.type == "product" and order.product_id.tracking == "serial":

					lot_range = range(int(order.product_uom_qty))

					for create_lot in lot_range:
						
						unique_lot_id = self.env['stock.production.lot'].sudo().create({'product_id' : order.product_id.id,
																						 'company_id' : picking.env.user.company_id.id,
																						 'product_qty':order.product_uom_qty})
						
						order.update({'move_line_ids' : [(0,0,{ 'lot_id' : unique_lot_id.id , 'qty_done' : float(1.000) , 
														'product_uom_id' : order.product_id.uom_id.id  , 'location_id' : picking.location_id.id ,'picking_id' : picking.id,
														'location_dest_id' : picking.location_dest_id.id , 'move_id': order.id , 'product_id' : order.product_id.id } )] })


		picking.update({'state': 'assigned'})


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: