// vim:ts=4:sw=4

function getHTTPObject() { 
	var xmlhttp;
	/*@cc_on
	  @if (@_jscript_version >= 5) try {
	  xmlhttp = new ActiveXObject("Msxml2.XMLHTTP"); 
	  } 
	  catch (e) { 
	  try { xmlhttp = new ActiveXObject("Microsoft.XMLHTTP"); } 
	  catch (E) { xmlhttp = false; }
	  } 
	  @else 
	  xmlhttp = false;
	  @end @*/ 
	if (!xmlhttp && typeof XMLHttpRequest != 'undefined') { 
		try {
			xmlhttp = new XMLHttpRequest(); 
		}
		catch (e) {
			xmlhttp = false;
		} 
	}
	return xmlhttp; 
}
function callToggle(id) {
	var http = getHTTPObject();
	http.open("GET", 'toggle?ajax=yes&avatar_id='+id);
	http.onreadystatechange = function() {
		if (http.readyState == 4) { 
			response = http.responseText.replace(/^\s+|\s+$/g, '')
			document.getElementById("on"+id).innerHTML = response;
			if(response == "yes") {
				document.getElementById("av"+id).style.background = "#EEE";
			}
			else {
				document.getElementById("av"+id).style.background = "#CCC";
			}
		}
	}
	http.send(null);
}


