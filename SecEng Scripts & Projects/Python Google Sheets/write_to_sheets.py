import csv
import random
import string

def generate_token_strings(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


# Created headers 

headers = ['l1', 'l2', 'l3', 'l4', 'l5', 'l6']


data = [
    [generate_token_strings(random.randint(5,10)) for _ in range(random.randint(10,80))],
    [generate_token_strings(random.randint(5,10)) for _ in range(random.randint(10,80))],
    [generate_token_strings(random.randint(5,10)) for _ in range(random.randint(10,80))],
    [generate_token_strings(random.randint(5,10)) for _ in range(random.randint(10,80))],
    [generate_token_strings(random.randint(5,10)) for _ in range(random.randint(10,80))],
    [generate_token_strings(random.randint(5,10)) for _ in range(random.randint(10,80))],
]


data = list(map(list, zip(*data)))


# writing csv file 

with open('data/tokenized_dataframe.csv', 'w', newline='') as csvfile:
    csv_write = csv.writer(csvfile)

    csv_write.writerow(headers)
    csv_write.writerows(data)