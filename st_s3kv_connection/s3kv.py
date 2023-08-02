"Storage adapter - one collection for each user / api_key"

# pip install pycryptodome
# REF: https://www.pycryptodome.org/src/cipher/aes
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad,unpad

# pip install cloudpickle
import cloudpickle as pickle

# pip install boto3
import boto3
import botocore

#from retry import retry

from binascii import hexlify,unhexlify
from collections import OrderedDict
import hashlib
import zlib
import os
import io

class Storage:
	"Encrypted object storage (base class)"
	
	def __init__(self, collection, **kw):
		passwd = kw.pop('password','')
		salt = kw.pop('salt','')
		salt = unhexlify(salt)
		self.passwd = hashlib.blake2s(passwd.encode('utf8'), salt=salt, person=b'passwd', digest_size=32).hexdigest() if passwd else None
		self.collection = self.encode(collection) # to protect against forbidden characters in filenames/paths
		self.AES_MODE = AES.MODE_ECB # TODO: better AES mode ???
		self.AES_BLOCK_SIZE = 16
	
	def get(self, name, default=None):
		"get one object from the collection"
		safe_name = self.encode(name)
		try:
			data = self._get(safe_name)
		except: # TODO: catch only expected exceptions
			return default
		obj = self.deserialize(data)
		return obj
	
	def put(self, name, obj):
		"put the object into the collection"
		safe_name = self.encode(name)
		data = self.serialize(obj)
		self._put(safe_name, data)
		return data

	def list(self):
		"list object names from the collection"
		return [self.decode(name) for name in self._list()]

	def delete(self, name):
		"delete the object from the collection"
		safe_name = self.encode(name)
		self._delete(safe_name)
	

	# DICT LIKE INTERFACE

	def __getitem__(self, name):
		return self.get(name)

	def __setitem__(self, name, obj):
		return self.put(name, obj)

	def __delitem__(self, name):
		return self.delete(name)

	def __contains__(self, name):
		safe_name = self.encode(name)
		return self._has(safe_name)

	def __len__(self):
		return len(self.keys())

	def keys(self):
		return self.list()

	def items(self):
		return ((name, self.get(name)) for name in self.keys())

	def update(self, data):
		items = data.items() if isinstance(data, dict) else data
		for name, obj in items:
			self.put(name, obj)
	
	def pop(self, name, default=None):
		obj = self.get(name, default)
		if name in self:
			self.delete(name)
		return obj

	# IMPLEMENTED IN SUBCLASSES
	def _put(self, name, data):
		...
	def _get(self, name):
		...	
	def _delete(self, name):
		pass
	def _list(self):
		...
	def _has(self, name):
		...
	
	# # #
	
	def serialize(self, obj):
		raw = pickle.dumps(obj)
		compressed = self.compress(raw)
		encrypted = self.encrypt(compressed)
		return encrypted
	
	def deserialize(self, encrypted):
		compressed = self.decrypt(encrypted)
		raw = self.decompress(compressed)
		obj = pickle.loads(raw)
		return obj

	def encrypt(self, raw):
		if self.passwd:
			cipher = AES.new(unhexlify(self.passwd), self.AES_MODE)
			return cipher.encrypt(pad(raw, self.AES_BLOCK_SIZE))
		else:
			return raw
	
	def decrypt(self, encrypted):
		if self.passwd:
			cipher = AES.new(unhexlify(self.passwd), self.AES_MODE)
			return unpad(cipher.decrypt(encrypted), self.AES_BLOCK_SIZE)
		else:
			return encrypted

	def compress(self, data):
		return zlib.compress(data)
	
	def decompress(self, data):
		return zlib.decompress(data)
	
	# to protect against forbidden characters in filenames/paths
	def encode(self, name):
		return hexlify(name.encode('utf8')).decode('utf8')
	
	# to protect against forbidden characters in filenames/paths
	def decode(self, name):
		return unhexlify(name).decode('utf8')


