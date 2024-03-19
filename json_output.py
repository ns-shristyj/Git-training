
import json


def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append(sublist)


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    # print(ldjson)


    # export 

    with open(export_path, 'a', encoding='utf-8') as json_file:
        json_file.write(ldjson)
        json_file.write('\n')
        json_file.close()

