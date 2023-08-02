import streamlit as st
import numpy as np
from st_s3kv_connection import S3KV
from time import time

data = {}
#s3 = st.experimental_connection('my_s3', type=S3KV, mode='local', path='usunmnie')
s3 = st.experimental_connection('my_s3', type=S3KV, mode='dict', data=data, salt='2121')
#s3 = st.experimental_connection('my_s3', type=S3KV)
db = s3.collection('examples', salt='1234') # TODO: override salt from secrets / connection

if 1:
    db['key1'] = "🎈"
    db['key2'] = {'name':'Boaty McBoatface', 'launched':2017}
    db['key3'] = np.array([42, 2501, 1337])
    db['key4'] = lambda x: f'Hello {x}!'

print(db.keys())
t0 = time()
print(db['key1'])
print(db['key2'])

print(db['key3'])
t1 = time()
del db['key3']
print(db['key3'])

print(db['key4'])
print(db['key4'](db['key2']['name']))
print(db.keys())

print(t1-t0, (t1-t0)/3)
db['x'] = '1234567890' * 10_000_000
print(len(data['6578616d706c6573']['78']))
#print(f'{s3.kwargs=}')
