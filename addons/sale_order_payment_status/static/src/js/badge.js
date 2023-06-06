odoo.define("sale_order_payment_status.badge_fields", function (require) {
    "use strict";

    var basic_fields = require("web.basic_fields");
    var FieldChar = basic_fields.FieldChar;
    var core = require("web.core");
    var fieldRegistry = require("web.field_registry");

    var _lt = core._lt;

    var FieldBadge = FieldChar.extend({
        template: "sale_order_payment_status.FieldBadge",
        description: _lt("Badge"),
        supportedFieldTypes: ["selection", "many2one", "char"],

        //   _setDecorationClasses
        _applyDecorations() {
            var self = this;
            this.attrs.decorations.forEach(function (dec) {
                var isToggled = py.PY_isTrue(py.evaluate(dec.expression, self.record.evalContext));
                var className = `badge-${dec.className.split("-")[1]}`;
                self.$el.toggleClass(className, isToggled);
            });
        },
    });

    fieldRegistry.add("badge", FieldBadge);

    return FieldBadge;
});
