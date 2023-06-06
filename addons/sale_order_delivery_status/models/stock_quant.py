
from odoo import models

class StockQuant(models.Model):
    _inherit = "stock.quant"

    # If product is available for picking. The Picking will be assigned with date_deadline priority
    def _set_inventory_quantity(self):
        if not self._is_inventory_mode():
            return
        super(StockQuant, self)._set_inventory_quantity()
        for quant in self:
            available_qty = self.env['stock.quant']._get_available_quantity(quant.product_id,
                                                                            quant.location_id)
            if available_qty:
                domain = [('product_id', '=', quant.product_id.id),
                          ('location_id', '=', quant.location_id.id),
                          ('state', 'in', ['draft', 'waiting', 'confirmed', 'partially_available', 'assigned']),
                          ('sale_line_id', '!=', False)]
                moves = self.env['stock.move'].search(domain, order='priority DESC, date_expected asc')
                for move in moves:
                    available_qty = self.env['stock.quant']._get_available_quantity(quant.product_id,
                                                                                    quant.location_id)
                    if available_qty and move.picking_id and move.picking_id.picking_type_id.code in ['outgoing']:
                        if move.picking_id.state == 'draft':
                            move.picking_id.action_confirm()
                            if move.picking_id.show_check_availability:
                                move.picking_id.action_assign()

                        elif move.picking_id.show_check_availability:
                            move.picking_id.action_assign()
                    if not available_qty:
                        break

class Inventory(models.Model):
    _inherit = "stock.inventory"

    def _action_done(self):
        res = super(Inventory, self)._action_done()
        if res:
            for line in self.line_ids:
                available_qty = self.env['stock.quant']._get_available_quantity(line.product_id, line.location_id)
                if available_qty:
                    domain = [('product_id', '=', line.product_id.id),
                              ('location_id', '=', line.location_id.id),
                              ('state', 'in', ['draft', 'waiting', 'confirmed', 'partially_available', 'assigned']),
                              ('sale_line_id', '!=', False)]
                    moves = self.env['stock.move'].search(domain, order='priority DESC, date_expected asc')
                    for move in moves:
                        available_qty = self.env['stock.quant']._get_available_quantity(line.product_id,
                                                                                        line.location_id)
                        if available_qty and move.picking_id and move.picking_id.picking_type_id.code in ['outgoing']:
                            if move.picking_id.state == 'draft':
                                move.picking_id.action_confirm()
                                if move.picking_id.show_check_availability:
                                    move.picking_id.action_assign()

                            elif move.picking_id.show_check_availability:
                                move.picking_id.action_assign()
                        if not available_qty:
                            break
