var socket_host = "wss://eventchat.tk:443/event"
// var socket_host = "ws://localhost:8888/event"

var ws = new WebSocket(socket_host);
var session_utterance = 0;
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
        if (response.speaker == $("#workerId").val()) {
            $("#inbox").append(
                `<div class="list-group-item list-group-item-success">
                    <p class="text-wrap">
                    ${response.speaker} : ${response.text}
                    </p>
                </div>`
            );
        }
        else {
            $("#inbox").append(
                `<div class="list-group-item list-group-item-primary">
                    <p class="text-wrap">
                    ${response.speaker} : ${response.text}
                    </p>
                </div>`
            );
        }
        
        $("#inbox_container").scrollTop($("#inbox_container")[0].scrollHeight);
}

// if the server send a disconnection resposne
if (response.type == "partner_disconnect") {
    alert(response.text);
    $("#new_message").prop("disabled", true);
    $("#new_session").prop("disabled", true);
    $("#submit_notification").html(`Thank you for your participating. Your partner might have exited the chat room. To get paid, 
    you need to click the <strong>Finish the HIT and Go Back to AMT</strong> button to submit your HIT.`)
}

// if the partner reconnected
if (response.type == "reconnection") {
    if ( $("#new_message").is(":disabled")) {
        alert("Reconnected!");
        $("#new_message").prop("disabled", false);
        if (session_utterance >= 2) {
            $('#new_session').prop("disabled", false);
        }
    }
}

// if the server send a session resposne
if (response.type == "session") {
    events_html = `${response.gap} has/have passed. During this time, the following events happened.<br> Events: <br>`
    for (let i = 0; i < response.events.length; i++) {
        events_html += response.events[i] + "<br>"
    }
    $("#events").html(events_html);
    $("#inbox").append(
        `<div class="list-group-item list-group-item-dark">
                <p class="text-wrap">
                (The above conversation heppened ${response.gap} ago)
                </p>
        </div>`
    );
    $("#inbox_container").scrollTop($("#inbox_container")[0].scrollHeight);

    if (!$("#time_machine").is(':visible')) {
        $("#time_machine").modal('toggle');
    }
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
    session_utterance = 0;
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
    $("#message").val("").select();
    session_utterance += 1;
    if (session_utterance >= 2) {
        $('#new_session').prop("disabled", false);
    }
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

// event listener for submit check
$('#submitCheck').change(function () {
    if ($('#submitCheck').is(":checked")) {
        $('#hit_submit').prop("disabled", false)
    }
    else {
        $('#hit_submit').prop("disabled", true)
    }
})

//keep websocket alive
setInterval(function () {
    message = {
        "type": "ping",
        "text": "ping"
    }
    ws.send(JSON.stringify(message));
}, 1000 * 15);