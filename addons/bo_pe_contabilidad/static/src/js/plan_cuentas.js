odoo.define("plan_cuentas",function(require){
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var PlanCuentas = AbstractAction.extend({
        template:"plan_cuentas",
        start:function(){
            core.bus.on("DOM_updated",this,function(){
                $('#jstree_demo').jstree({
                    "core" : {
                      "animation" : 0,
                      "check_callback" : true,
                      "themes" : { "stripes" : true },
                      'data' : [
                        'Simple root node',
                        {
                            'id' : 'node_2',
                            'text' : 'Root node with options',
                            'state' : { 'opened' : true, 'selected' : true },
                            'children' : [ { 'text' : 'Child 1' }, 'Child 2']
                        }
                    ]
                    },
                    "types" : {
                      "#" : {
                        "max_children" : 1,
                        "max_depth" : 4,
                        "valid_children" : ["root"]
                      },
                      "root" : {
                        "icon" : "/static/3.3.11/assets/images/tree_icon.png",
                        "valid_children" : ["default"]
                      },
                      "default" : {
                        "valid_children" : ["default","file"]
                      },
                      "file" : {
                        "icon" : "glyphicon glyphicon-file",
                        "valid_children" : []
                      }
                    },
                    "plugins" : [
                      "contextmenu", "dnd", "search",
                      "state", "types", "wholerow"
                    ]
                  });
            })
        }
    })

    core.action_registry.add("action_plan_cuentas",PlanCuentas)
    return PlanCuentas

})