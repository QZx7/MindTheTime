var socket_host = "wss://eventchat.tk:443/match";
// var socket_host = "ws://localhost:8888/match";
var ws = new WebSocket(socket_host);

function showNotificaiton() {
    document.getElementById("match_notification").innerHTML = `<p class="fs-5" style="color: black;">
    This could take a few minutes...</p><p class="fs-5" style="color: black;"> please read through the 
    instruction again while waiting.</p>`;
    document.getElementById("start_match").disabled = true;
}

ws.onopen = function(evt) {
    message = {
        "type": "joined",
        "worker_id": getUrlParameter('workerId'),
    }
    ws.send(JSON.stringify(message));
};

ws.onmessage = function(evt) {
    var response = JSON.parse(evt.data);
    if (response.type == "matching") {
        window.location.href = `/room/id/${response.room_info.room_id}?workerId=${getUrlParameter('workerId')}&assignmentId=${getUrlParameter('assignmentId')}&hitId=${getUrlParameter('hitId')}&turkSubmitTo=${getUrlParameter('turkSubmitTo')}`;
    }
};

ws.onclose = function() {
    ws.close();
}

$("#start_match").on("click", function(e) {
    e.preventDefault();
    message = {
        "type": "matching",
        "worker_id": $("#workerId").val(),
    }
    ws.send(JSON.stringify(message));

    var sec = -1;
    setInterval(function() {
        $("#seconds").html(pad(++sec % 60));
        $("#minutes").html(pad(parseInt(sec / 60, 10) % 60));
    }, 1000);
});

function pad(val) {
    return val > 9 ? val : "0" + val;
}

function getUrlParameter(sParam) {
    var sPageURL = window.location.search.substring(1),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
        }
    }
    return false;
};

//keep websocket alive
setInterval(function() {
    message = {
        "type": "ping",
        "text": "ping"
    }
    ws.send(JSON.stringify(message));
}, 1000 * 15);
