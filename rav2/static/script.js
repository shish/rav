function callToggle(id) {
	fetch('toggle?ajax=yes&avatar_id='+id)
		.then((response) => response.text())
		.then((response) => {
			document.getElementById("on"+id).innerHTML = response;
			document.getElementById("av"+id).style.background = (response == "yes") ? "#EEE" : "#CCC";
		});
}
