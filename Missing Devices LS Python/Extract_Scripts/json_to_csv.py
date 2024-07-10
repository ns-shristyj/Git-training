import pandas as pd 
import os 
import pdb
from collections import defaultdict


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def make_csv(sf, stack):

    csv_dict = defaultdict(list)
    df = sf['Inventory']

    for k,v in sf.items():
        for sublist in v:
            for key,value in sublist.items():
                csv_dict[key].append(value)

    out_df = pd.DataFrame.from_dict(dict(csv_dict.items()))
    # out_df = pd.DataFrame.from_records
    print(out_df)




                
    output_folder = BASE_DIR + f'/out_data/out_csv/{stack}.csv'

    out_df.to_csv(output_folder)




# if __name__ == '__main__':
#     make_csv()