class DictStorage(Storage):
	"Dictionary based storage"
	
	def __init__(self, collection, data_dict, **kw):
		super().__init__(collection, **kw)
		self.data = data_dict
		
	def _put(self, name, data):
		if self.collection not in self.data:
			self.data[self.collection] = {}
		if name in self.data[self.collection]:
			del self.data[self.collection][name] # to preserve insertion time
		self.data[self.collection][name] = data
		
	def _get(self, name):
		return self.data[self.collection][name]
	
	def _list(self):
		return list(self.data.get(self.collection,{}).keys())[::-1] # sorted by insertion time (newest first)
	
	def _delete(self, name):
		del self.data[self.collection][name]
	
	def _has(self, name):
		return name in self.data.get(self.collection,{})


class LocalStorage(Storage):
	"Local filesystem based storage"
	
	def __init__(self, collection, path, **kw):
		super().__init__(collection, **kw)
		self.path = os.path.join(path, self.collection)
		if not os.path.exists(self.path):
			os.makedirs(self.path)
	
	def _put(self, name, data):
		with open(os.path.join(self.path, name), 'wb') as f:
			f.write(data)

	def _get(self, name):
		with open(os.path.join(self.path, name), 'rb') as f:
			data = f.read()
		return data
	
	def _list(self):
		# TODO: sort by modification time (reverse=True)
		return os.listdir(self.path)

	def _delete(self, name):
		os.remove(os.path.join(self.path, name))

	def _has(self, name):
		return os.path.exists(os.path.join(self.path, name))


class S3Storage(Storage):
	"S3 based encrypted storage"
	
	def __init__(self, collection, bucket, s3_client, **kw):
		super().__init__(collection, **kw)
		self.s3 = s3_client
		self.bucket = bucket
		self.prefix = kw.get('prefix','')
	
	def get_key(self, name):
		return f'{self.prefix}/{self.collection}/{name}'
	
	def _put(self, name, data):
		key = self.get_key(name)
		f = io.BytesIO(data)
		self.s3.upload_fileobj(f, self.bucket, key)
	
	def _has(self, name):
		key = self.get_key(name)
		try:
			self.s3.head_object(Bucket=self.bucket, Key=key)
			return True
		except botocore.exceptions.ClientError as e:
			if e.response['Error']['Code'] == "404":
				return False
			else:
				raise

	def _get(self, name):
		key = self.get_key(name)
		f = io.BytesIO()
		self.s3.download_fileobj(self.bucket, key, f)
		f.seek(0)
		return f.read()
	
	def _list(self):
		resp = self.s3.list_objects(
				Bucket=self.bucket,
				Prefix=self.get_key('')
			)
		contents = resp.get('Contents',[])
		contents.sort(key=lambda x:x['LastModified'], reverse=True)
		keys = [x['Key'] for x in contents]
		names = [x.split('/')[-1] for x in keys]
		return names
	
	def _delete(self, name):
		self.s3.delete_object(
				Bucket=self.bucket,
				Key=self.get_key(name)
			)


def get_kv(mode, collection, **kw):
	"get KV storage adapter"
	if mode=='s3':
		s3_client = kw.pop('s3_client')
		bucket = kw.pop('bucket')
		return S3Storage(collection, bucket, s3_client, **kw)
	elif mode=='local':
		path = kw.pop('path','.')
		return LocalStorage(collection, path, **kw)
	elif mode=='dict':
		data_dict = kw.pop('data',{})
		return DictStorage(collection, data_dict, **kw)


if __name__=="__main__":
	#x = DictStorage('my-collection', password='x', {'a':1})
	#x = LocalStorage('my-collection', password='x', '../usunmnie')
	#x = get_kv('local', 'my-collection', password='x', path='../usunmnie')
	x = get_kv('dict', 'my-collection', password='x', data={'a':1})
	x.put('a', [1,2,3])
	x.put('b', [3,2,1])
	print('a' in x)
	print('c' in x)
	x.update({'x':1,'y':2})
	x.update([('z',3), ('q',4)])
	x['a'] = 123
	print(x.keys())
	print(list(x.items()))
	print(len(x))
	print(x.pop('K'))
