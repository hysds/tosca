    function is_supported(){
       
    var is_chrome = navigator.userAgent.indexOf('Chrome') > -1;
    var is_explorer = navigator.userAgent.indexOf('MSIE') > -1;
    var is_firefox = navigator.userAgent.indexOf('Firefox') > -1;
    var is_safari = navigator.userAgent.indexOf("Safari") > -1;
    var is_opera = navigator.userAgent.toLowerCase().indexOf("op") > -1;
    if ((is_chrome)&&(is_safari)) {is_safari=false;}
    if ((is_chrome)&&(is_opera)) {is_chrome=false;}

    return is_chrome || is_firefox  

}

    function check_browser(){
        var isSupported=is_supported()
         if(!isSupported){
        var close_icon='<span class="closebtn" onclick="this.parentElement.style.display='  + "'none';" +' ">&times;</span>'
        var alert_msg = "We recommend using Chrome or Firefox browser as other browsers may offer degraded performance."
        var alert_panel= '<div class="alertbrowser">' + close_icon + alert_msg+'</div>' 
            document.write(alert_panel)
         }

   }
