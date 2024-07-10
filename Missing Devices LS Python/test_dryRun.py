import pdb, json, os
from ts_party_autokandji import main as ts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_score(abv, passnumber, stack, index):
    score = 0
    for i in range(len(stack[index])):
        if abv in stack[index][i]['Score']:
            score +=1 
    if score == passnumber:
        print(f"{index} PASSED")
    else:
        print(f"FAILED ** {index} ** FAILED")
        print(score)

    pass

def check_missing_score(abv, passnumber, stack, index):
    score = 0
    for i in range(len(stack[index])):
        if not abv in stack[index][i]['Score']:
            score +=1 
    if score == passnumber:
        print(f"{index} PASSED")
    else:
        print(f"FAILED ** {index} ** FAILED")
        print(score)

    pass


def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append(sublist)


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    # print(ldjson)


    # export 

    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)
        json_file.write('\n')
        json_file.close()


rt = True


autokandji = ts(rt)
output_json = BASE_DIR + '/Extract_Scripts/test_data/tk.json'
write_to_json(autokandji, output_json)


from ts_party_autotune import main as ts
intune_automox = ts(rt)
# pdb.set_trace()
output_json = BASE_DIR + '/Extract_Scripts/test_data/tk.json'
# write_to_json(intune_automox, output_json)



from ts_party_crowdkandji import main as ts
crowdkandji = ts(rt)



from ts_party_crowdtune import main as ts
crowdtune = ts(rt)



from ts_party_netkandji import main as ts
netkandji = ts(rt)



from ts_party_nettune import main as ts
nettune = ts(rt)


from detect_missing import main as ts
hermits = ts(rt)




check_score("A", 120, autokandji, 'AutoKandji')
check_score("A", 120, intune_automox, 'AutoTune')
check_score("C", 120, crowdkandji, 'CrowdKandji')
check_score("C", 120, crowdtune, 'CrowdTune')
check_score("N", 120, netkandji, 'NetKandji')
check_score("N", 120, nettune, 'NetTune')
print('-------------------------')
check_missing_score("C", 20, hermits, 'Crowdstrike')
check_missing_score("A", 20, hermits, 'Automox')
check_missing_score("N", 20, hermits, 'Netskope')



