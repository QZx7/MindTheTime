import json
from typing import Text, List

def load_data(data_path: Text) -> List:
    data_list = []
    data_file = open(data_path, 'r', encoding='utf-8')
    for line in data_file.readlines():
        data_list.append(json.loads(line.strip()))
    
    return data_list

def view_data(data_list: List):
    for item in data_list:
        input_text = input("command\n")
        if input_text == 'x':
            print(item)
            # display previous dialog
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
        else:
            break


if __name__ == "__main__":
    data_path = "./data/msc/valid.txt"
    data_list = load_data(data_path)
    view_data(data_list)
