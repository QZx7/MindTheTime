import asyncio
import tornado.locks
import tornado.web
import tornado.websocket
import tornado.httpserver
import os.path
import uuid
import json
import random

from tornado.options import define, options, parse_command_line
from tornado import ioloop
from concurrent.futures import ThreadPoolExecutor
from typing import Text, Dict, List, Any

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
LOG_PATH = os.path.join(os.path.dirname(__file__), "log")

class MessageBuffer(object):
    def __init__(self, id):
        # cond is notified whenever the message cache is updated
        self.id = id
        self.cond = tornado.locks.Condition()
        self.cache = []
        self.cache_size = 200

    def get_messages_since(self, cursor):
        """Returns a list of messages newer than the given cursor.
        ``cursor`` should be the ``id`` of the last message received.
        """
        results = []
        for msg in reversed(self.cache):
            if msg["id"] == cursor:
                break
            results.append(msg)
        results.reverse()
        return results

    def add_message(self, message):
        self.cache.append(message)
        if len(self.cache) > self.cache_size:
            self.cache = self.cache[-self.cache_size :]
        self.cond.notify_all()

def read_event(filename: Text):
    print("loading events ....")
    file_path = os.path.join(DATA_PATH, filename)
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.loads(file.read())

def get_random_gap(event_dict: Dict[Text, List[Text]]) -> Dict[Text, Any]:
    duration = random.randint(0, 5)
    duration_key = ""
    gap = ""
    # hours
    if duration == 0:
        duration_key = "hour"
        gap = f"{random.randint(1, 20)} hours"
    # days
    elif duration == 1:
        duration_key = "day"
        gap = f"{random.randint(1, 5)} days"
    # weekend
    elif duration == 2:
        duration_key = "weekend"
        gap = "weekend"
    # weeks
    elif duration == 3:
        duration_key = "week"
        gap = f"{random.randint(1, 3)} weeks"
    # months
    elif duration == 4:
        duration_key = "month"
        gap = f"{random.randint(1, 5)} months"
    elif duration == 5:
        duration_key = "year"
        gap = "year"
    # events = random.choices(event_dict[duration_key], k=3)
    return gap, duration_key

def get_random_events(event_dict: Dict[Text, List[Text]], duration_key: Text, events_number: int) -> List[Text]:
    if duration_key in event_dict:
        events = random.choices(event_dict[duration_key], k=events_number)
        return events

# Global arguments to manage the server and rooms
executor = ThreadPoolExecutor(4)
global_user_pool = {}
matching_queue = []
global_room_id = 0
global_room_pool = {}
global_message_buffer_dict: Dict[int, MessageBuffer] = {}

# Event
event_dict = read_event("event.json")
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
        if global_user_pool[workerId]["is_matching"] == False and global_user_pool[workerId]["matched"]:
            room_id = global_user_pool[workerId]["room_id"]
            room_info = {"room_id": room_id,
                "speaker_1": global_room_pool[room_id]['speaker_1'],
                "speaker_2": global_room_pool[room_id]['speaker_2']
            }
            return room_info
        
        # if this user is not matched with anyone else, match this user with the
        # first person in the queue.
        if len(matching_queue) >= 2:

            # global settings
            speaker_1 = workerId
            matching_queue.remove(workerId)
            speaker_2 = matching_queue.pop(0)
            global_room_pool[global_room_id] = {
                "speaker_1": speaker_1,
                "speaker_2": speaker_2
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
                "speaker_2": speaker_2
            }
            global_room_id += 1
            return room_info


class MainHandler(tornado.web.RequestHandler):
    """Render the index page

    Args:
        tornado (_type_): a RequestHandler class
    """
    def get(self):
        # matching = False
        workerId = self.get_argument("workerId")
        worker_status = {
            "is_matching": False,
            "matched": False,
            "worker_id": workerId, 
            "room_id": "",
        }
        global_user_pool[workerId] = worker_status
        self.render("index.html", message=worker_status)

