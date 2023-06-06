
from odoo import models

class Picking(models.Model):
    _inherit = "stock.picking"

    def action_done(self):
        for pick in self:
            res = super(Picking, pick).action_done()
            if res:
                picking_type_id = pick.picking_type_id
                if picking_type_id.code in ['internal', 'incoming']:
                    stock_move = pick.move_ids_without_package.filtered(
                        lambda sm: (
                                sm.state in ['done']
                        )
                    )

                    domain = [('product_id', 'in', stock_move.product_id.ids),
                              ('location_id', '=', pick.location_dest_id.id),
                              ('state', 'in', ['draft', 'waiting', 'confirmed', 'partially_available', 'assigned']),
                              ('sale_line_id', '!=', False)]

                    stock_moves_sale = self.env['stock.move'].search(domain, order='priority DESC, date_expected asc')
                    for move in stock_moves_sale:
                        available_qty = self.env['stock.quant']._get_available_quantity(move.product_id,
                                                                                        move.location_id)

                        if available_qty and move.picking_id and move.picking_id.picking_type_id.code in ['outgoing']:
                            if move.picking_id.state in ['waiting', 'confirmed'] and move.picking_id.show_check_availability:
                                move.picking_id.action_assign()
                            if move.picking_id.state == 'draft':
                                move.picking_id.action_confirm()
                                if move.picking_id.show_check_availability:
                                    move.picking_id.action_assign()
                            if move.picking_id.state == 'assigned' and move.picking_id.show_check_availability:
                                move.picking_id.action_assign()

                        if not available_qty:
                            break
