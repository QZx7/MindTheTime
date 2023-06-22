import json

def prepare_time_aware_data(conversation_path, events_path, time_tag_path, schedule_path):
    conversation_file = open(conversation_path, 'r', encoding='utf-8')
    events_file = open(events_path, 'r', encoding='utf-8')
    time_file = open(time_tag_path, 'r', encoding='utf-8')
    schedule_file = open(schedule_path, 'r', encoding='utf-8')


    parlai_format_file = open(r"./data/new_data/time_parlai_format.txt", 'w+', encoding='utf-8')
    time_schedule_format_file = open(r"./data/new_data/time_schedule_parlai_format.txt", 'w+', encoding='utf-8')
    schedule_format_file = open(r"./data/new_data/schedule_parlai_format.txt", 'w+', encoding='utf-8')
    event_format_file = open(r"./data/new_data/event_parlai_format.txt", 'w+', encoding='utf-8')

    # valid data
    conversation_data = json.load(conversation_file)
    events_data = json.load(events_file)
    time_tag_data = time_file.readlines()
    schedule_data = schedule_file.readlines()

    session_number = 0
    for item in conversation_data:
        session_number += len(item)
    
    assert(session_number == len(events_data))
    assert(session_number == len(time_tag_data))
    assert(session_number == len(schedule_data))

    for index in range(session_number):
        tag_data = json.loads(time_tag_data[index])
        for key, value in events_data[index].items():
            # print(f"{index} : {key} : {value}")
            print(tag_data[key])
            if value[0] in [" Not mentioned."]:
                value = []
            assert(len(tag_data[key]) == len(value))

    # convert_data
    for index in range(len(conversation_data)):
        conversation = conversation_data[index]
        conversation_length = len(conversation)
        events_text = ""
        schedule_text = ""
        pure_events_text = ""
        gap = []
        for event_index in range(conversation_length + 1):
            gap.append(conversation[event_index - 1]["gaps"])
            for key, value in events_data[index + event_index].items():
                # print(f"Loading events: {value} for speaker: {key}")
                for value_index in range(len(value)):
                    # print(f"Adding tags to {value_index} event for speaker: {key}")
                    if value[value_index] != " Not mentioned.":
                        tag_info = json.loads(time_tag_data[index + event_index])
                        print(f"Loading from time tag at {index}, for speaker: {key}, event: {value_index}")
                        progress_label = get_progress_label(gap, tag_info[key][value_index])
                        events_text += value[value_index] + " " + progress_label + "\\n"
                        pure_events_text += value[value_index] + "\\n"
                        # print(events_text)
            for key, value in json.loads(schedule_data[index + event_index]).items():
                if isinstance(value, str) or value == []:
                    pass
                else:
                    schedules = ';'.join(value)
                    schedule_text += f"\\n {key}: {schedules}"
            print(schedule_text)
            utterance_index = 0
            while utterance_index < len(conversation[event_index - 1]["sessions"]):
                utterance = conversation[event_index - 1]["sessions"][utterance_index]
                if utterance_index == len(conversation[event_index - 1]["sessions"]) - 1:
                    pass
                elif utterance_index == len(conversation[event_index - 1]["sessions"]) - 2:
                    parlai_format_file.write(
                        "text:" + utterance["text"] + "\\n Progress:" + events_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\t" + "episode_done:True\n"
                    )
                    time_schedule_format_file.write(
                        "text:" + utterance["text"] + "\\n Progress:" + events_text + "\\n Schedules:" + schedule_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\t" + "episode_done:True\n"
                    )
                    schedule_format_file.write(
                        "text:" + utterance["text"] + "\\n Schedules:" + schedule_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\t" + "episode_done:True\n"
                    )
                    event_format_file.write(
                        "text:" + utterance["text"] + "\\n Events:" + pure_events_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\t" + "episode_done:True\n"   
                    )
                else:
                    parlai_format_file.write(
                        "text:" + utterance["text"] + "\\n Progress:" + events_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\n"
                    )
                    time_schedule_format_file.write(
                        "text:" + utterance["text"] + "\\n Progress:" + events_text + "\\n Schedules:" + schedule_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\n"
                    )
                    schedule_format_file.write(
                        "text:" + utterance["text"] + "\\n Schedules:" + schedule_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\n"
                    )
                    event_format_file.write(
                        "text:" + utterance["text"] + "\\n Events:" + pure_events_text + "\t" + "labels:" + conversation[event_index - 1]["sessions"][utterance_index + 1]["text"] + "\n"
                    )
                utterance_index += 2

def time_to_minutes(time) -> int:
    """Convert the time to minutes.

    Args:
        time (Text): Input time.

    Returns:
        int: Time in minutes.
    """
    if time == "0 s":
        return 0
    time_parts = time.split(" ")
    if "-" in time_parts[0]:
        min = int(time_parts[0].split('-')[0])
        max = int(time_parts[0].split('-')[1])
        time_parts[0] = int((min + max) / 2)
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

def get_progress_label(gaps, duration):
    duration = duration[1:]
    if "indefinite" in duration:
        duration = "2 years"
    if "N/A" in duration:
        return "No significant progress."
    if "ongoing" in duration:
        duration = "1 day"

    if gaps == ["0 s"]:
        return "No significant progress."
    else:
        gap_time = 0
        for gap in gaps:
            gap_time += time_to_minutes(gap)
        duration_time = time_to_minutes(duration)
        if gap_time >= duration_time:
            return "Finished."
        elif gap_time >= 0.75 * duration_time:
            return "Three-forth Finished."
        elif gap_time >= 0.5 * duration_time:
            return "Half Finished."
        elif gap_time >= 0.25 * duration_time:
            return "One-forth Finished."
        else:
            return "No significant progress"


def main():
    conversation_path = r"./data/new_data/merged_conversation.json" # path to gap_chat data
    events_path = r"./data/new_data/extracted_events.json" # path to events
    time_tag_path = r"./data/new_data/time_tag.jsonl" # path to progress label
    schedule_path = r"./data/new_data/schedule.jsonl" # path to schedules
    prepare_time_aware_data(
        conversation_path, events_path, time_tag_path, schedule_path
    )
    # print(time_to_minutes("1-2 hours"))

if __name__ == "__main__":
    main()