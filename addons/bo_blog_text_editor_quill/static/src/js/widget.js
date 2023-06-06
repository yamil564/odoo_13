odoo.define("bo_blog_text_editor_quill.widget", function(require){
    var widget = require("web.public.widget")

    Quill.register("modules/imageUploader", ImageUploader);

    hljs.configure({
        useBR:false,
        languages: ['bash', 'javascript', 'python','html']
    });

    widget.registry.QuillTextEditor = widget.Widget.extend({
        selector:".quill_text_editor",
        events:{
            "click .btn_blog_save":"save"
        },
        start:function(){
            var self = this;
            $(this.$el).find(".btn_blog_save").removeClass("d-none")

            const fullToolbarOptions = [
                [{ 'header': 1 }, { 'header': 2 }], 
                [{ 'align':['center','right','justify']},{ 'size': [ 'small', false, 'large', 'huge' ]},'direction'],
                [{ 'indent': '-1'}, { 'indent': '+1' }], 
                ['background','bold', 'italic', 'underline', 'strike','underline'],
                ["clean"],
                ["image"],
                ['code-block']
            ];
            var options = {
                theme: 'snow',
                modules:{
                    syntax: true,
                    toolbar: {
                        container: fullToolbarOptions,
                    },
                    imageResize:{
                        displaySize: true,
                    },
                    imageUploader:{
                        upload: (file) => {
                            return new Promise((resolve, reject) => {
                                var reader = new FileReader();
                                reader.onloadend = function () {
                                    self._rpc({
                                        model:"ir.attachment",
                                        method:"create",
                                        args:[{
                                            type:"binary",
                                            public:true,
                                            name:file.name,
                                            mimetype:file.type,
                                            file_size:file.size,
                                            datas:reader.result.replace(/^data:.+;base64,/, '')
                                        }]
                                    }).then(function(res){
                                        if(res){
                                            resolve(window.location.origin+"/web/content/"+String(res))
                                        }else{
                                            reject("Error al cargar la imagen")
                                        }
                                    })
                                }
                                reader.readAsDataURL(file);
                            })
                        },
                    }
                },
            };
            this.quill = new Quill(".blog_post_content",options); 
            this._super()
        },
        save:function(ev){
            var blog_id = $(this.$el).data("blog-id");
            var content = this.quill.root.innerHTML.trim();

            $(ev.currentTarget).attr("disabled", true);
            $(".blog_msg").text("Guardando ... ")
            this._rpc({
                model:"blog.post",
                method:"write",
                args:[[blog_id],{content}]
            }).then(function(res){
                setTimeout(function(){
                    $(ev.currentTarget).attr("disabled", false);
                    $(".blog_msg").text("");
                },1000)
            }).catch(function(res){
                $(ev.currentTarget).attr("disabled", false);
                $(".blog_msg").text("Se ha producido un error, vuelva a intentarlo.");
            })
        }
    })
})