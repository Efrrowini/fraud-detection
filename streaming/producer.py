import redis, time, random, json
import pandas as pd

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
QUEUE = 'txn:queue'

df = pd.read_csv('data/processed/test.csv')
records = df.to_dict('records')

print(f'Streaming {len(records):,} transactions to Redis...')
print('Press Ctrl+C to stop.')

count = 0
while True:
    record = random.choice(records)
    txn = {k: str(v) for k, v in record.items()}
    txn['txn_id'] = f'TXN{count:08d}'
    txn['timestamp'] = str(time.time())

    r.lpush(QUEUE, json.dumps(txn))
    r.ltrim(QUEUE, 0, 9999)
    count += 1

    if count % 50 == 0:
        print(f'Published {count} transactions')

    time.sleep(0.02)