odoo.define("gestionit_pe_fe_pos.DB",[
    "point_of_sale.DB",
],function(require){
    "use strict";
    var PosDB = require("point_of_sale.DB")
    var PosDBSuper = PosDB.prototype
    
    
    PosDB = PosDB.extend({
        init: function(options) {
            this.journal_ids = []
            this.journal_by_id = {};
            this.sequence_by_id = {};
            this.identification_type_by_id = {};
            this.journal_sequence_by_id = {};
            this.invoice_numbers=[];
            this.credit_note_types = [
                {id:"06",name:"Devolución Total",code:"06",display_name:"Devolución Total"},
                {id:"07",name:"Devolución por Item",code:"07",display_name:"Devolución por Item"},
                {id:"02",name:"Anulación de la operación",code:"02",display_name:"Anulación de la operación"}
            ];
            return PosDBSuper.init.apply(this, arguments);
        },
        add_invoice_numbers: function(number) {
            if (number) {
                var invoice_numbers = this.load('invoice_numbers') || [];
                invoice_numbers.push(number);
                this.save('invoice_numbers', invoice_numbers || null);
            }
        },
        get_invoice_numbers: function() {
            return this.load('invoice_numbers') || [];
        },
        add_journals: function(journals) {
            if (!journals instanceof Array) {
                journals = [journals];
            }
            for (var i = 0, len = journals.length; i < len; i++) {
                this.journal_ids = journals
                this.journal_by_id[journals[i].id] = journals[i];
                this.journal_sequence_by_id[journals[i].id] = journals[i].sequence_id[0];
            }
        },
        add_sequences: function(sequences) {
            if (!sequences instanceof Array) {
                sequences = [sequences];
            }
            for (var i = 0, len = sequences.length; i < len; i++) {
                this.sequence_by_id[sequences[i].id] = sequences[i];
            }
        },
        add_identification_types: function(identification_types){
            for (var i = 0, len = identification_types.length; i < len; i++) {
                this.identification_type_by_id[identification_types[i].id] = identification_types[i];
            }
        },
        get_journal_sequence_id: function(journal_id) {
            var sequence_id = this.journal_sequence_by_id[journal_id]
            return this.sequence_by_id[sequence_id] || {};
        },
        get_journal_by_id: function(journal_id) {
            return this.journal_by_id[journal_id];
        },
        set_sequence_next: function(id, number_increment) {
            var sequences = this.load('sequences') || {};
            sequences[id] = number_increment + 1;
            this.save('sequences', sequences || null);
        },
        get_sequence_next: function(journal_id) {
            var sequence_id = this.journal_sequence_by_id[journal_id];

            var sequences = this.load('sequences') || {};
            if (sequences[sequence_id]) {
                if (this.sequence_by_id[sequence_id].number_next_actual > sequences[sequence_id]) {
                    return this.sequence_by_id[sequence_id].number_next_actual;
                } else {
                    return sequences[sequence_id];
                }
            } else {
                return this.sequence_by_id[sequence_id].number_next_actual;
            }
        },
        set_credit_note_types:function(credit_note_types){
            this.credit_note_types = credit_note_types
        },
        get_credit_note_types:function(){
            return this.credit_note_types
        },
        get_credit_note_type_by_code:function(code){
            return _.find(this.credit_note_types,function(el){return el.code == code})
        },
        get_credit_note_type_by_id:function(id){
            return _.find(this.credit_note_types,function(el){return el.id == id})
        },
    });

    return PosDB


})