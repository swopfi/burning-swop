import numpy as np
import requests as r
import hashlib as h

NODE = "https://nodes-testnet.wavesnodes.com"
BURNING_ADDR = "3Mp5JgVSHA9iziujC9Kmnf2rCN5SYFE97yC"
TOP_USERS_COUNT = 10
MAIN_PRIZE_ID = 5
PRIZES_IDS = [0, 1, 2, 3, 4]


def parse_data():
    params = {'matches': "boosting|prizes_amount|[A-z0-9]+_total_burned"}
    try:
        req = r.get(NODE + '/addresses/data/' + BURNING_ADDR, params)
        if req.status_code != 200:
            raise r.exceptions.RequestException(req)
    except r.exceptions.RequestException as e:
        print('Can\'t get burning data')
        raise e
    boost = None
    prizes_amounts = None
    burned_users = []
    for entry in req.json():
        if entry['key'] == 'boosting':
            boost = entry['value'].split('_')
        elif entry['key'] == 'prizes_amount':
            prizes_amounts = list(map(lambda x: int(x), entry['value'].split(',')))
        else:
            if "_total_burned" in entry['key']:
                burned_users.append({
                    'address': entry['key'].replace('_total_burned', ''),
                    'amount': int(entry['value'])
                })
    if boost is None or prizes_amounts is None or len(burned_users) == 0:
        raise Exception("Error with burning data")
    boost = list(map(lambda x: float(x) / 10, boost))
    burned_users = sorted(burned_users, key=lambda d: d['amount'], reverse=True)
    return boost, prizes_amounts, burned_users


def getVRF(vrf_height):
    try:
        req = r.get(NODE + '/blocks/at/' + vrf_height)
        if req.status_code != 200:
            raise r.exceptions.RequestException('Status code ' + str(req.status_code))
    except r.exceptions.RequestException as e:
        print('Can\'t get block at height ' + vrf_height)
        raise e
    return req.json()["VRF"]


def calc_amounts_with_boosting(boost, users_amount):
    count = min(len(boost), len(users_amount))
    for i in range(count):
        users_amount[i]['amount'] = int(users_amount[i]['amount'] * boost[i])
    return users_amount


def calc_user_weights_for_rand(users_amount, count):
    count = min(count, len(users_amount))
    sum_amount = sum(d['amount'] for d in users_amount[0:count])
    weights = np.zeros(count)
    for i in range(count):
        weights[i] = users_amount[i]['amount'] / sum_amount
    weights[0] += 1 - sum(weights[0:count])
    return weights


print("To start please input params:")
print("Input VRF height:")
vrf_height = input()
blockchain_height = 0
while blockchain_height < int(vrf_height):
    try:
        req = r.get(NODE + '/blocks/height')
        if req.status_code != 200:
            raise r.exceptions.RequestException('Status code ' + str(req.status_code))
    except r.exceptions.RequestException as e:
        print('Can\'t connect to node ' + e.response)
        raise e
    blockchain_height = req.json()['height']
    if blockchain_height < int(vrf_height):
        print('Block height can\'t be bigger than blockchain height')
        print("Input VRF height:")
        vrf_height = input()
print("Input secret word:")
secret = input()
print("VRF height: {0}\nSecret word: {1}\n".format(vrf_height, secret))
secret = secret + getVRF(vrf_height)
seed = int.from_bytes(h.sha256(secret.encode()).digest()[:4], 'little')
np.random.seed(seed)
boosting, prizes, users = parse_data()
users = calc_amounts_with_boosting(boosting, users)
winned_prizes = {}
uweights = calc_user_weights_for_rand(users, TOP_USERS_COUNT)
top_count = min(TOP_USERS_COUNT, len(users))

main_prize_winner = np.random.choice(range(top_count), 1, p=uweights[0:top_count], replace=False)
index = main_prize_winner[0]
winned_prizes[users[index]['address']] = MAIN_PRIZE_ID
users.pop(index)
uweights = calc_user_weights_for_rand(users, len(users))
winners = list(np.random.choice(len(users), min(len(users), sum(prizes)), p=uweights, replace=False))
for i in list(reversed(range(len(prizes)))):
    for j in range(prizes[i]):
        index = winners.pop()
        winned_prizes[users[index]['address']] = PRIZES_IDS[i]
        if not winners:
            break
    else:
        continue
    break

print(winned_prizes)
