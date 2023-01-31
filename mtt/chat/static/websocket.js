var host = window.location.host;
var socket_host = "";
if (host == "localhost:8888") {
    socket_host = "ws://localhost:8888/event";
}else if (host == "eventchat.tk") {
    socket_host = "wss://eventchat.tk:443/event";
}

// the minimum utterance number in each session.
var MINIMUM_UTTERANCE_EACH_SESSION = 20;
// the minimum session to finish this work and get fully paid.
var MINIMUM_SESSION_NUMBER = 7;
// the minimum session to get part of the payment due to the issues on the partner's side.
var MINIMUM_VALID_WORK_SESSION_NUMBER = 5;

$("#min_utterance").html(`${MINIMUM_UTTERANCE_EACH_SESSION}`)
$("#min_session").html(`${MINIMUM_SESSION_NUMBER}`)

var ws = new WebSocket(socket_host);
var session_utterance = 0;
var session_number = 0
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
                        You : ${response.text}
                    </p>
                </div>`
            );
        }
        else {
            $("#inbox").append(
                `<div class="list-group-item list-group-item-primary">
                    <p class="text-wrap">
                        Your partner : ${response.text}
                    </p>
                </div>`
            );
        }
        session_utterance += 1;
        $("#inbox_container").scrollTop($("#inbox_container")[0].scrollHeight);
    }

    // if the server send a disconnection resposne
    if (response.type == "partner_disconnect") {
        alert(response.text);
        $("#new_message").prop("disabled", true);
        $("#new_session").prop("disabled", true);
        // $("#submit_notification").html(`Thank you for your participation. Your partner might have exited the chat room. To get paid, 
        // you need to click the <strong>Submit the HIT and Go Back to AMT</strong> button to submit your HIT.`)
        if (session_number >= MINIMUM_VALID_WORK_SESSION_NUMBER && session_number < MINIMUM_SESSION_NUMBER) {
            $("#submit_notification").html(`You and your partner have finished ${session_number} session(s). However, you
            have not finished at least ${MINIMUM_SESSION_NUMBER} sessions yet. This might be caused by your partner, e.g., your 
            partner has disconnected. If this is the case please write in the report textarea and hit the Report buttion.`)
        } else if (session_number >= MINIMUM_SESSION_NUMBER) {
            $("#submit_notification").html(`Thank you for your participation. Your partner might have exited the chat room. You have
        finished at least ${MINIMUM_SESSION_NUMBER} sessions. Please click the <strong>Submit the HIT</strong> button to submit your task.`)
        } else if (session_number < MINIMUM_VALID_WORK_SESSION_NUMBER) {
            $("#submit_notification").html(`Your partner might have disconnected from the chatting room. Please exit the HIT and re-do the matching
            from the beginning.`)
        }
    }

    // if the partner reconnected
    if (response.type == "reconnection") {
        if ( $("#new_message").is(":disabled")) {
            alert("Reconnected!");
            $("#new_message").prop("disabled", false);
            $("#submit_notification").html(``);
            if (session_utterance >= MINIMUM_UTTERANCE_EACH_SESSION) {
                $('#new_session').prop("disabled", false);
            }
        }
    }

    // if the server send a session resposne
    if (response.type == "session") {
        session_number += 1;
        $("#sessions_finished").html(`Sessions you have finished: ${session_number}`)
        session_utterance = 0;
        events_html = `<p>${response.gap} has/have passed. During this time, the following events happened.<br> <strong>Finished Progress: </strong> <br>`
        for (let i = 0; i<response.events.progress.length; i++) {
            events_html += response.events.progress[i] + "<br>"
        }
        events_html += "<strong>Life Events: </strong><br>"
        for (let i = 0; i < response.events.life_events.length; i++) {
            events_html += response.events.life_events[i] + "<br>"
        }
        events_html += "<strong>World Events: </strong><br>"
        for (let i = 0; i < response.events.world_events.length; i++) {
            events_html += response.events.world_events[i] + "<br>"
        }
        events_html += "<strong>Future Plans: </strong><br>"
        for (let i = 0; i < response.events.plans.length; i++) {
            events_html += response.events.plans[i] + "<br>"
        }
        events_html += "</p>"
        $("#events").html(events_html);
        $("#inbox").append(
            `<div class="list-group-item list-group-item-dark">
                    <p class="text-wrap">
                    (The above conversation was ${response.gap} ago)
                    </p>
            </div>`
        );
        $("#inbox_container").scrollTop($("#inbox_container")[0].scrollHeight);

        if (!$("#time_machine").is(':visible')) {
            $("#time_machine").modal('toggle');
        }

        $('#new_session').prop("disabled", true);
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
    // session_utterance = 0;
    // session_number += 1;
    // $('#new_session').prop("disabled", true);
    if (session_number >= MINIMUM_SESSION_NUMBER) {
        $('#submit_notification').html(`<p>You are able to submit now as you have finished the minimum number of sessions. But you could be rewarded
        to finish the conversations as natural as possible if more sessions are necessary. </p>`)
    }
});

//event listener for new message
$("#new_message").on("click", function() {
    if ($("#message").val() == "") {
        alert("Message can't be empty.")
    } else {
        message = {
            "type": "message",
            "worker_id": $("#workerId").val(),
            "room_id": $("#roomId").val(),
            "message": $("#message").val(),
        }
        ws.send(JSON.stringify(message));
        $("#message").val("").select();
        // session_utterance += 1;
        if (session_utterance >= MINIMUM_UTTERANCE_EACH_SESSION) {
            $('#new_session').prop("disabled", false);
        }
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
    if ($('#submitCheck').is(":checked") && (session_number >= MINIMUM_SESSION_NUMBER)) {
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