import json

def progress_sample_to_latex_table(sample_id, progress_file):
    progress_data = json.load(progress_file)
    output_text = ""
    for item in progress_data[str(sample_id)]["schedules"][0]:
        output_text += "\\textbf{" + item["schedule_time"] + "} \\\\\n"
        for content in item["schedule_content"]:
            output_text += content + "\\\\\n"

    print(output_text)

progress_file = open(r"./mtt/chat/data/progress.json", 'r', encoding='utf-8')
progress_sample_to_latex_table(0, progress_file)
    