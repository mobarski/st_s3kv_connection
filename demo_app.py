import streamlit as st
from st_s3kv_connection import S3KV
import requests

st.title('S3KV Demo')
ss = st.session_state

s3 = st.experimental_connection('my_s3', type=S3KV)
db = s3.collection('demo_s3kv')

KEYS = list(range(1,100)) # 1-99
URL = 'https://picsum.photos/300/300'

c1,c2,c3 = st.columns(3)

c1.header('Fetch Data')
c2.header('Store Data')
c3.header('Load Data')

key1 = c2.selectbox('Select Key', KEYS, key='key1', disabled='image1' not in ss)
key2 = c3.selectbox('Select Key', KEYS, key='key2')

c1,c2,c3 = st.columns(3)

with c1:
    if st.button('fetch random picture'):
        resp = requests.get(URL)
        ss['image1'] = resp.content
        ss['url1'] = resp.url.split('?')[0]
    if 'image1' in ss:
        st.image(ss['image1'], use_column_width=True)

with c2:
    if c2.button('save in DB', disabled='image1' not in ss):
        db[str(key1)] = ss['image1']

with c3:
    if c3.button('load from DB'):
        img = db[str(key2)]
        ss['image2'] = img
    if 'image2' in ss and ss['image2']:
        st.image(ss['image2'], use_column_width=True)
