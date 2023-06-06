odoo.define('custom_pos_bo.popups', function (require) {
    "use strict";
    var PopupWidget = require('point_of_sale.popups');
    var gui = require('point_of_sale.gui');
    var rpc = require('web.rpc');
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');

    var CreateRemissionGuide = PopupWidget.extend({
        'template': 'remission_guide_info',
        show: function (options) {
            var self = this;
            options = options || {};
            this._super(options);
        },
        'events': {
            'change select[id="remission_guide_department"]':"change_department",
            'change select[id="remission_guide_district"]':"change_district",
            'change select[id="remission_guide_province"]':"change_province",
            'click .save': function () {
                let starting_address = $(this.$el).find("input[id='remission_guide_starting_address']");
                let remission_guide_arrival_address = $(this.$el).find("input[id='remission_guide_arrival_address']");
                let remission_guide_weight = $(this.$el).find("input[id='remission_guide_weight']");
                let remission_guide_department = $(this.$el).find("select[id='remission_guide_department']");
                let remission_guide_province = $(this.$el).find("select[id='remission_guide_province']");
                let remission_guide_district = $(this.$el).find("select[id='remission_guide_district']");
                let remission_guide_ubigeo = $(this.$el).find("input[id='remission_guide_ubigeo']");
                let remission_guide_transport_companys = $(this.$el).find("select[id='remission_guide_transport_companys']");
                let remission_guide_driver = $(this.$el).find("select[id='remission_guide_driver']");
                let remission_guide_car = $(this.$el).find("select[id='remission_guide_car']");
                let self = this;
                rpc.query({
                    model: 'pos.order',
                    method: 'print_guia',
                    args:[self.options.data.order,starting_address.val(), remission_guide_arrival_address.val(), remission_guide_weight.val(), remission_guide_department.val(), remission_guide_province.val(), remission_guide_district.val(), remission_guide_ubigeo.val(), remission_guide_transport_companys.val(), remission_guide_driver.val(), remission_guide_car.val()]
                }).then(function (res) {
                    let win = window.open(res, '_blank');
                    win.focus();
                    self.gui.close_popup();
                })
            },
            'click .cancel': function () {
                this.gui.close_popup();
            }

        },
        change_department: function () {
            let self = this;
            let remission_guide_department = $(this.$el).find("select[id='remission_guide_department']");
            let remission_guide_province = $(this.$el).find("select[id='remission_guide_province']");
            let remission_guide_district = $(this.$el).find("select[id='remission_guide_district']");
            let remission_guide_ubigeo = $(this.$el).find("input[id='remission_guide_ubigeo']");
            rpc.query({
                model: 'pos.order',
                method: 'get_ubigeo_guia',
                args:[self.options.data.order, remission_guide_department.val(), remission_guide_province.val(), remission_guide_district.val()]
            }).then(function (res) {
                remission_guide_province.empty();
                remission_guide_district.empty();
                for (let sel in res.provinces) {
                    let province = res.provinces[sel];
                    const option = document.createElement('option');
                    option.value = province[0];
                    option.text = province[1];
                    remission_guide_province.append(option);
                }
                for (let sel in res.districts) {
                    let district = res.districts[sel];
                    const option = document.createElement('option');
                    option.value = district[0];
                    option.text = district[1];
                    remission_guide_district.append(option);
                }
                remission_guide_ubigeo.val(res.ubigeo)
                remission_guide_district.val(res.district_id)
                remission_guide_province.val(res.province_id)
            });
        },
        change_district: function () {
            let self = this;
            let remission_guide_department = $(this.$el).find("select[id='remission_guide_department']");
            let remission_guide_province = $(this.$el).find("select[id='remission_guide_province']");
            let remission_guide_district = $(this.$el).find("select[id='remission_guide_district']");
            let remission_guide_ubigeo = $(this.$el).find("input[id='remission_guide_ubigeo']");
            rpc.query({
                model: 'pos.order',
                method: 'get_ubigeo_guia',
                args:[self.options.data.order, remission_guide_department.val(), remission_guide_province.val(), remission_guide_district.val()]
            }).then(function (res) {
                remission_guide_province.empty();
                remission_guide_district.empty();
                for (let sel in res.provinces) {
                    let province = res.provinces[sel];
                    const option = document.createElement('option');
                    option.value = province[0];
                    option.text = province[1];
                    remission_guide_province.append(option);
                }
                for (let sel in res.districts) {
                    let district = res.districts[sel];
                    const option = document.createElement('option');
                    option.value = district[0];
                    option.text = district[1];
                    remission_guide_district.append(option);
                }
                remission_guide_ubigeo.val(res.ubigeo)
                remission_guide_district.val(res.district_id)
                remission_guide_province.val(res.province_id)
            });
        },
        change_province: function () {
            let self = this;
            let remission_guide_department = $(this.$el).find("select[id='remission_guide_department']");
            let remission_guide_province = $(this.$el).find("select[id='remission_guide_province']");
            let remission_guide_district = $(this.$el).find("select[id='remission_guide_district']");
            let remission_guide_ubigeo = $(this.$el).find("input[id='remission_guide_ubigeo']");
            rpc.query({
                model: 'pos.order',
                method: 'get_ubigeo_guia',
                args:[self.options.data.order, remission_guide_department.val(), remission_guide_province.val(), remission_guide_district.val()]
            }).then(function (res) {
                remission_guide_province.empty();
                remission_guide_district.empty();
                for (let sel in res.provinces) {
                    let province = res.provinces[sel];
                    const option = document.createElement('option');
                    option.value = province[0];
                    option.text = province[1];
                    remission_guide_province.append(option);
                }
                for (let sel in res.districts) {
                    let district = res.districts[sel];
                    const option = document.createElement('option');
                    option.value = district[0];
                    option.text = district[1];
                    remission_guide_district.append(option);
                }
                remission_guide_ubigeo.val(res.ubigeo)
                remission_guide_district.val(res.district_id)
                remission_guide_province.val(res.province_id)
            });
        },
        renderElement: function () {
            this._super();
            let self = this
        },
    });
    gui.define_popup({name: 'create_remission_guide_popup', widget: CreateRemissionGuide});

    screens.ReceiptScreenWidget.include({
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.button.guide').click(function(){
                let orderId = self.pos.get_order();
                rpc.query({
                    model: 'pos.order',
                    method: 'get_fields_popup_guia',
                    args:[orderId.pos_order_id]
                }).then(function (res) {
                    if (res) {
                        self.pos.gui.show_popup('create_remission_guide_popup', {
                            'order': self.pos.get_order().number,
                            'session': self.pos.pos_session.id,
                            'data':res
                        });
                    }
                });
            });
        },

    });
});
