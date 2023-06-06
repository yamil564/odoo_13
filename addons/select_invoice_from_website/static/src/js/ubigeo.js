odoo.define('select_invoice_from_website.change_res_ubigeo',function(require){
    'use strict';
    var publicWidget = require("web.public.widget")
    // var rpc = require("web.rpc")
    // var core = require("web.core")
    // var qweb = core.qweb
    var ajax = require("web.ajax")
    // var _t = core._t;
    // var Widget = require("web.Widget")
    // var session = require("web.session")

    var WebsiteSaleSuper = publicWidget.registry.WebsiteSale.prototype

    publicWidget.registry.WebsiteSale = publicWidget.registry.WebsiteSale.extend({
        events:_.extend({},WebsiteSaleSuper.events,{
            'change #departamento':'loadProvincias',
            'change #provincia':'loadDistritos',
            'change #country':'loadDepartamentos',
        }),
        loadDepartamentos:function(){
            var self = this
            var pais = $(self.$el).find("#country").val()
            let departamento_id = $(self.$el).find("select#departamento").val()
            $(self.$el).find("#departamento").empty()
            ajax.jsonRpc('/get-departamento', 'call',
             {'pais': pais}).then(function (data) {
                    // console.log(data);
                    $(self.$el).find("#departamento").append($('<option selected="1"/}>').val(0).text("Seleccionar"));
                    for (let i = 0; i < data.length; i++) {
                        if(departamento_id != data[i].id){
                            $(self.$el).find("#departamento").append($('<option /}>').val(data[i].id).text(data[i].name));
                        }else{
                            $(self.$el).find("#departamento").append($('<option selected="1"/}>').val(data[i].id).text(data[i].name));
                        }
                    }
            })
        },
        loadProvincias:function(){
            var self = this
            var departamento = $(self.$el).find("#departamento").val()
            let provincia_id = $(self.$el).find("select#provincia").val()
            $(self.$el).find("#provincia").empty()
            ajax.jsonRpc('/get-provincia', 'call',
             {'departamento': departamento}).then(function (data) {
                $(self.$el).find("#provincia").append($('<option selected="1"/}>').val(0).text("Seleccionar"));
                for (let i = 0; i < data.length; i++) {
                    $(self.$el).find("#provincia").append($('<option /}>').val(data[i].id).text(data[i].name));
                }
                    // if(provincia_id == undefined || provincia_id == undefined){
                    //     $(self.$el).find("#provincia").append($('<option selected="1"/}>').val(data[0].id).text(data[0].name));
                    // }
                    // for (let i = 1; i < data.length; i++) {
                    //     if(provincia_id != data[i].id){
                    //         $(self.$el).find("#provincia").append($('<option /}>').val(data[i].id).text(data[i].name));
                    //     }else{
                    //         $(self.$el).find("#provincia").append($('<option selected="1"/}>').val(data[i].id).text(data[i].name));
                    //     }
                    // }
            })
        },
        loadDistritos:function(){
            var self = this
            var provincia = $(self.$el).find("#provincia").val()
            $(self.$el).find("#distrito").empty()
            ajax.jsonRpc('/get-distrito', 'call',
             {'provincia': provincia}).then(function (data) {
                $(self.$el).find("#distrito").append($('<option selected="1"/}>').val(0).text("Seleccionar"));
                for (let i = 0; i < data.length; i++) {
                    $(self.$el).find("#distrito").append($('<option /}>').val(data[i].id).text(data[i].name));
                }
            })
        },
    });
});
