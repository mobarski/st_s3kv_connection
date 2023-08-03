# Streamlit S3KV Connection

Connect from Streamlit to S3 and use it as an encrypted key-value database.



Features:

- key-value (dict) interface → easy to use
- cloudpickle serialization → serialize anything
- data at rest encryption (AES) → better data security
- compression →faster transfers, lower storage costs
- ability to work without S3 → easy testing
- caching →less transfers



**Note**

The S3KV connection communicates with S3 in the cloud, which can  introduce latency compared to a local key-value store. This makes it  less ideal for use cases requiring millisecond response times.

However, the S3KV connection excels at securely storing large  documents like JSON, CSV, PDFs, images, etc. The cloud storage and  compression provide very cost-effective storage for large amounts of  data. The encryption keeps sensitive documents secure. So while not the  fastest, the S3KV connection offers inexpensive, encrypted document  storage with a simple key-value interface. The latency trade-off is  often worth it for document-heavy use cases.



## Installation

`pip install git+https://github.com/mobarski/st_s3kv_connection`



## Quick demonstration

```python
import streamlit as st
from st_s3kv_connection import S3KV

s3 = st.experimental_connection('my_kv', type=S3KV)
db = s3.collection('my-collection')

db['my-key'] = '1234567890' * 10_000_000

st.write(len(db['my-key']))
st.write(db['my-key'][:100])
```

**No S3? No problem!**

```python
s3 = st.experimental_connection('my_kv', type=S3KV, mode='local', path='path/to/local/data/directory')
```

```python
s3 = st.experimental_connection('my_kv', type=S3KV, mode='dict')
```



## Main methods



#### collection()

`connection.collection(name, **kwargs) -> dictionary-like object`

Get dictionary-like object that can be used to interact with the collection.



## Configuration

The connection configuration can be:

- passed via collection kwargs
- passed via connection kwargs
- passed through environmental variables
- stored in Streamlit's [secrets.toml](https://docs.streamlit.io/library/advanced-features/secrets-management) file (~/.streamlit/secrets.toml on Linux)

You can find more information about managing connections in [this section](https://docs.streamlit.io/library/advanced-features/connecting-to-data#global-secrets-managing-multiple-apps-and-multiple-data-stores) of Streamlit documentation **and some examples below**.



##### most importatnt parameters

- `mode` - connection mode
  - `s3` - store data in S3 bucket

  - `local` - store data in local directory

  - `dict` - store data in RAM

- `password` - password that will be used to generate data encryption key (default: '')

- `salt` - cryptographic salt that will be used to generate data encryption key (default: '')

- `ttl` - Streamlit's cache time-to-live option (default: None → no caching), more info [here](docs.streamlit.io/library/advanced-features/caching#controlling-cache-size-and-duration)



##### mode = 's3'

- `access_key` - access key for the account
- `secret_key ` - secret key for the account
- `endpoint` - endpoint URL (required for providers other than AWS)
- `addressing` - [addressing style](https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/s3.html#changing-the-addressing-style) [`path`|`auto`|`virtual`] (default: '' → 'auto')
- `region` - region to use
- `bucket` - bucket name
- `prefix` - prefix to use for all the keys (default: '')



##### mode = 'local'

- `path` - directory where the data will be stored (default: '' → current working directory)



##### mode = 'dict'

- `data` - dictionary-like object that will be used to store the data (default: None → new dictionary will be created)

  

## Usage examples



##### simple_app.py

```python
import streamlit as st
import numpy as np
from st_s3kv_connection import S3KV

s3 = st.experimental_connection('my_kv', type=S3KV)
db = s3.collection('examples', 'password-to-this-collection')

db['key1'] = "🎈"
db['key2'] = {'name':'Boaty McBoatface', 'launched':2017}
db['key3'] = np.array([42, 2501, 1337])
db['key4'] = lambda x: f'Hello {x}!'

st.write(db['key1'])
st.write(db['key4'](db['key2']['name']))

del db['key3']
st.write(db.keys())
```



##### demo_app.py

You can find live demo of this app [here](https://s3kv-demo.streamlit.app)

```python
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
```



## Configuration examples



##### secrets.toml

```toml
[connections.my_kv]
access_key = "XXXXXXXXXXXXXXXXXXXX"
secret_key = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
endpoint   = "https://sfo3.digitaloceanspaces.com" # NOT REQUIRED ON AWS
region = "sfo3"
bucket = "my-bucket-name"
prefix = "something/version-1"  # NOT REQUIRED
password = "my-secret-password" # NOT REQUIRED
salt = "crypto-salt" # NOT REQUIRED

[connections.my_kv2]
mode = "local"
path = "/mnt/data/my-kv2-data"
```



##### environmental variables

```bash
my_kv_access_key = "XXXXXXXXXXXXXXXXXXXX"
my_kv_secret_key = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
my_kv_endpoint   = "https://sfo3.digitaloceanspaces.com"
my_kv_region = "sfo3"
my_kv_bucket = "my-bucket-name"
my_kv_prefix = "something/version-1"
my_kv_password = "my-secret-password"
my_kv_salt = "crypto-salt"

my_kv2_mode = "local"
my_kv2_path = "/mnt/data/my-kv2-data"
```



##### connection kwargs

```python
# override my_kv connection mode to test it offline / without S3
s3 = st.experimental_connection('my_kv', type=S3KV, mode="dict")

# persistent local storage 
s3 = st.experimental_connection(None, type=S3KV, mode="local", path="data", password="xxx")
```

