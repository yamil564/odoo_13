odoo.define("gestionit_pe_tipocambio.menu_exchange",function(require){
    "use strict";
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');

    function dateToYMD(date) {
        var d = date.getDate();
        var m = date.getMonth() + 1; //Month from 0 to 11
        var y = date.getFullYear();
        return '' + y + '-' + (m<=9 ? '0' + m : m) + '-' + (d <= 9 ? '0' + d : d);
    }

    var currency_types = {
        "commercial":"Comercial",
        "sale":"Venta",
        "purchase":"Compra"
    }

    var ExchangeMenuLine = Widget.extend({
        template:"ExchangeMenuLine",
        init:function(parent,options){
            this._super(parent,options);
            this.id = options.id
            this.name = options.name
            this.display_name = options.display_name
            this.parent = parent
            this.type = currency_types[options.type] || "-"
            // var d = new Date()
            if(options.rate!=0 && options.date == dateToYMD(new Date())){
                this.rate = Math.round(10000*(1/options.rate),4)/10000
                // this.tc_compra = Math.round(10000*(options.cambio_compra),4)/10000
                // this.tc_venta = Math.round(10000*(options.cambio_venta),4)/10000
            }else{
                this.rate = 0.00
                // this.tc_venta = 0.00
            }
        },
        start:function(){
            var self = this;
            $(this.$el).on("click",function(ev){
                ev.preventDefault();
                var currency_menu = $(ev.currentTarget)
                var currency_id = currency_menu.data("id")
                // console.log(currency_id)
                self.trigger_up('clear_uncommitted_changes', {
                    callback: function () {
                        self._rpc({
                                model: "res.currency",
                                method: "action_get",
                                args:[[currency_id]],
                                kwargs: {}
                            })
                            .then(function (result) {
                                // result.res_id = session.uid;
                                self.do_action(result);
                            });
                    },
                });
            })
        }
    })

    var ExchangeMenu = Widget.extend({
        template: 'ExchangeMenu',
        start:function(){
            var self = this;
            var options_exchanges = $(this.$el).find(".options-exchanges")
            var f = new Date();
            var fecha = f.getDate() + "/" + (f.getMonth() +1) + "/" + f.getFullYear();
            $(this.$el).find(".date_today").text(fecha)
            
            $(this.$el.find(".menu-exchange")).on("click",function(e){
                options_exchanges.empty()
                // console.log(e.currentTarget)
                self._rpc({
                    model:"res.currency",
                    method:"search_read",
                    args:[],
                    kwargs:{}
                }).then(function(result){
                    // console.log(result);
                    _.each(result,function(el){
                        if(el.name != "PEN"){
                            // console.log(new ExchangeMenuLine(self,el));
                            (new ExchangeMenuLine(self,el)).appendTo(options_exchanges)
                        }
                    })
                })
            })
        },

    })
    rpc.query({
        model:"res.users",
        method:"has_group",
        args:['gestionit_pe_tipocambio.res_groups_access_exchange_usd_pen_view'],
        kwarts:{}
    }).then(function(res){
        if(res){
            SystrayMenu.Items.push(ExchangeMenu);
        }
    })
    
})