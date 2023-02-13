import asyncio
import tornado.locks
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.gen
import os.path
import json
import random
import datetime
import uuid

from tornado.options import define, options, parse_command_line
from tornado import ioloop
from concurrent.futures import ThreadPoolExecutor
from typing import Text, Dict, List, Any, Optional, Union, Tuple

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
LOG_PATH = os.path.join(os.path.dirname(__file__), "log")
CURRENT_TIME = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def read_event(filename: Text):
    print("loading events ....")
    file_path = os.path.join(DATA_PATH, filename)
    with open(file_path, "r", encoding="utf-8") as file:
        return json.loads(file.read())


def move_forward() -> Union[Text, Text]:
    """Move the time machine forward to a random period of time.

    Returns:
        Union[Text, Text]: Replace the time gap and its duration key.
    """
    possible_units = ["minute", "hour", "day", "week", "month", "year"]
    duration = random.randint(0, len(possible_units) - 1)
    gap = ""
    duration_key = ""

    if duration == 0:
        gap_number = random.randint(1, 59)
        gap = f"{gap_number} minutes" if gap_number > 1 else "1 minute"
    elif duration == 1:
        gap_number = random.randint(1, 23)
        gap = f"{gap_number} hours" if gap_number > 1 else "1 hour"
    elif duration == 2:
        gap_number = random.randint(1, 5)
        gap = f"{gap_number} days" if gap_number > 1 else "1 day"
    elif duration == 3:
        gap_number = random.randint(1, 3)
        gap = f"{gap_number} weeks" if gap_number > 1 else "1 week"
    elif duration == 4:
        gap_number = random.randint(1, 11)
        gap = f"{gap_number} months" if gap_number > 1 else "1 month"
    elif duration == 5:
        gap = "1 year"

    duration_key = possible_units[duration]
    return gap, duration_key


def get_initial_progress(
    event_dict: Dict[
        Text,
        Dict[Text, Union[int, Text, List[List[Dict[Text, Union[Text, List[Text]]]]]]],
    ]
) -> Dict:
    """Get the initial events.

    Args:
        event_dict (Dict[Text, List[Text]]): The pre-defined initial events list.

    Returns:
        List[Text]: A list of initial events.
    """
    initial_event = random.choice(list(event_dict.values()))
    return initial_event


def time_to_minutes(time: Text) -> int:
    """Convert the time to minutes.

    Args:
        time (Text): Input time.

    Returns:
        int: Time in minutes.
    """
    time_parts = time.split(" ")
    time_number = int(time_parts[0])
    time_unit = time_parts[1]

    assert (
        "minute" in time_unit
        or "hour" in time_unit
        or "day" in time_unit
        or "week" in time_unit
        or "month" in time_unit
        or "year" in time_unit
    )
    multiplyer = 1
    if "hour" in time_unit:
        multiplyer *= 60
    elif "day" in time_unit:
        multiplyer = multiplyer * 60 * 24
    elif "week" in time_unit:
        multiplyer = multiplyer * 60 * 24 * 7
    elif "month" in time_unit:
        multiplyer = multiplyer * 60 * 24 * 30
    elif "year" in time_unit:
        multiplyer = multiplyer * 60 * 24 * 365

    return time_number * multiplyer


def schedule_time_to_minutes(time: Text) -> int:
    """Convert timestamps in the shcedule into minutes.

    Args:
        time (Text): The text version timestamp.

    Returns:
        int: Converted time in minutes.
    """

    def single_time_to_minutes(time: Text) -> int:
        time_parts = time.split(":")
        time_number = int(time_parts[1])
        time_unit = time_parts[0]

        assert (
            "H" in time_unit or "D" in time_unit or "W" in time_unit or "M" in time_unit
        )
        multiplyer = 1
        if "M" in time_unit:
            multiplyer = multiplyer * 60 * 24 * 30
        elif "W" in time_unit:
            multiplyer = multiplyer * 60 * 24 * 7
        elif "D" in time_unit:
            multiplyer = multiplyer * 60 * 24
        elif "H" in time_unit:
            multiplyer *= 60
        return time_number * multiplyer

    schedule_time = 0
    if "|" in time:
        key_parts = time.split("|")
        for key in key_parts:
            schedule_time += single_time_to_minutes(key)
    else:
        schedule_time = single_time_to_minutes(time)

    return schedule_time