class MatchHandler(tornado.web.RequestHandler):
    """Handle the matching.

    Args:
        tornado (_type_): A RequestHandler class
    """
    async def post(self):
        global matching_queue
        workerId = self.get_argument("workerId")
        print(f"Worker: {workerId} started matching.")
        if not global_user_pool[workerId]["matched"]:
            global_user_pool[workerId]["is_matching"] = True
            if workerId not in matching_queue:
                matching_queue.append(workerId)
        # Matched. if there are more than two users, open a new room.
        room_info = await ioloop.IOLoop.current().run_in_executor(executor, match, workerId)
        print(f"matched, room_info: {room_info}")
        self.write(room_info)

class RoomHandler(tornado.web.RequestHandler):
    """Assign a room for a matched pair

    Args:
        tornado (_type_): A RequestHandler class
    """
    def get(self, room_id):
        workerId = self.get_argument("workerId")
        room_id = int(room_id)
        if room_id not in global_event_dict:
            gap, duration_key = get_random_gap(event_dict)
            room_event_info = {
                "gap": [
                    {
                        "gap": gap,
                        "duration_key": duration_key
                    }
                ],
                "events": [
                    {
                        workerId: get_random_events(event_dict, duration_key, 3)
                    }
                ]
            }
            # events_info = get_random_events(event_dict)
            global_event_dict[room_id] = room_event_info
        elif workerId not in global_event_dict[room_id]["events"][0]:
            duration_key = global_event_dict[room_id]["gap"][0]["duration_key"]
            global_event_dict[room_id]["events"][0][workerId] = get_random_events(event_dict, duration_key, 3)
        # global_user_pool.append(self.request.uri.split("workerId=")[1])
        room_client_info = {
            "room_id": room_id,
            "speaker_1": global_room_pool[room_id]["speaker_1"],
            "speaker_2": global_room_pool[room_id]["speaker_2"],
            "worker_id": workerId,
            "gap_info": global_event_dict[room_id]["gap"][-1]["gap"],
            "events_info": global_event_dict[room_id]["events"][-1][workerId]
        }

        # create history dictionary for this room
        # global_message_dict[room_id] = []
        if room_id not in global_message_buffer_dict:
            global_message_buffer_dict[room_id] = MessageBuffer(room_id)
        # messages = {
        #     "messages": global_message_dict[room_id]
        # }
        self.render("room.html", room_client_info=room_client_info)
        # self.render("room.html", messages=global_message_buffer.cache)

clients : Dict[int, List[tornado.websocket.WebSocketHandler]] = {}

class EventUpdateHandler(tornado.websocket.WebSocketHandler):

    def __init__(self, application, request) -> None:
        super().__init__(application, request)
        self.worker_id = ""
        self.room_id = 0

    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        print(f"websocket message: {message}")
        message_data = json.loads(message)

        if message_data['type'] == "initialize":
            self.worker_id = message_data['worker_id']
            self.room_id = int(self.room_id)

            if self.room_id not in clients:
                clients[self.room_id] = [self]
            else:
                clients[self.room_id].append(self)
            print(clients)

        if message_data['type'] == "session":
            gap, duration_key = get_random_gap(event_dict)
            global_event_dict[self.room_id]["gap"].append({
                "gap": gap,
                "duration_key": duration_key
            })
            speaker_1_events = get_random_events(event_dict, duration_key, 3)
            speaker_2_events = get_random_events(event_dict, duration_key, 3)
            global_event_dict[self.room_id]["events"].append({
                global_room_pool[self.room_id]["speaker_1"]: speaker_1_events,
                global_room_pool[self.room_id]["speaker_2"] : speaker_2_events
            })

            for c in clients[self.room_id]:
                print(f"sending to {c.worker_id}")
                response = {
                    "type": "session",
                    "session": 0,
                    "gap": gap,
                    "events": global_event_dict[self.room_id]["events"][-1][c.worker_id]
                }
                c.write_message(json.dumps(response))

        if message_data['type'] == "message":
            for c in clients[self.room_id]:
                response = {
                    "type": "message",
                    "speaker": message_data['worker_id'],
                    "text": message_data['message'],
                }
                c.write_message(json.dumps(response))
        
        if message_data['type'] == "report":
            response = {
                "type": "report",
                "text": "Thanks for your report. We will process your report ASAP!",
            }
            self.write_message(json.dumps(response))

    def on_close(self):
        room = self.room_id
        clients[self.room_id].remove(self)
        if clients[room]:
            for c in clients[room]:
                print("writing to...")
                response = {
                    "type": "partner_disconnect",
                    "text": "You partner has disconnected from the server."
                }
                c.write_message(json.dumps(response))
        print(clients)

