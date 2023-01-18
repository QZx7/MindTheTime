import json
from typing import Text, List


def load_data(data_path: Text) -> List:
    data_list = []
    data_file = open(data_path, "r", encoding="utf-8")
    for line in data_file.readlines():
        data_list.append(json.loads(line.strip()))

    return data_list


def view_data(data_list: List):
    for item in data_list:
        print("*************************************************************")

        print("*************************************************************")
        for previous_dialog in item["previous_dialogs"]:
            print("===============================")
            print(previous_dialog["time_back"])
            for utt_index in range(len(previous_dialog["dialog"])):
                if utt_index % 2 == 0:
                    print(previous_dialog["dialog"][utt_index]["text"])
                else:
                    print("          " + previous_dialog["dialog"][utt_index]["text"])
        # display current dialog
        print("===============================")
        for utt_index in range(len(item["dialog"])):
            if utt_index % 2 == 0:
                print(item["dialog"][utt_index]["text"])
            else:
                print("          " + item["dialog"][utt_index]["text"])


def load_data(data_path: Text):
    data_file = open(data_path, "r", encoding="utf-8")
    for line in data_file.readlines():
        line_data = json.loads(line.strip())
        if line_data["type"] == "event":
            print("************ events ************")
            if line_data["event_type"] == "initial":
                print("Gap: " + line_data["gap"])
            else:
                print("Gap: " + line_data["gap"]["gap"])
            print(line_data["speaker"] + ": " + str(line_data["events"]))
            print("************ chat ************")
        elif line_data["type"] == "chat":
            print(line_data["speaker"] + ": " + line_data["text"].strip())


def continuous_event_viewer(data_path: Text):
    data_file = open(data_path, "r", encoding="utf-8")
    reformat_data = open(r"./mtt/chat/data/new_continuous.json", "w", encoding="utf-8")
    continuous_data = json.load(data_file)
    for key, value in continuous_data.items():
        print(f"{key}: {len(value)}")

    new_list = []
    id = 0
    for key, value in continuous_data.items():
        for item in value:
            item["id"] = id
            item["duration_key"] = key
            new_schedule_list = []
            for schedule in item["schedules"]:
                new_schedule = []
                for schedule_key, schedule_value in schedule.items():
                    new_schedule_item = {
                        "schedule_time": schedule_key,
                        "schedule_content": schedule_value,
                    }
                    new_schedule.append(new_schedule_item)
            new_schedule_list.append(new_schedule.copy())
            item["schedules"] = new_schedule_list
            new_list.append(item)
            id += 1
    # print(new_list)
    json.dump(new_list, reformat_data, indent=4)
    print(len(new_list))


if __name__ == "__main__":
    # data_path = "./data/msc/valid.txt"
    # data_list = load_data(data_path)
    # view_data(data_list)
    # data_path = "./mtt/chat/log/chat.log"
    data_path = r"./mtt/chat/data/continuous_event.json"
    # load_data(data_path)
    continuous_event_viewer(data_path)
