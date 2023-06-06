function buscar_documento() {
    console.log("buscando doc");
    var data = {
            "serie": $("#serie").val(),
            "correlativo": $("#correlativo").val(),
            "fecha":$("#fecha").val(),
            "ruc":$("#ruc").val(),
            "total":$("#total").val()

    }
    $.post("/busqueda", data).done(function(response) {
        $("#documento").html(response)
    })
}

$(function(){
    $('form').submit(function(event){
        event.preventDefault()
        console.log("submi")
  })
});