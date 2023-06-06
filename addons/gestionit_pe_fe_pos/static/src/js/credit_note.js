odoo.define("gestionit_pe_fe_pos.credit_note",function(require){
    "use strict";
    var pos_order_mgmt = require('pos_order_mgmt.widgets')
    var screens = require("point_of_sale.screens")
    var gui = require("point_of_sale.gui")
    var popups = require("point_of_sale.popups")
    var DB = require('point_of_sale.DB');
    var models = require('point_of_sale.models')
    var chrome = require('point_of_sale.chrome')
    var BaseWidget = require('point_of_sale.BaseWidget')
    var PosModelSuper = models.PosModel


    chrome.OrderSelectorWidget.include({
        order_click_handler: function(event,$el) {
            this._super(event,$el)
            if(this.pos.get_order()){
                if(this.pos.get_order().get_invoice_type() == 'out_refund'){
                    this.gui.show_screen("screen_credit_note")
                }
            }
        },
    })
    
    chrome.Chrome.include({
        build_widgets:function(){
            this._super();
            if(this.pos.get_order()){
                if(this.pos.get_order().get_invoice_type() == 'out_refund'){
                    this.gui.show_screen("screen_credit_note")
                }
            }
        }
    })

    var CreateCreditNoteModal = popups.extend({
        template:"CreateCreditNoteModal",
        events:{
            "click .create_credit_note":"create",
            'click .button.cancel': 'click_cancel'
        },
        show:function(options){
            this._super(options)
            this.order_id = options.order_id
            this.partner_id = options.partner_id[0]
            $(this.$el).find("#invoice_name").text(options.invoice_id[1]) 
            $(this.$el).find("#partner_name").text(options.partner_id[1])
        },
        create:function(ev){
            var self = this
            var credit_note_comment = $(this.$el).find("textarea[name='credit_note_comment']").val()
            var credit_note_type = $(this.$el).find("input[name='credit_note_type']:checked").val()
            if(credit_note_comment == "" || credit_note_type == ""){
                self.gui.show_popup('error', {
                    'title': "Error",
                    'body': "El sustento y el tipo de la nota de crédito son obligatorios",
                });
                return;
            }
            this._rpc({
                model:"pos.order",
                method:"get_order",
                args:[[self.order_id]],
                kwargs:{}
            }).then(async function(res){
                var new_order = new models.Order({},{pos:self.pos});
                self.pos.get('orders').add(new_order);

                var client = self.pos.db.get_partner_by_id(self.partner_id)
                new_order.set_client(client);
                new_order.set_sale_type("refund")
                new_order.set_invoice_type('out_refund');
                new_order.set_credit_note_comment(credit_note_comment);
                new_order.set_refund_order_id(self.order_id);
                new_order.set_refund_order_name(res.order_name);
                new_order.set_refund_order_date(res.date)
                new_order.set_credit_note_type(credit_note_type);
                new_order.set_refund_order_payments(res.payments)
                console.log(self.pos)
                console.log(res.payments)
                await _.forEach(res.payments,function(el){
                    let payment_method = self.pos.payment_methods_by_id[el.id];
                    new_order.add_paymentline_v2(payment_method,-1*el.amount)
                })

                if(res.has_invoice){
                    new_order.set_refund_invoice(res.invoice_id);
                    new_order.set_refund_invoice_type_code(res.invoice_type_code);
                }
                new_order.trigger('change',new_order);
                self.pos.set('selectedOrder', new_order);
                self.gui.show_screen("screen_credit_note")
            })
        }
    })

    gui.define_popup({
        name:"create_credit_note_modal",
        widget:CreateCreditNoteModal
    })

    // LÍNEAS DE NOTAS DE CRÉDITO
    var CreditNoteLine = BaseWidget.extend({
        template:"CreditNoteLine",  
        events:{
            "click .remove":"remove",
        },
        init:function(parent,options){
            this._super(parent,options)
            // this.id = options.id
            this.line = options
            this.default_code = options.get_product().default_code
            this.name = options.product.display_name
            this.quantity = options.get_quantity()
            this.product_id = [options.product.id,options.product.display_name]
            // this.uom_id = options.product.uom_id
            this.price_unit = options.get_unit_price()
            this.price_total = options.get_price_with_tax()

            // var current_order = this.pos.get_order()  
            // this.pos.get_order().on("change:credit_note_type",function(){console.log("cambio")})  
            // console.log(current_order)
        },
        renderElement:function(){
            this._super()
            var credit_note_type = this.pos.db.get_credit_note_type_by_id(this.pos.get_order().get_credit_note_type())
            if(["01","02","06"].indexOf(credit_note_type.code) >= 0){
                $(this.$el).find(".remove").css({"display":"none"})
            }else{
                $(this.$el).find(".remove").css({"display":"block"})
            }
        },
        remove:function(ev){
            _.bind(this.line.set_quantity,this.line)("remove")
            this.destroy()
        }
    })

    // REFUND INVOICE LINE

    var RefundInvoiceLine = BaseWidget.extend({
        template:"RefundInvoiceLine",
        events:{
            "click .add_line":"btn_add_line",
            "click .edit_add_line":"btn_edit_add_line"
        },
        init:function(parent,options){
            this._super(parent,options)
            this.id = options.id
            this.name = options.display_name
            this.quantity = options.qty
            this.product_id = options.product_id
            // this.uom_id = options.uom_id
            this.price_unit = options.price_unit
            this.price_total = options.price_subtotal_incl
            this.parent = parent
        },
        renderElement:function(){
            this._super()
            var credit_note_type = this.pos.db.get_credit_note_type_by_id(this.pos.get_order().get_credit_note_type())
            if(["01","02","06"].indexOf(credit_note_type.code) >= 0){
                $(this.$el).find(".add_line").css({"display":"none"})
                $(this.$el).find(".edit_add_line").css({"display":"none"})
            }else{
                $(this.$el).find(".add_line").css({"display":"block"})
                $(this.$el).find(".edit_add_line").css({"display":"block"})
            }
        },
        btn_add_line:function(ev){
            this.add_line(this.product_id[0],this.quantity,this.price_unit)
        },
        add_line:function(product_id,quantity,price_unit){
            var self = this
            var order = this.pos.get_order()
            var lines = order.get_orderlines()

            var exist_line = _.find(lines,function(line){return line.product.id == product_id})
            let product = self.pos.db.get_product_by_id(product_id)
            
            if(exist_line == undefined){
                order.add_product(product,{price:price_unit,quantity:-quantity})
                _.bind(self.parent.refresh_credit_note_lines,self.parent)()
            }else{
                order.remove_orderline(exist_line)
                order.add_product(product,{price:price_unit,quantity:-quantity})
                _.bind(self.parent.refresh_credit_note_lines,self.parent)()
            }
        },
        btn_edit_add_line:function(ev){
            this.gui.show_popup("add_credit_note_line_modal",{product_id:this.product_id[0],
                                                                product_name:this.product_id[1],
                                                                quantity:this.quantity,
                                                                price_unit:this.price_unit,
                                                                add_line:this.add_line,
                                                                parent:this})
        }
    })

    // SCREEN CREDIT NOTE

    var ScreenCreditNote = screens.ScreenWidget.extend({
        template:"ScreenCreditNote",
        events:{
            "click .back":"remove",
            "click .next":"validate",
            "change input[name='credit_note_type']":"change_credit_note_type"
        },
        change_credit_note_type: function(ev){
            var credit_note_type_id = $(ev.currentTarget).val()
            this.pos.get_order().set_credit_note_type(credit_note_type_id)
            this.select_credit_note_type(credit_note_type_id)
            this.refresh_refund_invoice_lines()
        },
        select_credit_note_type:async function(credit_note_type_id){
            var order = this.pos.get_order()
            var credit_note_type = this.pos.db.get_credit_note_type_by_id(parseInt(credit_note_type_id))
            var self = this
            var lines = _.clone(order.get_orderlines())
            if(["01","02","06"].indexOf(credit_note_type.code) >= 0){
                if(lines.length >0){
                    // Se eliminan las lineas de ordenes de venta almacenadas
                    await lines.forEach((line,idx)=> order.remove_orderline(line))
                }
                // Se actualizan las líneas de órden de venta
                await self._rpc({
                    model:"pos.order.line",
                    method:"search_read",
                    args:[],
                    kwargs:{
                        fields:["product_id","display_name","qty","price_unit","price_subtotal_incl"],
                        domain:[["order_id","=",order.refund_order_id]]
                    }
                }).then(async function(lines){
                    await lines.forEach(function(line){
                        let product = self.pos.db.get_product_by_id(line.product_id[0])
                        order.add_product(product,{price:line.price_unit,quantity:-line.qty})
                    })
                    await _.bind(self.refresh_credit_note_lines,self)()
                })
            }
            else if(credit_note_type.code == "07"){
                self.refresh_credit_note_lines()
            }
        },
        show: function(options){
            var self = this
            this._super(options);
            var order = this.pos.get_order()
            // var credit_note_type_id = order.get_credit_note_type()
            // console.log(credit_note_type_id)
            
            var refund_invoice = order.get_refund_invoice()
            if(refund_invoice){
                $(this.$el).find("#invoice_name").text(refund_invoice.name)
            }else{
                $(this.$el).find("#invoice_name").text("------------")
            }
            var client = order.get_client()
            if(client){
                $(this.$el).find("#partner_name").text(client.name)
            }else{
                $(this.$el).find("#partner_name").text("------------")
            }

            // console.log($(this.$el).find("input[name='credit_note_type'][value='"+credit_note_type_id+"']"))
            $(this.$el).find("input[name='credit_note_type'][value='"+order.credit_note_type+"']").selected(true).change()
            $(this.$el).find("textarea[name='credit_note_comment']").val(order.credit_note_comment)

            // await this.select_credit_note_type(order.get_credit_note_type())

            // var table_refund_invoice_lines = $(self.$el).find(".table_refund_invoice_lines tbody")
            // this._rpc({
            //     model:"pos.order.line",
            //     method:"search_read",
            //     args:[],
            //     kwargs:{
            //         fields:["product_id","display_name","qty","price_subtotal","price_subtotal_incl","price_unit"],
            //         domain:[["order_id","=",order.refund_order_id]]
            //     }
            // }).then(function(lines){
            //     table_refund_invoice_lines.empty()
            //     lines.forEach(function(line){
            //         // console.log(line);
            //         (new RefundInvoiceLine(self,line)).appendTo(table_refund_invoice_lines)
            //     })
            // })

            setInterval(function(){
                order = self.pos.get_order()
                $(self.$el).find("#credit_note_amount_total").text(self.format_currency(order.get_total_with_tax(),'Price POS'))
            },600)

            // this.refresh_credit_note_lines()
            
        },
        remove:function(ev){
            var self = this;
            this.gui.show_popup('confirm',{
                'title': "¿Desea eliminar la nota de crédito actual?",
                'body': "Usted perderá cualquier información asociada a este nota de crédito",
                confirm: function(){
                    self.pos.delete_current_order();
                },
            });
        },
        validate:function(ev){
            this.gui.show_screen('payment');
        },
        refresh_credit_note_lines:function(){
            var order = this.pos.get_order()
            var self = this
            var table_credit_note_lines = $(self.$el).find(".table_credit_note_lines tbody").empty()
            order.get_orderlines().forEach(function(line){
                // console.log(line);
                (new CreditNoteLine(self,line)).appendTo(table_credit_note_lines)
            })
        },
        refresh_refund_invoice_lines:function(){
            var self = this;
            var order = self.pos.get_order()
            var table_refund_invoice_lines = $(self.$el).find(".table_refund_invoice_lines tbody").empty()
            this._rpc({
                model:"pos.order.line",
                method:"search_read",
                args:[],
                kwargs:{
                    fields:["product_id","display_name","qty","price_subtotal","price_subtotal_incl","price_unit"],
                    domain:[["order_id","=",order.refund_order_id]]
                }
            }).then(function(lines){
                lines.forEach(function(line){
                    (new RefundInvoiceLine(self,line)).appendTo(table_refund_invoice_lines)
                })
            })
        }
    })

    gui.define_screen({
        name: 'screen_credit_note',
        widget: ScreenCreditNote
    });


});