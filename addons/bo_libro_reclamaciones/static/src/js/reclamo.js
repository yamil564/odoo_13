odoo.define('bo_libro_reclamaciones.create_reclamos',function(require){
    'use strict';
    var publicWidget = require("web.public.widget")
    var rpc = require("web.rpc")
    var core = require("web.core")
    var qweb = core.qweb
    var ajax = require("web.ajax")
    var _t = core._t;
    var Widget = require("web.Widget")
    var session = require("web.session")

    publicWidget.registry.ExamAnswers = publicWidget.Widget.extend({
        selector: ".exam",
        events:{
            'click .btn_enviar_tarea':'nueva_tarea',
            'change #attachment':'change_attachemnt',
        },
        start: function () {
            this.examid = $(this.$el).data("examid");
        },
        send_answers: function (ev) {
            if (confirm("¿Estás seguro de querer enviar tus respuestas?")) {
                var self = this;
                var questions = $(self.$el).find(".question");
                var respuestas = [];

                for (let i = 0; i < questions.length; i++) {
                    var respuesta = {
                        question_id: $(questions[i]).data("questionid"),
                        answer_id: parseInt(
                            $(questions[i])
                                .find(".form-check-input:checked")
                                .val()
                        ),
                    };
                    respuestas.push(respuesta);
                }

                rpc.query({
                    model: "ap.exam",
                    method: "validar_respuestas",
                    args: ["", [self.examid, respuestas]],
                }).then(function (res) {
                    $(self.$el)
                        .find(".form-check-input")
                        .parent()
                        .removeClass("text-dark bg-danger bg-success");
                    if (res.success) {
                        $(self.$el)
                            .find(".form-check-input:checked")
                            .parent()
                            .addClass("text-dark bg-danger");
                        for (let i = 0; i < res.correctas.length; i++) {
                            $(self.$el)
                                .find("#answer_" + res.correctas[i])
                                .removeClass("bg-danger")
                                .addClass("text-dark bg-success");
                        }

                        $(self.$el)
                            .find(".btn_send_answers")
                            .addClass("d-none");
                        $(self.$el)
                            .find(".btn_back_course")
                            .removeClass("d-none");
                        $(self.$el).find(".calificacion").text(res.nota);
                    }
                });
            } else {
                console.log("Thing was not saved to the database.");
            }
        },
    });
});
