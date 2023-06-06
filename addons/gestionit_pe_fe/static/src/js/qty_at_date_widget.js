odoo.define('QtyAtDateWidgetExtend',function(require){
    "use strict";
    var QtyAtDateWidget = require("sale_stock.QtyAtDateWidget")
    var widget_registry = require('web.widget_registry');

    QtyAtDateWidget = QtyAtDateWidget.extend({
        start:function(){
            // console.log("QtyAtDateWidget.extend")
            // console.log(this.data)
            try {
                this.data.qty_by_loc = JSON.parse(this.data.qty_by_location)    
            } catch (error) {
                this.data.qty_by_loc = []
            }
            
            return this._super()
        }
    })
    
    widget_registry.add('qty_at_date_widget', QtyAtDateWidget);
})