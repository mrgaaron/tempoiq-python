
#!/usr/bin/env python
# encoding: utf-8
"""
tempodb/client.py

Copyright (c) 2012 TempoDB, Inc. All rights reserved.
"""

from dateutil import parser
import requests
import simplejson
import urllib
import urllib2


API_HOST = 'api.tempo-db.com'
API_PORT = 80
API_VERSION = 'v1'


class Database(object):

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class Series(object):

    def __init__(self, i, key, attributes={}, tags=[]):
        self.id = i
        self.key = key
        self.attributes = attributes
        self.tags = tags


class DataPoint(object):

    def __init__(self, ts, value):
        self.ts = ts
        self.value = value


class Client(object):

    def __init__(self, key, secret, host=API_HOST, port=API_PORT, secure=True):
        self.key = key
        self.secret = secret
        self.host = host
        self.port = port
        self.secure = secure

    def create_database(self, name=""):
        params = {
            'name': name,
        }
        json = self.request('/database/', method='POST', params=params)
        key = json.get('id', '')
        secret = json.get('password', '')
        database = Database(key, secret)
        return database

    def get_series(self):
        json = self.request('/series/', method='GET')
        series = []
        for s in json:
            i = s.get('id', '')
            key = s.get('key', '')
            attr = s.get('attributes', {})
            tags = s.get('tags', [])
            series.append(Series(i, key, attr, tags))
        return series
    
    def read_id(self, series_id, start, end, interval=None, function=None):
        series_type = 'id'
        series_val = series_id
        return self.read(series_type, series_val, start, end, interval, function)

    def read_key(self, series_key, start, end, interval=None, function=None):
        series_type = 'key'
        series_val = series_id
        return self.read(series_type, series_val, start, end, interval, function)

    def read(self, series_type, series_val, start, end, interval=None, function=None):
        params = {
            'start': start.isoformat(),
            'end': end.isoformat(),
        }

        # add rollup interval and function if supplied
        if interval:
            params['interval'] = interval
        if function:
            params['function'] = function

        url = '/series/%s/%s/data/' % (series_type, series_val)
        json = self.request(url, method='GET', params=params)
        history = []
        for dp in json:
            ts = parser.parse(dp.get('t', ''))
            value = dp.get('v', None)
            history.append(DataPoint(ts, value))
        return history

    def request(self, target, method='GET', params={}):
        assert method in ['GET', 'POST'], "Only 'GET' and 'POST' are allowed for method."

        if method == 'GET':
            base = self.build_full_url(target, params)
            response = requests.get(base, auth=(self.key, self.secret))
        else:
            base = self.build_full_url(target)
            response = requests.post(base, data=simplejson.dumps(params), auth=(self.key, self.secret))

        if response.status_code == 200:
            json = simplejson.loads(response.text)
            #try:
            #    json = simplejson.loads(response.text)
            #except simplejson.decoder.JSONDecodeError, err:
            #    json = dict(error="JSON Parse Error (%s):\n%s" % (err, response.text))
        else:
            json = dict(error=response.text)
        return json

    def build_full_url(self, target, params={}):
        port = "" if self.port == 80 else ":%d" % self.port
        protocol = "https://" if self.secure else "http://"
        base_full_url = "%s%s%s" % (protocol, self.host, port)
        return base_full_url + self.build_url(target, params)

    def build_url(self, url, params={}):
        target_path = urllib2.quote(url)

        if params:
            return "/%s%s?%s" % (API_VERSION, target_path, self._urlencode(params))
        else:
            return "/%s%s" % (API_VERSION, target_path)

    def _urlencode(self, params):
        p = []
        for key, value in params.iteritems():
            if isinstance(value, (list, tuple)):
                for v in value:
                    p.append((key + '[]', v))
            else:
                p.append((key, value))
        return urllib.urlencode(p)


class TempoDBApiException(Exception):
    pass
