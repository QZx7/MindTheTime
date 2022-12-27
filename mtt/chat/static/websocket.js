var socket_host = "wss://eventchat.tk:443/event"
// var socket_host = "ws://localhost:8888/event"

var ws = new WebSocket(socket_host);
// register self as client
ws.onopen = function() {
message = {
    "type": "initialize",
    "worker_id": $("#workerId").val(),
    "room_id": $("#roomId").val(),
}
ws.send(JSON.stringify(message));
};
// process messages from server
ws.onmessage = function (evt) {
var response = JSON.parse(evt.data);
// if the server send a message resposne
if (response.type == "message") {
    $("#inbox").append(
    `<div class="list-group-item">
        <p class="text-wrap">
        ${response.speaker} : ${response.text}
        </p>
    </div>`
    );
    $("#message").val("").select();
}

// if the server send a disconnection resposne
if (response.type == "partner_disconnect") {
    alert(response.text);
    $("#new_message").prop("disabled", true);
    $("#new_session").prop("disabled", true);
}

// if the server send a session resposne
if (response.type == "session") {
    events_html = `${response.gap} has/have passed. During this time, the following events happened.<br> Events: <br>`
    for (let i = 0; i < response.events.length; i++) {
        events_html += response.events[i] + "<br>"
    }
    $("#events").html(events_html);
}

// if the server send a report response
if (response.type == "report") {
    alert(response.text);
    $("#report_message").val("");
}

};
// when closes
ws.onclose = function() {
ws.close();
alert("disconnected from server, reconnecting");
ws = new WebSocket(socket_host);
};

// event listener for new session
$("#new_session").on("click", function() {
    message = {
        "type": "session",
        "worker_id": $("#workerId").val(),
        "room_id": $("#roomId").val(),
    }
    ws.send(JSON.stringify(message));
});

//event listener for new message
$("#new_message").on("click", function() {
    message = {
        "type": "message",
        "worker_id": $("#workerId").val(),
        "room_id": $("#roomId").val(),
        "message": $("#message").val(),
    }
    ws.send(JSON.stringify(message));
});

//event listener for report
$("#report").on("click", function() {
    message = {
        "type": "report",
        "worker_id": $("#workerId").val(),
        "room_id": $("#roomId").val(),
        "report": $("#report_message").val(),
    }
    ws.send(JSON.stringify(message));
});

//keep websocket alive
setInterval(function () {
    message = {
        "type": "ping",
        "text": "ping"
    }
    ws.send(JSON.stringify(message));
});