def get_next_progress(
    event: Dict[
        Text, Union[int, Text, List[List[Dict[Text, Union[Text, List[Text]]]]]]
    ],
    gap_time: int,
    start_time: int,
) -> Tuple[List[Text], List[Text], bool]:
    """Get the next progress as described in a given progress schedule.

    Args:
        event (Dict[ Text, Union[int, Text, List[List[Dict[Text, Union[Text, List[Text]]]]]] ]): The progress schedule
        gap_time (int): The gap time generated by time machine.
        start_time (int): The beginning time of the time schedule.

    Returns:
        List[Text]: _description_
    """
    finish_status = False
    progress = []
    next = []
    schedule = event["schedules"][0]
    print(f"Schedule: {schedule}")
    # if the gap covers the whole schedule
    if schedule_time_to_minutes(schedule[-1]["schedule_time"]) < start_time + gap_time:
        print(schedule[-1]["schedule_time"])
        finish_status = True
        progress = ["You finished the previous progress and started the following new event."]

    # else
    else:
        for index in range(len(schedule)):
            print(schedule[index]["schedule_time"])
            schedule_time = schedule_time_to_minutes(schedule[index]["schedule_time"])
            if schedule_time >= (start_time + gap_time):
                next = schedule[index]["schedule_content"]
                if index > 0 and start_time < schedule_time_to_minutes(
                    schedule[index - 1]["schedule_time"]
                ):
                    progress = schedule[index - 1]["schedule_content"]
                else:
                    progress = ["No significant progress."]
                break

    return progress, next, finish_status


def get_life_events(
    event_dict: Dict[Text, List[Text]], duration_key: Text, events_number: int
) -> List[Text]:
    """Get a list of life events based on the duration key.

    Args:
        event_dict (Dict[Text, List[Text]]): The pre-defined life events list.
        duration_key (Text): The duration key.
        events_number (int): The number of life events to generate.

    Returns:
        List[Text]: A list of life events.
    """
    if duration_key in event_dict:
        events = random.sample(event_dict[duration_key], k=events_number)
        return events


def get_world_events(
    event_dict: Dict[Text, List[Text]], event_number: int
) -> List[Text]:
    """Get a list of world events.

    Args:
        event_dict (Dict[Text, List[Text]]): The pre-defined news list.
        event_number (int): The number of world events.

    Returns:
        List[Text]: A list of world events
    """
    events = random.sample(event_dict["news"], k=event_number)
    return events


def get_random_future_plans(
    event_dict: Dict[Text, List[Text]], event_number: int
) -> List[Text]:
    events = random.sample(event_dict["plan"], k=event_number)
    return events


# Global arguments to manage the server and rooms
executor = ThreadPoolExecutor(4)
global_user_pool = {}
matching_queue = []
global_room_id = 0
global_room_pool = {}
global_message_dict: Dict[int, List[Dict[Text, Text]]] = {}

# Event
progress_dict = read_event("progress.json")
life_event_dict = read_event("life_events.json")
world_event_dict = read_event("world_events.json")
future_plan_dict = read_event("future_plans.json")
global_event_dict: Dict[
    int,
    Dict[
        Text,
        Union[
            List[Text],
            Dict[Text, List[Dict[Text, Union[Text, List[Dict[Text, List[Text]]]]]]],
        ],
    ],
] = {}


def match(workerId: Text):
    """The matching function for a worker

    Args:
        workerId (Text): submit workerId for matching

    Returns:
        _type_: Room information if matched
    """
    # print("start matching...")
    global matching_queue
    global global_room_id
    # while True:
    # If this user is already matched with other user
    if (
        global_user_pool[workerId]["is_matching"] == False
        and global_user_pool[workerId]["matched"]
    ):
        room_id = global_user_pool[workerId]["room_id"]
        room_info = {
            "room_id": room_id,
            "speaker_1": global_room_pool[room_id]["speaker_1"],
            "speaker_2": global_room_pool[room_id]["speaker_2"],
        }
        return room_info

    # if this user is not matched with anyone else, match this user with the
    # first person in the queue.
    if len(matching_queue) >= 2:
        # global settings
        speaker_1 = workerId
        matching_queue.remove(workerId)
        speaker_2 = matching_queue.pop(0)

        # create save file for this room
        save_location = os.path.join(LOG_PATH, CURRENT_TIME + f"-{global_room_id}.log")
        f = open(save_location, "a")
        f.write(f"Room Id: {global_room_id} \n")
        f.close()

        global_room_pool[global_room_id] = {
            "speaker_1": speaker_1,
            "speaker_2": speaker_2,
            "save_location": save_location,
        }

        # worker settings
        global_user_pool[speaker_1]["is_matching"] = False
        global_user_pool[speaker_1]["room_id"] = global_room_id
        global_user_pool[speaker_1]["matched"] = True

        global_user_pool[speaker_2]["is_matching"] = False
        global_user_pool[speaker_2]["room_id"] = global_room_id
        global_user_pool[speaker_2]["matched"] = True

        # self
        room_info = {
            "room_id": global_room_id,
            "speaker_1": speaker_1,
            "speaker_2": speaker_2,
            "save_location": save_location,
        }
        global_room_id += 1
        return room_info
    else:
        return None


