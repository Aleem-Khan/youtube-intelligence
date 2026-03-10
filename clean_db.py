import sqlite3

conn = sqlite3.connect('intelligence.db')
c = conn.cursor()

bad = [
    'UCftUwav0Av97LwlQ-m0G1sw',
    'UClpbzZkyGk4Wk8S7tuVvXCw',
    'UCI3AcTL9ESEmK8U6uvqzCOg'
]

for cid in bad:
    c.execute('DELETE FROM channels WHERE channel_id=?', (cid,))
    print('Removed:', cid)

c.execute('DELETE FROM channels WHERE niche="history and mysteries" AND total_views=0')
print('Cleared history channels with missing view data')

conn.commit()
conn.close()
print('Done')