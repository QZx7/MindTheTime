import asyncio
import tornado.locks
import tornado.web
import tornado.websocket
import tornado.httpserver
import os.path
import json
import random
import datetime

from tornado.options import define, options, parse_command_line
from tornado import ioloop
from concurrent.futures import ThreadPoolExecutor
from typing import Text, Dict, List, Any, Optional, Union

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


def get_random_gap(event_dict: Dict[Text, List[Text]]):
    """Get a random gap.

    Args:
        event_dict (Dict[Text, List[Text]]): The pre-defined event list.

    Returns:
        Return a random gap and the duration key.
    """
    duration = random.randint(0, len(event_dict.keys()) - 1)
    duration_key = ""
    gap = ""
    # hours
    if duration == 0:
        duration_key = "hour"
        gap = f"{random.randint(2, 20)} hours"
    # days
    elif duration == 1:
        duration_key = "day"
        gap = f"{random.randint(2, 5)} days"
    # weekend
    elif duration == 2:
        duration_key = "weekend"
        gap = "A weekend"
    # weeks
    elif duration == 3:
        duration_key = "week"
        gap = f"{random.randint(2, 3)} weeks"
    # months
    elif duration == 4:
        duration_key = "month"
        gap = f"{random.randint(2, 5)} months"
    elif duration == 5:
        duration_key = "year"
        gap = "A year"
    # events = random.choices(event_dict[duration_key], k=3)
    return gap, duration_key


def move_forward() -> Union[Text, Text]:
    possible_units = ["minutes", "hours", "days", "weeks", "months", "year"]
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


def get_initial_progress(event_dict: List[Dict[Text, Any]]) -> Union[Dict, Text]:
    """Get the initial events.

    Args:
        event_dict (Dict[Text, List[Text]]): The pre-defined initial events list.

    Returns:
        List[Text]: A list of initial events.
    """
    initial_event = random.choice(event_dict)
    event_text = initial_event["initial"]
    return initial_event, event_text


def time_to_minutes(time: Text) -> int:
    """Convert the time to minutes.

    Args:
        time (Text): Input time.

    Returns:
        int: Time in minutes.
    """
    time_parts = time.split(" ")[0]
    time_number = int(time_parts[0])
    time_unit = time_parts[1]

    multiplyer = 1
    if "hour" in time_unit:
        multiplyer *= 60
    elif "day" in time_unit:
        multiplyer = multiplyer * 60 * 24
    elif "weeks" in time_unit:
        multiplyer = multiplyer * 60 * 24 * 7
    elif "months" in time_unit:
        multiplyer = multiplyer * 60 * 24 * 30
    elif "year" in time_unit:
        multiplyer = multiplyer * 60 * 24 * 365

    return time_number * multiplyer


def schedule_time_to_minutes(time: Text) -> int:
    time = 0
    if "|" in time:
        key_parts = time.split("|")
        for key in key_parts:
            time += single_time_to_minutes(key)
    else:
        time = single_time_to_minutes(time)

    def single_time_to_minutes(time: Text) -> int:
        time_parts = time.split(":")
        time_number = int(time_parts)[1]
        time_unit = time_parts[0]

        multiplyer = 1
        if "M" in time_unit:
            multiplyer = multiplyer * 60 * 24 * 30
        elif "W" in time_unit:
            multiplyer = multiplyer * 60 * 24 * 7
        elif "D" in time_unit:
            multiplyer = multiplyer * 60 * 24
        elif "H" in time_unit:
            multiplyer *= 60

        return time_number * time_unit

    return time


def get_progress(
    event: Dict[Text, Union[int, Text, List[Dict[Text, List[Text]]]]], gap: Text
) -> List[Text]:
    gap = time_to_minutes(gap)

    for key, value in event["schedules"][0].items():
        if schedule_time_to_minutes(key) >= gap:
            print(value)
            break


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


# Global arguments to manage the server and rooms
executor = ThreadPoolExecutor(4)
global_user_pool = {}
matching_queue = []
global_room_id = 0
global_room_pool = {}
# global_message_buffer_dict: Dict[int, MessageBuffer] = {}
global_message_dict: Dict[int, List[Dict[Text, Text]]] = {}

# Event
event_dict = read_event("random_event.json")
initial_dict = read_event("initial.json")
news_dict = read_event("news.json")
global_event_dict: Dict[int, Dict[Text, List[Dict[Text, Any]]]] = {}


def match(workerId: Text):
    """The matching function for a worker

    Args:
        workerId (Text): submit workerId for matching

    Returns:
        _type_: Room information if matched
    """
    print("start matching...")
    global matching_queue
    global global_room_id
    while True:
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
            save_location = os.path.join(
                LOG_PATH, CURRENT_TIME + f"-{global_room_id}.log"
            )
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