def log_request(
    room_id: int,
    workId: Text,
    assignmentId: Text = "",
    log_type: Text = "chat",
    event_status: Optional[Text] = "initial",
    chat_text: Optional[Text] = "",
):
    """Log the coming request from a client.

    Args:
        room_id (int): The room id of current client.
        workId (Text): The worker id of current client.
        event_status (Optional[Text]): If logging events, set this to 'initial' or <session number>. Defaults to "initial"
        chat_text (Optional[Text]): If logging chat, set this to the message. Defaults to empty string.
        log_type (Text, optional): Choose to log "events" or "chat". Defaults to "chat".
    """
    save_file = open(global_room_pool[room_id]["save_location"], "a")
    log_message = {}
    # logging the initial events
    if log_type == "events":
        if event_status == "initial":
            log_message = {
                "time": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
                "type": "event",
                "event_type": "initial",
                "assignmentId": assignmentId,
                "speaker": workId,
                "room_id": room_id,
                "gap": "None",
                "events": global_event_dict[room_id]["timelines"][workId][0][
                    "schedule"
                ][0],
            }
        else:
            event_info = {}
            if (
                "life_events"
                not in global_event_dict[room_id]["timelines"][workId][-1]["schedule"][
                    -1
                ]
            ):
                event_info = global_event_dict[room_id]["timelines"][workId][-2][
                    "schedule"
                ][-1]
                event_info["progress"].extend(
                    global_event_dict[room_id]["timelines"][workId][-1]["schedule"][-1][
                        "progress"
                    ]
                )
            log_message = {
                "time": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
                "type": "event",
                "event_type": "subsequent",
                "speaker": workId,
                "room_id": room_id,
                "gap": global_event_dict[room_id]["gap"][-1],
                "events": event_info,
            }
    elif log_type == "chat":
        log_message = {
            "time": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            "type": "chat",
            "room_id": room_id,
            "speaker": workId,
            "text": chat_text,
        }
    elif log_type == "report":
        log_message = {
            "time": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            "type": "report",
            "room_id": room_id,
            "speaker": workId,
            "text": chat_text,
        }
    save_file.write(json.dumps(log_message) + "\n")


class MainHandler(tornado.web.RequestHandler):
    """Render the index page

    Args:
        tornado (_type_): a RequestHandler class
    """

    def __init__(self, application, request) -> None:
        super().__init__(application, request)
        self.worker_id = ""

    def get(self):
        # matching = False
        # workerId = ""
        try:
            self.worker_id = self.get_argument("workerId")
            assignmentId = self.get_argument("assignmentId")
            hitId = self.get_argument("hitId")
        except tornado.web.MissingArgumentError:
            # workerId = uuid.uuid1().hex
            self.render("invalid_argument.html")
            return
        # Once connected, assign worker_status and add worker to
        # worker pool.
        worker_status = {
            "is_matching": False,
            "matched": False,
            "worker_id": self.worker_id,
            "room_id": "",
        }
        global_user_pool[self.worker_id] = worker_status
        self.render("index.html", message=worker_status)

    def on_connection_close(self) -> None:
        print(f"{self.worker_id} left")


class FinishHandler(tornado.web.RequestHandler):
    def post(self):
        self.render("finish.html")


