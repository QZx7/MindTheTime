var ws = new WebSocket("wss://www.eventchat.tk/event/");
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
    $("#events").html(
    `Gap: ${response.gap} <br>
    Events: ${response.events}`
    );
}
};
// when closes
ws.onclose = function() {
ws.close();
alert("disconnected from server, reconnecting");
ws = new WebSocket("wss://www.eventchat.tk/event/");
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
})