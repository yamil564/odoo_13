odoo.define('bo_libro_reclamaciones.libro_reclamaciones',function(require){
    'use strict';
    var publicWidget = require("web.public.widget")
    var rpc = require("web.rpc")
    var core = require("web.core")
    var qweb = core.qweb
    var ajax = require("web.ajax")
    var _t = core._t;
    var Widget = require("web.Widget")
    var session = require("web.session")

    publicWidget.registry.LibroReclamaciones = publicWidget.Widget.extend({
        selector: ".libro-reclamaciones",
        events:{
            'change select[name="consumer_state_id"]':'change_consumer_state',
            'change select[name="consumer_province_id"]':'change_consumer_province',
            'change input[name="consumer_type"]':'change_consumer_type',
            'change input[name="consumer_younger"]':'change_consumer_younger'
        },
        start: function () {
        },
        change_consumer_state: function(ev){
            var self = this
            var consumer_state_id = $(ev.currentTarget).val()
            ajax.jsonRpc('/get-provincia-libro-reclamaciones', 'call',
                            {'departamento': consumer_state_id}).then(async function (data) {
                    await $(self.$el).find("select[name='consumer_province_id']").empty()
                    await $(self.$el).find("select[name='consumer_district_id']").empty()
                    $(self.$el).find("select[name='consumer_province_id']").append($('<option selected="" disabled="">Seleccionar</option>'))
                    $(self.$el).find("select[name='consumer_district_id']").append($('<option selected="" disabled="">Seleccionar</option>'))
                    for (let i = 0; i < data.length; i++) {
                        $(self.$el).find("select[name='consumer_province_id']").append($('<option /}>').val(data[i].id).text(data[i].name));
                    }
            })
        },
        change_consumer_province:function(ev){
            var self = this
            var consumer_province_id = $(ev.currentTarget).val()
            ajax.jsonRpc('/get-distrito-libro-reclamaciones', 'call',
                            {'provincia': consumer_province_id}).then(async function (data) {
                    await $(self.$el).find("select[name='consumer_district_id']").empty()
                    $(self.$el).find("select[name='consumer_district_id']").append($('<option selected="" disabled="">Seleccionar</option>'))
                    for (let i = 0; i < data.length; i++) {
                        $(self.$el).find("select[name='consumer_district_id']").append($('<option /}>').val(data[i].id).text(data[i].name));
                    }
            })
        },
        change_consumer_type:function(ev){
            var self = this;
            var company_type = $(ev.currentTarget).val()
            console.log(ev)
            if(company_type == 'individual'){
                $(self.$el).find("#consumer_company_name").addClass("d-none")
                $(self.$el).find("#consumer_company_document").addClass("d-none")
            }else if(company_type == 'company'){
                $(self.$el).find("#consumer_company_name").removeClass("d-none")
                $(self.$el).find("#consumer_company_document").removeClass("d-none")
            }
        },
        change_consumer_younger:function(ev){
            var self = this;
            var consumer_younger = $(ev.currentTarget).is(':checked')
            console.log(consumer_younger)
            if(consumer_younger){
                $(self.$el).find("#consumer_younger_title").removeClass("d-none")
                $(self.$el).find("#consumer_younger_content").removeClass("d-none")
            }else{
                $(self.$el).find("#consumer_younger_title").addClass("d-none")
                $(self.$el).find("#consumer_younger_content").addClass("d-none")
            }
        }
    });
});
