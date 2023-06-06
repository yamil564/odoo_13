odoo.define("select_invoice_from_website.website_sale",function(require){
    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    var WebsiteSaleSuper = publicWidget.registry.WebsiteSale.prototype

    publicWidget.registry.WebsiteSale = publicWidget.registry.WebsiteSale.extend({

        events:_.extend({},WebsiteSaleSuper.events,{
            "change input[name='vat']":"change_vat",
            "change input[name='invoice_type_code']":"change_invoice_type_code",
            "change input[name='l10n_latam_identification_type_id']:checked":"click_l10n_latam_identification_type_id",
            'change input[name="country_id"]': '_onChangeCountry',
        }),

        start:function(){
            var def = this._super.apply(this, arguments);
            this.$('select[id="country"]').trigger("change");
            this.$('input[name="l10n_latam_identification_type_id"]').trigger("change");
            return def
        },

        _changeCountry:function(){
            if (!$("#country_id").val()) {
                return;
            }
            this._rpc({
                route: "/shop/country_infos/" + $("#country_id").val(),
                params: {
                    mode: 'shipping',
                },
            }).then(function (data) {
                $(".div_state").css("display","")
                $("input[name='state_name']").autocomplete({
                    minLength:3,
                    source:_.map(data.states,function(el){return {id:el[0],value:el[1]}}),
                    select:function(ev,ui){
                        $("input[name='state_id']").val( ui.item.id );
                        return false;
                    }
                })
            })
        },

        change_invoice_type_code:function(ev){
            var invoice_type_code = $(ev.currentTarget).val()
            this._rpc({
                route:"/change_invoice_type_code",
                params:{
                    "invoice_type_code":invoice_type_code
                }
            }).then(function(res){
                return true
            })
        },

        click_l10n_latam_identification_type_id:function(ev){
            var itc = $(ev.currentTarget).data("itc")
            $("input[type='radio'][name='invoice_type_code']:checked").attr("checked",false)
            // $("input[name='invoice_type_code']").trigger("change")
            if(itc=="6"){
                $(".div_company label").removeClass("label-optional")
                $(".div_country label").removeClass("label-optional")
                $(".div_state label").removeClass("label-optional")
                $(".div_street label").removeClass("label-optional")
                $("input[value='01']").attr("checked",true).trigger("change")

            }else{
                $(".div_company label").addClass("label-optional")
                $(".div_country label").addClass("label-optional")
                $(".div_street label").addClass("label-optional")
                $(".div_state label").addClass("label-optional")
                $("input[value='03']").attr("checked",true).trigger("change")
            }

            if(itc == "0"){
                $("input[name='vat']").val("0")
                $("div_vat").addClass("d-none")
            }
            // else{
            //     $("input[name='vat']").val("")
            //     $("div_vat").removeClass("d-none")
            // }
            if(itc == "1" || itc == "7" || itc == "4"){
                $(".div_company").addClass("d-none")
            }else{
                $(".div_company").removeClass("d-none")
            }
        },

        change_vat: function(){
          var type = $("input[type='radio'][name='l10n_latam_identification_type_id']:checked").val();
          var vat = $('#vat').val();
          var country = $('#country').val()
          var self = this
          ajax.jsonRpc('/change_vat', 
                        'call', 
                        {'type': type, 'vat': vat, 'country': country})
            .then(function (result) {
              if (result.validate){
                $('#country').val(result["country"]);
                $('#departamento').val(0)
                $('#provincia').val(0)
                $('#distrito').val(0)

                  if (result.name && $('#name_aux').val() == ""){
                    $('#name_aux').val(result['name'])
                  }

                  if (result.address && $('#street_aux').val() == ""){
                    $('#street_aux').val(result['address'])
                  }

                  if (result.razon){
                    $('#company_name').val(result['razon'])
                  }

                  if (result.country){
                    $('#country').val(result['country'])
                    ajax.jsonRpc('/get-departamento', 'call',
                     {'pais': result['country']}).then(function (data) {
                            for (let i = 0; i < data.length; i++) {
                                $(self.$el).find("#departamento").append($('<option /}>').val(data[i].id).text(data[i].name));
                                if (data[i].id == result['departamento']){
                                    $('#departamento').val(data[i].id)
                                }
                            }
                    })
                  }

                  if (result.department){
                    $('#departamento').val(result['department'])
                    ajax.jsonRpc('/get-provincia', 'call',
                     {'departamento': result['department']}).then(function (data) {
                            for (let i = 0; i < data.length; i++) {
                                $(self.$el).find("#provincia").append($('<option /}>').val(data[i].id).text(data[i].name));
                                if (data[i].id == result['province']){
                                    $('#provincia').val(data[i].id)
                                }
                            }
                    })
                  }

                  if (result.province){
                    $('#provincia').val(result['province'])
                    ajax.jsonRpc('/get-distrito', 'call',
                     {'provincia': result['province']}).then(function (data) {
                            for (let i = 0; i < data.length; i++) {
                                $(self.$el).find("#distrito").append($('<option /}>').val(data[i].id).text(data[i].name));
                                if (data[i].id == result['district']){
                                    $('#distrito').val(data[i].id)
                                }
                            }
                    })
                  }

                  if (result.district){
                    $('#distrito').val(result['district'])
                  }

                  $("#vat").blur(function(){
                    $(this).css({"background":"transparent"})
                  })
              }else{
                $("#vat").css("background-color", "pink");
                $('#name_aux').val("")
                $('#company_name').val("")
                $('#street_aux').val("")
              }
          });
        },

    })
})