class MatchHandler(tornado.websocket.WebSocketHandler):
    """Handle the matching

    Args:
        tornado (_type_): _description_
    """

    def __init__(self, application: tornado.web.Application, request) -> None:
        super().__init__(application, request)
        self.worker_id = ""

    async def on_message(self, message):
        global matching_queue
        message_data = json.loads(message)

        # someone joined
        if message_data["type"] == "joined":
            self.worker_id = message_data["worker_id"]
            print(f"[Log] {self.worker_id} Joined")

        # someone started matching
        elif message_data["type"] == "matching":
            # workerId = message_data["worker_id"]
            matching_clients[self.worker_id] = self
            print(f"[Log] Worker: {self.worker_id} started matching.")
            if not global_user_pool[self.worker_id]["matched"]:
                global_user_pool[self.worker_id]["is_matching"] = True
                if self.worker_id not in matching_queue:
                    matching_queue.append(self.worker_id)
            print(f"[Log] matching queue: {matching_queue}")
            # Matched. if there are more than two users, open a new room.
            room_info = await ioloop.IOLoop.current().run_in_executor(
                executor, match, self.worker_id
            )
            # room_info = ioloop.IOLoop.current().add_callback(match, self.worker_id)
            if room_info != None:
                response = {"type": "matching", "room_info": room_info}
                print(f"[Log] matched, room_info: {room_info}")
                matching_clients[room_info["speaker_1"]].write_message(
                    json.dumps(response)
                )
                matching_clients[room_info["speaker_2"]].write_message(
                    json.dumps(response)
                )
                del matching_clients[room_info["speaker_1"]]
                del matching_clients[room_info["speaker_2"]]
                # self.write_message(json.dumps(response))

        # ping pong
        elif message_data["type"] == "ping":
            response = {"type": "ping", "text": "pong"}
            self.write_message(json.dumps(response))

    def on_close(self) -> None:
        print("left")
        if (
            global_user_pool[self.worker_id]["is_matching"] == True
            and global_user_pool[self.worker_id]["matched"] == False
        ):
            # remove user from matching queue
            matching_queue.remove(self.worker_id)
            global_user_pool[self.worker_id]["is_matching"] == False
            print(f"[Log] {self.worker_id} left matching")
            print(f"[Log] matching queue: {matching_queue}")


matching_clients: Dict[Text, MatchHandler] = {}


class RoomHandler(tornado.web.RequestHandler):
    """Assign a room for a matched pair

    Args:
        tornado (_type_): A RequestHandler class
    """

    def get(self, room_id):
        workerId = self.get_argument("workerId")
        assignmentId = self.get_argument("assignmentId")
        room_id = int(room_id)
        print(f"[Log] Room {room_id} is initialed")
        # For each new room, if the current connection
        # is the first user, generate the initial gap and events.
        if room_id not in global_event_dict:
            initial_event = get_initial_progress(progress_dict)
            room_event_info = {
                "gap": [""],
                "timelines": {
                    workerId: [
                        {
                            "event_id": initial_event["id"],
                            "start_time": 0,
                            "schedule": [{"progress": initial_event["initial"]}],
                        }
                    ]
                },
            }
            global_event_dict[room_id] = room_event_info

        # If the current client is matched with some other clinets in a room
        # but hasn't get events yet.
        elif workerId not in global_event_dict[room_id]["timelines"]:
            # generate some initial events with the same duration key.
            initial_event = get_initial_progress(progress_dict)
            global_event_dict[room_id]["timelines"][workerId] = [
                {
                    "event_id": initial_event["id"],
                    "start_time": 0,
                    "schedule": [{"progress": initial_event["initial"]}],
                }
            ]
        # Return the events of this client to the itself.
        room_client_info = {
            "room_id": room_id,
            "speaker_1": global_room_pool[room_id]["speaker_1"],
            "speaker_2": global_room_pool[room_id]["speaker_2"],
            "worker_id": workerId,
            "gap_info": global_event_dict[room_id]["gap"][-1],
            "events_info": global_event_dict[room_id]["timelines"][workerId][-1][
                "schedule"
            ][-1],
        }
        log_request(room_id, workerId, assignmentId, event_status="initial", log_type="events")

        # create message history dictionary for this room
        if room_id not in global_message_dict:
            global_message_dict[room_id] = []
        self.render("room.html", room_client_info=room_client_info)


class EventUpdateHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request) -> None:
        super().__init__(application, request)
        self.worker_id = ""
        self.room_id = 0

    def open(self):
        print("[Log] WebSocket opened")

    def on_message(self, message):
        message_data = json.loads(message)
        # if message_data["type"] != "ping":
        #     print(f"websocket message: {message}")

        # Process the initial message and register the current connection as a client.
        if message_data["type"] == "initialize":
            self.worker_id = message_data["worker_id"]
            self.room_id = message_data["room_id"]
            self.room_id = int(self.room_id)

            if self.room_id not in clients:
                clients[self.room_id] = [self]
            else:
                clients[self.room_id].append(self)
                for c in clients[self.room_id]:
                    # print(f"sending to {c.worker_id}")
                    response = {
                        "type": "reconnection",
                    }
                    c.write_message(json.dumps(response))
            # print(clients)

        # Process the new session message
        if message_data["type"] == "session":
            # generate a new gap and duration key
            gap, duration_key = move_forward()
            # print(f"generate gap {gap}")
            global_event_dict[self.room_id]["gap"].append(gap)
            gap_time = time_to_minutes(gap)

            # get life events and world events
            for worker, timeline in global_event_dict[self.room_id][
                "timelines"
            ].items():
                progress, next, finish_status = get_next_progress(
                    progress_dict[timeline[-1]["event_id"]],
                    gap_time,
                    timeline[-1]["start_time"],
                )
                timeline[-1]["schedule"].append(
                    {
                        "progress": progress,
                        "life_events": get_life_events(
                            life_event_dict, duration_key, 3
                        ),
                        "world_events": get_world_events(world_event_dict, 3),
                        "plans": next + get_random_future_plans(future_plan_dict, 2),
                    }
                )
                global_event_dict[self.room_id]["timelines"][worker][-1][
                    "start_time"
                ] += gap_time
                if finish_status:
                    initial_event = get_initial_progress(progress_dict)
                    global_event_dict[self.room_id]["timelines"][worker].append(
                        {
                            "event_id": initial_event["id"],
                            "start_time": 0,
                            "schedule": [{"progress": [initial_event["initial"]]}],
                        }
                    )

            for c in clients[self.room_id]:
                # print(f"sending to {c.worker_id}")
                log_request(
                    self.room_id,
                    c.worker_id,
                    event_status="events",
                    log_type="events",
                )
                event_info = {}
                if (
                    "life_events"
                    not in global_event_dict[self.room_id]["timelines"][c.worker_id][
                        -1
                    ]["schedule"][-1]
                ):
                    event_info = global_event_dict[self.room_id]["timelines"][
                        c.worker_id
                    ][-2]["schedule"][-1]
                    event_info["progress"].extend(
                        global_event_dict[self.room_id]["timelines"][c.worker_id][-1][
                            "schedule"
                        ][-1]["progress"]
                    )
                else:
                    event_info = global_event_dict[self.room_id]["timelines"][
                        c.worker_id
                    ][-1]["schedule"][-1]
                response = {
                    "type": "session",
                    "session": 0,
                    "gap": gap,
                    "events": event_info,
                }
                print(f"[Log] New session in room {self.room_id}. {response}")
                c.write_message(json.dumps(response))

        # Process the new message
        if message_data["type"] == "message":
            global_message_dict[self.room_id].append(
                {"speaker": self.worker_id, "text": message_data["message"]}
            )
            log_request(
                self.room_id,
                self.worker_id,
                chat_text=message_data["message"],
                log_type="chat",
            )
            for c in clients[self.room_id]:
                response = {
                    "type": "message",
                    "speaker": message_data["worker_id"],
                    "text": message_data["message"],
                }
                c.write_message(json.dumps(response))

        if message_data["type"] == "report":
            log_request(
                self.room_id,
                self.worker_id,
                chat_text=message_data["report"],
                log_type="report",
            )
            response = {
                "type": "report",
                "text": "Thanks for your report. We will process your report ASAP!",
            }
            self.write_message(json.dumps(response))

        # Ping pong to keep alive
        if message_data["type"] == "ping":
            response = {"type": "ping", "text": "pong"}
            self.write_message(json.dumps(response))

    def on_close(self):
        room = self.room_id
        worker = self.worker_id
        clients[self.room_id].remove(self)
        global_user_pool.pop(worker, None)
        if clients[room]:
            for c in clients[room]:
                # print("writing to...")
                response = {
                    "type": "partner_disconnect",
                    "text": "You partner has disconnected from the server.",
                }
                c.write_message(json.dumps(response))
        # print(clients)


clients: Dict[int, List[EventUpdateHandler]] = {}


async def main():
    parse_command_line()
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/match", MatchHandler),
            (r"/room/id/([0-9]+$)", RoomHandler),
            (r"/event", EventUpdateHandler),
            (r"/finish", FinishHandler),
        ],
        cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=False,
        debug=options.debug,
    )
    app.listen(options.port)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
    # print(time_to_minutes("3 weeks"))
    # print(schedule_time_to_minutes("W:1"))
    # initial_event = get_initial_progress(progress_dict)
    # print(initial_event, initial_event["initial"])
    # start_time = 0
    # while True:
    #     input_text = input("move forward?\n")
    #     if input_text == "N":
    #         gap, duration_key = move_forward()
    #         print(f"*** Gap:{gap}")
    #         gap_time = time_to_minutes(gap)
    #         progress, finished = get_next_progress(initial_event, gap_time, start_time)
    #         print(f"*** progress:{progress}")
    #         start_time += gap_time

    #         if finished:
    #             print("Creating new event..")
    #             initial_event = get_initial_progress(progress_dict)
    #             print(initial_event, initial_event["initial"])
    #             start_time = 0
