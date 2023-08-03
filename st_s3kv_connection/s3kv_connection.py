# TODO: ttl option
# TODO: compression level option

from streamlit.connections import ExperimentalBaseConnection
import boto3
import botocore

import os

from . s3kv import get_kv

S3_CLIENT_OPTIONS = {
    'secret_key': 'aws_secret_access_key',
    'access_key': 'aws_access_key_id',
    'endpoint':   'endpoint_url',
    'region':     'region_name',
    # '':'aws_session_token', # TODO: this is not supported yet
}
OTHER_OPTIONS = ['bucket', 'prefix', 'path', 'data', 'salt', 'addressing', 'ttl']


class S3KV(ExperimentalBaseConnection):

    def collection(self, name, **kwargs):
        kw = kwargs.copy()
        kw['s3_client'] = self._instance
        self._update_kw_dict(kw, OTHER_OPTIONS, self.kwargs)
        kv_obj = get_kv(self.mode, name, **kw)
        # handle TTL by monkey patching kv object
        ttl = kw.get('ttl', None)
        if ttl:
            from streamlit import cache_data
            kv_obj.__getitem__ = cache_data(kv_obj.__getitem__, ttl=ttl)
            ... # TODO: other methods ???
        return kv_obj


    def _connect(self, **kwargs):
        self.mode = kwargs.pop('mode', 's3')
        self.kwargs = self._update_kw_dict(None, OTHER_OPTIONS, kwargs)

        if self.mode == 's3':
            s3_kwargs = self._update_kw_dict(None, S3_CLIENT_OPTIONS, kwargs)
            if 'addressing' in self.kwargs:
                addressing = self.kwargs['addressing']
                s3_kwargs['config'] = botocore.config.Config(s3={'addressing_style': addressing})
                # REF: https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/s3.html
            session = boto3.session.Session()
            s3_client = session.client('s3', **s3_kwargs)
            return s3_client
        else:
            return None


    # TODO: THIS IS UGLY AS F*** !!!
    def _update_kw_dict(self, kw=None, options=[], other_kw={}):
        if kw is None:
            kw = {}
        for k in options:
            # translate option name
            if type(options) is dict:
                key = options[k]
            else:
                key = k
            # skip if already in kw
            if key in kw: continue
            # get value and add to kw
            v = self._get_param(k, other_kw)
            if v is not None:
                kw[key] = v
        return kw


    def _get_param(self, key, other_kw={}):
        if key in other_kw:
            return other_kw[key]
        env_key = f'{self._connection_name}_{key}'
        if env_key in os.environ:
            return os.environ[env_key]
        if key in self._secrets:
            return self._secrets[key]
