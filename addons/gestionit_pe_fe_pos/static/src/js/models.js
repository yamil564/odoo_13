odoo.define("gestionit_pe_fe_pos.models",[
    "gestionit_pe_fe_pos.DB",
    "point_of_sale.models",
    "web.rpc",
    "web.utils",
    "web.session"
],function(require){
    "use strict";
    var models = require("point_of_sale.models")
    var PosDB = require("gestionit_pe_fe_pos.DB")
    var session = require('web.session');
    var utils = require('web.utils');
    var PosModelSuper = models.PosModel;
    var OrderSuper = models.Order
    var OrderlineSuper = models.Orderline
    var PaymentlineSuper = models.Paymentline
    var exports = {}
    var round_di = utils.round_decimals;
    var round_pr = utils.round_precision;

    _.find(PosModelSuper.prototype.models,function(el){return el.model == 'res.partner'}).fields.push('l10n_latam_identification_type_id','mobile');
    _.find(PosModelSuper.prototype.models,function(el){return el.model == 'res.company'}).fields.push('logo','street','phone','website_invoice_search');
    _.find(PosModelSuper.prototype.models,function(el){return el.model == 'account.tax'}).fields.push('tax_group_id')

    _.find(PosModelSuper.prototype.models,function(el){return el.label == 'pictures'}).loaded = function (self) {
        self.company_logo = new Image();
        return new Promise(function (resolve, reject) {
            self.company_logo.onload = function () {
                var img = self.company_logo;
                var ratio = 1;
                var targetwidth = 300;
                var maxheight = 150;
                if( img.width !== targetwidth ){
                    ratio = targetwidth / img.width;
                }
                if( img.height * ratio > maxheight ){
                    ratio = maxheight / img.height;
                }
                var width  = Math.floor(img.width * ratio);
                var height = Math.floor(img.height * ratio);
                var c = document.createElement('canvas');
                c.width  = width;
                c.height = height;
                var ctx = c.getContext('2d');
                ctx.drawImage(self.company_logo,0,0, width, height);

                self.company_logo_base64 = c.toDataURL();
                resolve();
            };
            self.company_logo.onerror = function () {
                reject();
            };
            self.company_logo.crossOrigin = "anonymous";
            self.company_logo.src = '/web/image?model=res.company&id='+self.company.id+'&field=logo'+ '&dbname=' + session.db + '&_' + Math.random();
        });
    }

    PosModelSuper.prototype.models.push({
        model: 'account.journal',
        fields: ['id','name','code','invoice_type_code_id','sequence_id','tipo_comprobante_a_rectificar'],
        domain: function(self) {
            return [
                ['id', 'in', self.config.invoice_journal_ids]
            ];
        },
        loaded: function(self, journals) {
            self.db.sequence_ids = _.map(journals,function(journal){return journal.sequence_id[0]});
            self.db.add_journals(journals);
        },
    },{
        model: 'ir.sequence',
        fields: ['id', 'prefix', 'suffix', 'padding', 'number_next_actual'],
        domain: function(self) {
            return [
                ['id', 'in', self.db.sequence_ids]
            ];
        },
        loaded: function(self, sequences) {
            self.db.add_sequences(sequences);
        },
    },{
        model: 'account.tax.group',
        fields: ['id','codigo','tipo_afectacion'],
        loaded:function(self,account_tax_groups){
            self.taxes = _.map(self.taxes,function(tax){
                tax["tax_group_id"] = _.find(account_tax_groups,function(atg){atg.id == tax["tax_group_id"]})
                return tax
            })
        }
    },{
        model:'l10n_latam.identification.type',
        fields: ['id','name','l10n_pe_vat_code','available_in_pos'],
        domain:['|',['active','=',true],['active','=',false]],
        loaded:function(self,identification_types){
            self.identification_types = identification_types
            self.db.add_identification_types(identification_types)
        }
    });

    models.PosModel = models.PosModel.extend({
        initialize: function(session, attributes) {
            var res = PosModelSuper.prototype.initialize.apply(this, arguments);
            this.db = new PosDB(); // a local database used to search trough products and categories & store pending orders
            return res;
        },
        generate_order_number: function(journal_id) {
            var sequence = this.db.get_journal_sequence_id(journal_id);
            var num = "%0" + sequence.padding + "d";
            var prefix = sequence.prefix || "";
            var suffix = sequence.suffix || "";
            var increment = this.db.get_sequence_next(journal_id);
            var number = prefix + num.sprintf(parseInt(increment)) + suffix;
            return { 'number': number, 'sequence_number': increment };
        },
        get_order_number: function(journal_id) {
            var numbers = this.generate_order_number(journal_id);
            if (this.db.get_invoice_numbers().indexOf(numbers.number) != -1) {
                var numbers = this.get_order_number(journal_id);
                var sequence = this.db.get_journal_sequence_id(journal_id);
                this.db.set_sequence_next(sequence.id, numbers.sequence_number);
            }
            return numbers;
        },
        get_client_identification_type_code:function(){
            var client = this.get_client()
            var identification_type = undefined
            if(client.l10n_latam_identification_type_id){
                identification_type = this.db.identification_type_by_id[client.l10n_latam_identification_type_id[0]]
                var client_identification_type_code = identification_type.l10n_pe_vat_code
            }else{
                var client_identification_type_code = undefined
            }
            return client_identification_type_code
        },
        get_client_display_name:function(){
            var client = this.get_client()
            if(client){
                var client_name = client.name
            }else{
                return false
            }
            var identification_type = undefined;
            if(client.l10n_latam_identification_type_id){
                identification_type = this.db.identification_type_by_id[client.l10n_latam_identification_type_id[0]]
                var client_identification_type_code = identification_type.l10n_pe_vat_code
            }else{
                var client_identification_type_code = undefined
            }
            if(['1','6'].indexOf(client_identification_type_code) >=0 && Boolean(client.vat)){
                client_name += " [" +identification_type.name+"-"+client.vat+"]" 
            }else if(['1','6'].indexOf(client_identification_type_code) >=0 && Boolean(~client.vat) ){
                client_name += " [" +identification_type.name+"- N/A]" 
            }else{
                client_name += " [N/A]"
            }
            return client_name
        },
        set_sequence: function(journal_id, number, number_increment) {
            var sequence = this.db.get_journal_sequence_id(journal_id);
            this.db.set_sequence_next(sequence.id, number_increment);
            this.db.add_invoice_numbers(number);

        },
        rucValido: function(ruc) {
            var ex_regular_ruc;
            ex_regular_ruc = /^\d{11}(?:[-\s]\d{4})?$/;
            if (ex_regular_ruc.test(ruc)) {
                return true
            }
            return false;
        },
        dniValido: function(dni) {
            var ex_regular_dni;
            ex_regular_dni = /^\d{8}(?:[-\s]\d{4})?$/;
            if (ex_regular_dni.test(dni)) {
                return true
            }
            return false;
        },
    });
    
    models.Order = models.Order.extend({
        initialize: function(attributes, options) {
            this.sale_type = "sale"
            this.invoice_type = "out_invoice"
            this.refund_order_id = undefined;
            this.refund_order_payments = []
            OrderSuper.prototype.initialize.apply(this, arguments);
            this.number = false;
            this.invoice_journal_id = undefined;
            this.sequence_number = 0;
            this.set("credit_note_type",undefined)
            // console.log(this.pos)
            this.save_to_db(); 
        },
        set_sale_type: function(sale_type){
            var self = this;
            this.assert_editable();
            if(['sale','refund'].indexOf(sale_type)){
                self.sale_type = sale_type
            }else{
                self.gui.show_popup('error', {
                    'title': "Error",
                    'body': "El tipo de venta no esta permitido. Tipos de ventas permitidas 'sale', 'refund'",
                });
            }
        },
        set_invoice_type: function(invoice_type){
            var self = this;
            this.assert_editable();
            if(['out_invoice','out_refund'].indexOf(invoice_type)){
                self.invoice_type = invoice_type
            }else{
                self.gui.show_popup('error', {
                    'title': "Error",
                    'body': "El tipo de operación de comprobante no esta permitido. Tipos de operaciones permitidas 'out_invoice', 'out_refund'",
                });
            }
        },
        get_invoice_type: function(){
            return this.invoice_type
        },
        export_for_printing:function(){
            var res = OrderSuper.prototype.export_for_printing.apply(this, arguments);
            var self = this;
            var client = self.pos.get_client()
            var client_identification_type_code = undefined;
            var identification_type = undefined;
            if(client){
                if(client.l10n_latam_identification_type_id){
                    identification_type = self.pos.db.identification_type_by_id[client.l10n_latam_identification_type_id[0]]
                    var client_identification_type_code = identification_type.l10n_pe_vat_code
                }
            } 
            var journal = self.get_invoice_journal_id()?self.pos.db.journal_by_id[self.get_invoice_journal_id()]:undefined;
            // console.log(client)
            // console.log(journal)
            // console.log(res)
            // console.log(res.date)
            res["date"] = moment.utc(res.date).local().format("YYYY-MM-DD HH:mm:ss");
            // console.log(res.date)
            if(client && journal){
                res["qr_string"] = [res.company.vat, //RUC de emisor
                                    journal.invoice_type_code_id, //Tipo de comprobante electrónico
                                    journal.code, //Serie de comprobante
                                    self.sequence_number,//Número correlativo
                                    Math.abs(res.total_tax),//Total IGV
                                    Math.abs(res.total_with_tax),//Monto Totales
                                    res.date.substr(0,10),//Fecha de Emisión
                                    client_identification_type_code,//Tipo de documento de identidad de Receptor
                                    client.vat, //Número de documento de identidad de Receptor
                                    this.get_digest_value()
                                    ].join("|")
            }
            
            // console.log(res["qr_string"])
            // console.log("==============export_for_printing==================")
            // console.log(res)
            return res
        },
        set_pos_order_id:function(pos_order_id){
            this.pos_order_id = pos_order_id
        },
        get_pos_order_id:function(){
            return this.pos_order_id
        },
        set_digest_value:function(digest_value){
            this.digest_value = digest_value
        },
        get_digest_value:function(){
            return this.digest_value || "*"
        },
        set_invoice_portal_url:function(invoice_portal_url){
            this.invoice_portal_url = invoice_portal_url
        },
        get_invoice_portal_url:function(){
            return this.invoice_portal_url
        },
        get_sale_type: function(){
            return this.sale_type
        },
        set_invoice_journal_id: function(invoice_journal_id) {
            this.assert_editable();
            this.to_invoice = invoice_journal_id?true:false
            this.invoice_journal_id = invoice_journal_id;
        },
        get_invoice_journal_id: function() {
            return this.invoice_journal_id;
        },
        get_invoice_date:function(){
            return this.invoice_date
        },
        set_invoice_date:function(invoice_date){
            this.invoice_date = invoice_date
        },
        export_as_JSON: function() {
            var res = OrderSuper.prototype.export_as_JSON.apply(this, arguments);
            var journal = this.pos.db.get_journal_by_id(this.invoice_journal_id);
            res['invoice_journal_id'] = this.invoice_journal_id;
            res['number'] = this.number;
            res['sequence_number'] = this.sequence_number;
            res['invoice_type_code_id'] = (typeof journal === 'undefined') ? journal : journal.invoice_type_code_id;
            res['invoice_type'] = this.invoice_type
            res['credit_note_type'] = this.credit_note_type
            res['credit_note_comment'] = this.credit_note_comment
            res['sale_type'] = this.sale_type || "sale"
            res['refund_invoice'] = this.refund_invoice
            res['refund_invoice_type_code'] = this.refund_invoice_type_code
            res['refund_order_id'] = this.refund_order_id
            res['invoice_date'] = this.invoice_date
            res['refund_order_payments'] = this.refund_order_payments
            return res;
        },
        init_from_JSON: function(json) {
            OrderSuper.prototype.init_from_JSON.apply(this, arguments);
            this.sale_type = json.sale_type || "sale"
            this.credit_note_type = json.credit_note_type
            this.invoice_journal_id = json.invoice_journal_id
            this.refund_invoice = json.refund_invoice
            this.refund_invoice_type_code = json.refund_invoice_type_code
            this.credit_note_comment = json.credit_note_comment
            this.invoice_type_code_id = json.invoice_type_code_id
            this.invoice_type = json.invoice_type
            this.refund_order_id = json.refund_order_id
            this.invoice_date = json.invoice_date
            this.refund_order_payments = json.refund_order_payments
        },
        set_number: function(number) {
            // this.assert_editable();
            this.number = number;
        },
        get_number: function() {
            return this.number;
        },
        set_sequence_number: function(number) {
            this.sequence_number = number;
        },
        get_sequence_number: function() {
            return this.sequence_number;
        },
        set_credit_note_type:function(credit_note_type){
            this.assert_editable();
            if(credit_note_type){
                // this.credit_note_type = parseInt(credit_note_type)
                this.credit_note_type = credit_note_type;
                this.set("credit_note_type",credit_note_type)
            }
        },
        get_credit_note_type:function(){
            return this.credit_note_type
        },
        get_credit_note_type_name:function(){
            return this.pos.db.get_credit_note_type_by_id(this.credit_note_type)?this.pos.db.get_credit_note_type_by_id(this.credit_note_type).name:""
        },
        set_credit_note_comment:function(comment){
            this.assert_editable();
            this.credit_note_comment = comment
        },
        get_credit_note_comment:function(){
            return this.credit_note_comment
        },
        set_refund_invoice_type_code:function(refund_invoice_type_code){
            this.assert_editable();
            var self = this;
            if(["01","03"].indexOf(refund_invoice_type_code)>=0){
                this.refund_invoice_type_code = refund_invoice_type_code
            }else{
                self.pos.gui.show_popup('error', {
                    'title': "Error",
                    'body': "El tipo de comprobante a rectificar no esta permitido. Solo se acepta 01-Factura y 03-Boleta",
                });
                throw new TypeError("El tipo de comprobante a rectificar no existe");
            }
        },
        set_refund_order_id:function(order_id){
            this.refund_order_id = order_id
        },
        get_refund_order_id:function(){
            return this.refund_order_id
        },
        set_refund_order_name:function(order_name){
            this.refund_order_name = order_name
        },
        get_refund_order_name:function(){
            return this.refund_order_name
        },
        set_refund_order_date:function(order_date){
            this.refund_order_date = order_date
        },
        get_refund_order_date:function(){
            return this.refund_order_date
        },
        set_refund_invoice:function(invoice){
            this.assert_editable();
            this.refund_invoice = invoice
        },
        set_credit_note_types:function(credit_note_types){
            this.credit_note_types = credit_note_types
        },
        get_credit_note_types:function(){
            return this.credit_note_types
        },
        set_refund_order_payments:function(payments){
            this.refund_order_payments = payments
        },
        get_refund_order_payments:function(){
            return this.refund_order_payments
        },
        get_refund_invoice_type_code:function(){
            return this.refund_invoice_type_code
        },
        get_refund_invoice:function(){
            return {id:this.refund_invoice[0],name:this.refund_invoice[1]}
        },
        set_invoice_type_code_id:function(invoice_type_code_id){
            this.invoice_type_code_id = invoice_type_code_id
        },
        get_invoice_type_code_id:function(){
            return this.invoice_type_code_id
        },
        total_items: function(){
            return Math.abs(_.reduce(_.map(this.get_orderlines(),function(el){return el.get_quantity()}),function(a,b){return a+b}))
        },
        get_client: function() {
            var return_val = OrderSuper.prototype.get_client.apply(this, arguments);
            if (return_val == undefined) {
                return_val = this.pos.db.get_partner_by_id(
                    this.pos.config.anonymous_id[0]
                );
            }
            return return_val;
        },
        add_paymentline_v2: function(payment_method,amount) {
            this.assert_editable();
            var newPaymentline = new PaymentlineSuper({},{order: this, payment_method:payment_method, pos: this.pos});
            if(!payment_method.is_cash_count || this.pos.config.iface_precompute_cash){
                newPaymentline.set_amount(amount);
            };
            this.paymentlines.add(newPaymentline);
            this.select_paymentline(newPaymentline);
    
        },
        // get_total_for_taxes: function(tax_id){
        //     var total = 0;
    
        //     if (!(tax_id instanceof Array)) {
        //         tax_id = [tax_id];
        //     }
    
        //     var tax_set = {};
    
        //     for (var i = 0; i < tax_id.length; i++) {
        //         tax_set[tax_id[i]] = true;
        //     }
    
        //     this.orderlines.each(function(line){
        //         // var taxes_ids = line.get_product().taxes_id;
        //         var taxes_ids = line.taxes_id;
        //         for (var i = 0; i < taxes_ids.length; i++) {
        //             if (tax_set[taxes_ids[i]]) {
        //                 total += line.get_price_with_tax();
        //                 return;
        //             }
        //         }
        //     });
    
        //     return total;
        // },
    });

    // models.Orderline = models.Orderline.extend({
    //     initialize: function(attr,options){
    //         OrderlineSuper.prototype.initialize.apply(this, arguments);
    //         this.taxes_id = this.product.taxes_id
    //         console.log(this.taxes_id)
    //     },
    //     set_taxes_id:function(taxes_id){
    //         this.taxes_id = taxes_id
    //     },
    //     get_display_price_one: function(){
    //         var rounding = this.pos.currency.rounding;
    //         var price_unit = this.get_unit_price();
    //         if (this.pos.config.iface_tax_included !== 'total') {
    //             return round_pr(price_unit * (1.0 - (this.get_discount() / 100.0)), rounding);
    //         } else {
    //             // var product =  this.get_product();
    //             var taxes_ids = this.taxes_id;
    //             var taxes =  this.pos.taxes;
    //             var product_taxes = [];
    
    //             _(taxes_ids).each(function(el){
    //                 product_taxes.push(_.detect(taxes, function(t){
    //                     return t.id === el;
    //                 }));
    //             });
    
    //             var all_taxes = this.compute_all(product_taxes, price_unit, 1, this.pos.currency.rounding);
    
    //             return round_pr(all_taxes.total_included * (1 - this.get_discount()/100), rounding);
    //         }
    //     },
    //     get_taxes: function(){
    //         // var taxes_ids = this.get_product().taxes_id;
    //         var taxes_ids = this.taxes_id;
    //         var taxes = [];
    //         for (var i = 0; i < taxes_ids.length; i++) {
    //             taxes.push(this.pos.taxes_by_id[taxes_ids[i]]);
    //         }
    //         return taxes;
    //     },
    //     get_all_prices: function(){
    //         var self = this;
    
    //         var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
    //         var taxtotal = 0;
    
    //         // var product =  this.get_product();
    //         // var taxes_ids = product.taxes_id;
    //         var taxes_ids = this.taxes_id;
    //         var taxes =  this.pos.taxes;
    //         var taxdetail = {};
    //         var product_taxes = [];
    
    //         _(taxes_ids).each(function(el){
    //             var tax = _.detect(taxes, function(t){
    //                 return t.id === el;
    //             });
    //             product_taxes.push.apply(product_taxes, self._map_tax_fiscal_position(tax));
    //         });
    
    //         var all_taxes = this.compute_all(product_taxes, price_unit, this.get_quantity(), this.pos.currency.rounding);
    //         var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), this.get_quantity(), this.pos.currency.rounding);
    //         _(all_taxes.taxes).each(function(tax) {
    //             taxtotal += tax.amount;
    //             taxdetail[tax.id] = tax.amount;
    //         });
    
    //         return {
    //             "priceWithTax": all_taxes.total_included,
    //             "priceWithoutTax": all_taxes.total_excluded,
    //             "priceSumTaxVoid": all_taxes.total_void,
    //             "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
    //             "tax": taxtotal,
    //             "taxDetails": taxdetail,
    //         };
    //     },
    // })

    exports.models =models

})