# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.addons import decimal_precision as dp

class ReportStockMoveValuation(models.Model):
    _name = 'report.stock.move.valuation'
    _auto = False
    _description = 'Stock move valuation report'
    _order = "product_id, location_id, date"
    _rec_name = "picking_id"

    move_id = fields.Many2one('stock.move', string="Movimiento")
    type = fields.Selection(selection=[('in','Entrada'),('out','Salida')], string="Ind. ES")
    account_move_name = fields.Char(string="Reg. Contable")
    invoice_number = fields.Char(string="Nro. Documento")
    origin = fields.Char(string="Referencia")
    picking_id = fields.Many2one('stock.picking', string="Cod. Inventario")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Detalle de Compra")
    purchase_id = fields.Many2one('purchase.order', related="purchase_line_id.order_id", string="Compra", readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string="Detalle de Venta")
    sale_id = fields.Many2one('sale.order', related="sale_line_id.order_id", string="Venta", readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', readonly=True)
    categ_id = fields.Many2one('product.category', string='Categoria', related='product_id.categ_id', readonly=True)
    uom_id = fields.Many2one('uom.uom', string="UoM")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    quantity = fields.Float(string="Cantidad Ingreso", digits=dp.get_precision('Product Unit of Measure'))
    location_id = fields.Many2one('stock.location', string="Ubicacion")
    usage = fields.Selection(related='location_id.usage', string="Tipo de Ubicacion", readonly=True)
    qty_in = fields.Float(string="Cantidad Entrada", digits=dp.get_precision('Product Unit of Measure'))
    cost_in = fields.Float(string="Cost. Unit. Entrada", digits=dp.get_precision('Product Price'))
    total_cost_in = fields.Float(string="Total Costo Entrada", digits=dp.get_precision('Product Price'))
    qty_out = fields.Float(string="Cantidad Salida", digits=dp.get_precision('Product Unit of Measure'))
    cost_out = fields.Float(string="Cost. Unit. Salida", digits=dp.get_precision('Product Price'))
    total_cost_out = fields.Float(string="Total Costo Salida", digits=dp.get_precision('Product Price'))
    
    ###########################################################################################
    qty = fields.Float(string="Saldo Cantidad", digits=dp.get_precision('Product Unit of Measure'))
    unit_cost = fields.Float(string="Cost. Promedio", digits=dp.get_precision('Product Price'))
    value = fields.Float(string="Saldo Costo Total", digits=dp.get_precision('Product Price'))
    stock_value = fields.Float(string="Valor (Valoración del inventario)")
    ###########################################################################################
    
    date = fields.Datetime(string="Fec. Movimiento")
    date_expected = fields.Datetime(string="Fec. Prevista")
    picking_type_id = fields.Many2one('stock.picking.type',string="Tipo de operacion")
    warehouse_id = fields.Many2one('stock.warehouse', string="Almacén")
    inventory_id = fields.Many2one('stock.inventory', string="Cod. Inventario de Ajuste")
    value_difference=fields.Float(string="Diferencia", compute='_compute_campo_value_difference')
    # invoice_id = fields.Many2one('account.invoice', string="Factura", compute="_compute_invoice_search", store=True)

    @api.one
    @api.depends('value','stock_value')
    def _compute_campo_value_difference(self):
        self.value_difference=self.value - self.stock_value

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW report_stock_move_valuation AS (
          SELECT
  *,
  stock.qty * stock.unit_cost AS stock_value 
FROM
  (
  SELECT
  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      mov.id_move ELSE mov.id_move *-1
    END AS ID,
    mov.id_move AS move_id,
    mov.picking_id AS picking_id,
    mov.purchase_line_id AS purchase_line_id,
    mov.sale_line_id AS sale_line_id,
    mov.product AS product_id,
    mov.uom AS uom_id,
    mov.company_id AS company_id,
    mov.referencia AS origin,

  CASE
      
      WHEN mov.purchase_line_id IS NOT NULL THEN
      (
      SELECT
        array_to_string( ARRAY_AGG ( account_invoice.move_name ORDER BY account_invoice.move_name ), ', ' ) 
      FROM
        account_invoice
        JOIN account_invoice_line ON account_invoice_line.invoice_id = account_invoice.ID 
      WHERE
        account_invoice_line.purchase_line_id = mov.purchase_line_id 
      ) 
      WHEN mov.id_move IS NOT NULL THEN
      (
      SELECT
        array_to_string( ARRAY_AGG ( account_move.NAME ORDER BY account_move.NAME ), ', ' ) 
      FROM
        account_move 
      WHERE
        account_move.stock_move_id = mov.id_move 
        ) ELSE (
      SELECT
        array_to_string( ARRAY_AGG ( account_invoice.move_name ORDER BY account_invoice.move_name ), ', ' ) 
      FROM
        account_invoice 
      WHERE
        mov.referencia = account_invoice.NUMBER 
      ) 
    END AS account_move_name,
  

  CASE
      
      WHEN mov.sale_line_id IS NOT NULL THEN
      (
      SELECT
        array_to_string( ARRAY_AGG ( account_invoice.NUMBER ORDER BY account_invoice.NUMBER ), ', ' ) 
      FROM
        sale_order_line
        INNER JOIN sale_order_line_invoice_rel ON sale_order_line_invoice_rel.order_line_id = sale_order_line.
        ID INNER JOIN account_invoice_line ON sale_order_line_invoice_rel.invoice_line_id = account_invoice_line.
        ID INNER JOIN account_invoice ON account_invoice_line.invoice_id = account_invoice.ID 
      WHERE
        sale_order_line.ID = mov.sale_line_id 
        AND account_invoice_line.product_id = mov.product 
      ) 
      WHEN mov.purchase_line_id IS NOT NULL THEN
      (
      SELECT
        array_to_string( ARRAY_AGG ( account_invoice.NUMBER ORDER BY account_invoice.NUMBER ), ', ' ) 
      FROM
        purchase_order_line
        INNER JOIN account_invoice_line ON account_invoice_line.purchase_line_id = purchase_order_line.
        ID INNER JOIN account_invoice ON account_invoice_line.invoice_id = account_invoice.ID 
      WHERE
        purchase_order_line.ID = mov.purchase_line_id 
        AND account_invoice_line.product_id = mov.product 
      ) 
      WHEN mov.inventory_id IS NOT NULL THEN
      'AJUSTE' ELSE (
      SELECT
        array_to_string( ARRAY_AGG ( DISTINCT ( account_invoice.NUMBER ) ORDER BY account_invoice.NUMBER ), ', ' ) 
      FROM
        account_invoice
        INNER JOIN account_invoice_line ON account_invoice_line.invoice_id = account_invoice.
        ID INNER JOIN stock_picking ON stock_picking.origin = account_invoice.NUMBER 
      WHERE
        stock_picking.ID = mov.picking_id 
        AND account_invoice_line.product_id = mov.product 
      ) 
    END AS invoice_number,


  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      'in' ELSE'out' 
    END AS TYPE,
  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      mov.cantidad ELSE - mov.cantidad 
    END AS quantity,
  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      mov.ubicacion ELSE mov.origen 
    END AS location_id,
  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      mov.cantidad ELSE NULL 
    END AS qty_in,
  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      mov.price_unit ELSE NULL 
    END AS cost_in,
  CASE
      
      WHEN ubicacion.ID = mov.ubicacion THEN
      ( mov.price_unit * mov.cantidad ) ELSE NULL 
    END AS total_cost_in,
  CASE
      
      WHEN ubicacion.ID = mov.origen THEN
      mov.cantidad ELSE NULL 
    END AS qty_out,
  CASE
      
      WHEN ubicacion.ID = mov.origen THEN
      - mov.price_unit ELSE NULL 
    END AS cost_out,
  CASE
      
      WHEN ubicacion.ID = mov.origen THEN
      - ( mov.price_unit * mov.cantidad ) ELSE NULL 
    END AS total_cost_out,
    (
    SELECT SUM
      ( totales.cantidad ) 
    FROM
      (
      SELECT
      CASE
          
        WHEN
          stock_move.location_dest_id = ubicacion.ID THEN
            stock_move.product_qty ELSE - stock_move.product_qty 
            END AS cantidad 
        FROM
          stock_move 
        WHERE
          STATE = 'done' 
          AND stock_move.product_id = mov.product 
          AND stock_move.DATE <= mov.DATE 
          AND ( stock_move.location_id = ubicacion.ID OR stock_move.location_dest_id = ubicacion.ID ) 
        ) AS totales 
      ) AS qty,
      (
      SELECT
        product_price_history.COST 
      FROM
        product_price_history 
      WHERE
        product_price_history.product_id = mov.product 
        AND product_price_history.company_id = mov.company_id 
        AND product_price_history.datetime <= mov.DATE 
      ORDER BY
        product_price_history.datetime DESC,
        product_price_history.ID DESC 
        LIMIT 1 
      ) AS unit_cost,
      (
      SELECT SUM
        ( total_costo.costo_prom ) 
      FROM
        (
        SELECT
        CASE
            
          WHEN
            stock_move.location_dest_id = ubicacion.ID THEN
              stock_move.
            VALUE
              ELSE stock_move.
            VALUE
              
            END AS costo_prom 
          FROM
            stock_move 
          WHERE
            STATE = 'done' 
            AND stock_move.product_id = mov.product 
            AND stock_move.DATE <= mov.DATE 
            AND ( stock_move.location_id = ubicacion.ID OR stock_move.location_dest_id = ubicacion.ID ) 
          ) AS total_costo 
        ) AS 
      VALUE
        ,
        mov.DATE AS DATE,
        mov.date_expected AS date_expected,
        mov.picking_type_id AS picking_type_id,
        mov.warehouse_id AS warehouse_id,
        mov.inventory_id AS inventory_id 
      FROM
        stock_location AS ubicacion
        JOIN (
        
        SELECT
          sm.ID AS id_move,
          sm.picking_id,
          sm.purchase_line_id,
          sm.sale_line_id,
          sm.origin AS referencia,
          sm.product_id AS product,
          sm.product_uom AS uom,
          sm.location_id AS origen,
          sm.location_dest_id AS ubicacion,
          sm.product_qty AS cantidad,
          sm.product_uom_qty AS cantidad_uom,
          sm.price_unit,
          sm.DATE,
          sm.date_expected,
          sm.picking_type_id,
          sm.company_id,
          sm.warehouse_id,
          sm.inventory_id 
        FROM
          stock_move sm
          JOIN stock_location ori_loc ON ori_loc.ID = sm.location_id
          JOIN stock_location dest_loc ON dest_loc.ID = sm.location_dest_id 
        WHERE
          sm.STATE = 'done' 

        ) AS mov ON mov.origen = ubicacion.ID 
      OR mov.ubicacion = ubicacion.ID 
  ) AS stock
          )""")

    @api.multi
    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('id', 'in', self.move_id.account_move_ids.ids)]
        return action_data

    # @api.multi
    # def action_get_sale_order(self):
    #     self.ensure_one()
    #     action_ref = self.env.ref('sale.action_move_journal_line')
    #     if not action_ref:
    #         return False
    #     action_data = action_ref.read()[0]
    #     action_data['domain'] = [('id', 'in', self.sale_id.ids)]
    #     return action_data

    # @api.multi
    # def action_get_purchase_order(self):
    #     self.ensure_one()
    #     action_ref = self.env.ref('purchase.action_move_journal_line')
    #     if not action_ref:
    #         return False
    #     action_data = action_ref.read()[0]
    #     action_data['domain'] = [('id', 'in', self.purchase_id.ids)]
    #     return action_data

    # @api.multi
    # def action_get_invoice(self):
    #     self.ensure_one()
    #     action_ref = self.env.ref('account.action_invoice_form')
    #     if not action_ref:
    #         return False
    #     action_data = action_ref.read()[0]
    #     action_data['domain'] = [('id', 'in', self.invoice_id.ids)]

    # @api.one
    # @api.depends('sale_id', 'purchase_id', 'origin')
    # def _compute_invoice_search(self):
    #     self.ensure_one()
    #     invoice = False
    #     if self.purchase_id:
    #         invoice = self.env['account.invoice.line'].search([('purchase_line_id', '=', self.purchase_line_id.id)])
    #     elif self.sale_id:
    #         invoice = self.sale_line_id.invoice_lines
    #     else:
    #         invoice = self.env['account.invoice.line'].search([('invoice_id.origin', '=', self.origin)])
    #     import logging
    #     _logger = logging.getLogger(__name__)
    #     _logger.info('\n\n %r \n\n', invoice)
    #     if invoice:
    #         self.invoice_id = invoice.mapped('invoice_id').ids[0]
    #     else:
    #         self.invoice_id = invoice