# class MessageNewHandler(tornado.web.RequestHandler):
#     """Post a new message to the chat room."""

#     def post(self, room_id):
#         room_id = self.request.uri.split('/')[-1].split('?')[0]
#         room_id = int(room_id)
#         worker_id = self.get_argument("workerId")
#         print(global_message_buffer_dict[room_id])
#         message = {"id": str(uuid.uuid4()), "body": self.get_argument("body"), "speaker": worker_id}
#         # render_string() returns a byte string, which is not supported
#         # in json, so we must convert it to a character string.
#         message["html"] = tornado.escape.to_unicode(
#             self.render_string("message.html", message=message)
#         )
#         if self.get_argument("next", None):
#             print(self.get_argument("next"))
#             self.redirect(self.get_argument("next"))
#         else:
#             self.write(message)
#         global_message_buffer_dict[room_id].add_message(message)
#         # global_message_buffer.add_message(message)


# class MessageUpdatesHandler(tornado.web.RequestHandler):
#     """Long-polling request for new messages.
#     Waits until new messages are available before returning anything.
#     """

#     async def post(self, room_id):
#         cursor = self.get_argument("cursor", None)
#         room_id = self.get_argument("roomId", None)
#         room_id = int(room_id)
#         messages = global_message_buffer_dict[room_id].get_messages_since(cursor)
#         # messages = global_message_buffer.get_messages_since(cursor)
#         while not messages:
#             # Save the Future returned here so we can cancel it in
#             # on_connection_close.
#             self.wait_future = global_message_buffer_dict[room_id].cond.wait()
#             try:
#                 await self.wait_future
#             except asyncio.CancelledError:
#                 return
#             messages = global_message_buffer_dict[room_id].get_messages_since(cursor)
#         if self.request.connection.stream.closed():
#             return
#         print(messages)
#         self.write(dict(messages=messages))

#     def on_connection_close(self):
#         self.wait_future.cancel()

# class EventUpdateHandler(tornado.web.RequestHandler):
#     def post(self):
#         room_id = self.get_argument("roomId", None)
#         worker_id = self.get_argument("workerId", None)
#         room_id = int(room_id)
#         gap, duration_key = get_random_gap(event_dict)
#         global_event_dict[room_id]["gap"].append(
#             {
#                 "gap": gap,
#                 "duration_key": duration_key
#             }
#         )
#         global_event_dict[room_id]["events"].append(
#             {
#                 global_room_pool[room_id]["speaker_1"]: get_random_events(event_dict, duration_key, 3),
#                 global_room_pool[room_id]["speaker_2"]: get_random_events(event_dict, duration_key, 3)
#             }
#         )
#         redirect_url = f"/room/id/{room_id}?workerId={worker_id}"
#         self.redirect(redirect_url)
        

# class NewMessageHandler(tornado.web.RequestHandler):
#     def post(self, worker_id):
#         worker_id = self.get_body_argument("workerId")
#         room_id = self.request.uri.split('/')[-1]
#         room_id = int(room_id)
#         message = self.get_body_argument("message")
#         global_message_dict[room_id].append(
#             {
#                 "speaker": worker_id,
#                 "text": message
#             }
#         )
#         self.write(
#             {
#                 "messages": global_message_dict[room_id]
#             }
#         )

# class UpdateMessageHandler(tornado.web.RequestHandler):
#     def post(self, worker_id):
#         # worker_id = self.get_body_argument("workerId")
#         counter = self.get_argument("currentCount")
#         room_id = self.request.uri.split('/')[-1]
#         counter = int(counter)
#         room_id = int(room_id)
#         # message = self.get_body_argument("message")
#         # global_message_dict[room_id].append(
#         #     {
#         #         "speaker": worker_id,
#         #         "text": message
#         #     }
#         # )
#         messages = get_messages_since(room_id, counter)
#         self.write(
#             {
#                 "messages": messages
#             }
#         )

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