def log_request(
    room_id: int,
    workId: Text,
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
        if event_status == "initial" or event_status == "news":
            log_message = {
                "type": "event",
                "event_type": "initial",
                "speaker": workId,
                "room_id": room_id,
                "gap": "None",
                "events": global_event_dict[room_id]["events"][0][workId],
            }
        else:
            log_message = {
                "type": "event",
                "event_type": "subsequent",
                "speaker": workId,
                "room_id": room_id,
                "gap": global_event_dict[room_id]["gap"][-1],
                "events": global_event_dict[room_id]["events"][-1][workId],
            }
    elif log_type == "chat":
        log_message = {
            "type": "chat",
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

    def get(self):
        # matching = False
        workerId = ""
        try:
            workerId = self.get_argument("workerId")
        except tornado.web.MissingArgumentError:
            self.render("invalid_argument.html")
        # Once connected, assign worker_status and add worker to
        # worker pool.
        worker_status = {
            "is_matching": False,
            "matched": False,
            "worker_id": workerId,
            "room_id": "",
        }
        global_user_pool[workerId] = worker_status
        self.render("index.html", message=worker_status)


class MatchHandler(tornado.websocket.WebSocketHandler):
    """Handle the matching

    Args:
        tornado (_type_): _description_
    """

    async def on_message(self, message):
        global matching_queue
        message_data = json.loads(message)

        # someone joined
        if message_data["type"] == "joined":
            print("Joined")

        # someone started matching
        elif message_data["type"] == "matching":
            workerId = message_data["worker_id"]
            print(f"Worker: {workerId} started matching.")
            print(f"matching queue: {matching_queue}")
            if not global_user_pool[workerId]["matched"]:
                global_user_pool[workerId]["is_matching"] = True
                if workerId not in matching_queue:
                    matching_queue.append(workerId)
            # Matched. if there are more than two users, open a new room.
            room_info = await ioloop.IOLoop.current().run_in_executor(
                executor, match, workerId
            )
            response = {"type": "matching", "room_info": room_info}
            # self.write_message()
            print(f"matched, room_info: {room_info}")
            self.write_message(json.dumps(response))

        # ping pong
        elif message_data["type"] == "ping":
            response = {"type": "ping", "text": "pong"}
            self.write_message(json.dumps(response))


class RoomHandler(tornado.web.RequestHandler):
    """Assign a room for a matched pair

    Args:
        tornado (_type_): A RequestHandler class
    """

    def get(self, room_id):
        workerId = self.get_argument("workerId")
        room_id = int(room_id)

        # For each new room, if the current connection
        # is the first user, generate the initial gap and events.
        if room_id not in global_event_dict:
            gap, duration_key = get_random_gap(event_dict)
            room_event_info = {
                "gap": [{"gap": gap, "duration_key": duration_key}],
                "events": [{workerId: get_initial_progress(initial_dict)}],
            }
            global_event_dict[room_id] = room_event_info

        # If the current client is matched with some other clinets in a room
        # but hasn't get events yet.
        elif workerId not in global_event_dict[room_id]["events"][0]:
            # generate some initial events with the same duration key.
            duration_key = global_event_dict[room_id]["gap"][0]["duration_key"]
            global_event_dict[room_id]["events"][0][workerId] = get_initial_progress(
                initial_dict
            )

        # Return the events of this client to the itself.
        room_client_info = {
            "room_id": room_id,
            "speaker_1": global_room_pool[room_id]["speaker_1"],
            "speaker_2": global_room_pool[room_id]["speaker_2"],
            "worker_id": workerId,
            "gap_info": global_event_dict[room_id]["gap"][-1]["gap"],
            "events_info": global_event_dict[room_id]["events"][-1][workerId],
        }
        log_request(room_id, workerId, event_status="initial", log_type="events")

        # create message history dictionary for this room
        if room_id not in global_message_dict:
            global_message_dict[room_id] = []
        self.render("room.html", room_client_info=room_client_info)


clients: Dict[int, List[tornado.websocket.WebSocketHandler]] = {}


class EventUpdateHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request) -> None:
        super().__init__(application, request)
        self.worker_id = ""
        self.room_id = 0

    def open(self):
        print("WebSocket opened")

    def on_message(self, message):

        message_data = json.loads(message)
        if message_data["type"] != "ping":
            print(f"websocket message: {message}")

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
                    print(f"sending to {c.worker_id}")
                    response = {
                        "type": "reconnection",
                    }
                    c.write_message(json.dumps(response))
            print(clients)

        # Process the new session message
        if message_data["type"] == "session":
            # generate a new gap and duration key
            gap, duration_key = get_random_gap(event_dict)
            global_event_dict[self.room_id]["gap"].append(
                {"gap": gap, "duration_key": duration_key}
            )
            speaker_1_events = get_life_events(event_dict, duration_key, 3)
            speaker_2_events = get_life_events(event_dict, duration_key, 3)
            speaker_1_events.extend(get_world_events(news_dict, 3))
            speaker_2_events.extend(get_world_events(news_dict, 3))
            global_event_dict[self.room_id]["events"].append(
                {
                    global_room_pool[self.room_id]["speaker_1"]: speaker_1_events,
                    global_room_pool[self.room_id]["speaker_2"]: speaker_2_events,
                }
            )
            for c in clients[self.room_id]:
                print(f"sending to {c.worker_id}")
                log_request(
                    self.room_id,
                    c.worker_id,
                    event_status=str(len(global_event_dict[self.room_id]["events"])),
                    log_type="events",
                )
                response = {
                    "type": "session",
                    "session": 0,
                    "gap": gap,
                    "events": global_event_dict[self.room_id]["events"][-1][
                        c.worker_id
                    ],
                }
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
                print("writing to...")
                response = {
                    "type": "partner_disconnect",
                    "text": "You partner has disconnected from the server.",
                }
                c.write_message(json.dumps(response))
        print(clients)


async def main():
    parse_command_line()
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/match", MatchHandler),
            (r"/room/id/([0-9]+$)", RoomHandler),
            (r"/event", EventUpdateHandler),
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
