# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging
import os
import requests
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory

WIT_API_HOST = os.getenv('WIT_URL', 'https://api.wit.ai')
WIT_API_VERSION = os.getenv('WIT_API_VERSION', '20200513')
INTERACTIVE_PROMPT = '> '
LEARN_MORE = 'Learn more at https://wit.ai/docs/quickstart'


class WitError(Exception):
    pass


def req(logger, access_token, meth, path, params, **kwargs):
    full_url = WIT_API_HOST + path
    logger.debug('%s %s %s', meth, full_url, params)
    headers = {
        'authorization': 'Bearer ' + access_token,
        'accept': 'application/vnd.wit.' + WIT_API_VERSION + '+json'
    }
    headers.update(kwargs.pop('headers', {}))
    rsp = requests.request(
        meth,
        full_url,
        headers=headers,
        params=params,
        **kwargs
    )
    if rsp.status_code > 200:
        raise WitError('Wit responded with status: ' + str(rsp.status_code) +
                       ' (' + rsp.reason + ')')
    json = rsp.json()
    if 'error' in json:
        raise WitError('Wit responded with an error: ' + json['error'])

    logger.debug('%s %s %s', meth, full_url, json)
    return json


class Wit(object):
    access_token = None
    _sessions = {}

    def __init__(self, access_token, logger=None):
        self.access_token = access_token
        self.logger = logger or logging.getLogger(__name__)

    def message(self, msg, context=None, n=None, verbose=None):
        params = {}
        if n is not None:
            params['n'] = n
        if msg:
            params['q'] = msg
        if context:
            params['context'] = json.dumps(context)
        if verbose:
            params['verbose'] = verbose
        resp = req(self.logger, self.access_token, 'GET', '/message', params)
        return resp

    def create_entity(self, data={}):
        params = {}
        headers = {'Content-Type': 'application/json'}
        resp = req(self.logger, self.access_token, 'POST', '/entities', params=params, headers=headers, data=json.dumps(data))
        return resp
        
    def post_utterances(self,data=""):
        params = {}
        headers = {'Content-Type': 'application/json'}
        resp = req(self.logger, self.access_token, 'POST', '/utterances', params=params,headers=headers, data=data)
        return resp

    def get_utterances(self,limit=100,version=None):
        params = {}
        params['limit'] = limit
        resp = req(self.logger, self.access_token, 'GET', '/utterances', params)
        return resp
    
    def retrieve_the_list_of_all_the_entities_in_your_app(self):
        params = {}
        resp = req(self.logger, self.access_token, 'GET', '/entities', params)
        return resp

    def retrieve_all_information_about_an_entity(self,entity):
        params = {}
        resp = req(self.logger, self.access_token, 'GET', '/entities/'+str(entity), params)
        return resp

    def update_the_information_of_an_entity(self, entity, roles=[]):
        params = {}
        if roles==[]:
            roles.append(entity)
        
        keyword = 'תל אביב'
        synonyms = ["תא"]
        keyword_dict = dict({'keyword': keyword, 'synonyms': synonyms})

        headers = {'Content-Type': 'application/json'}
        data = dict({
                    'name': entity,
                    'roles': list(set(roles)),
                    'lookups': ["free-text", "keywords"],
                    'keywords': [keyword_dict]
                    })
        resp = req(self.logger, self.access_token, 'PUT', '/entities/'+str(entity), params, headers=headers, data=data)
        return resp

    def add_new_values_to_a_keywords_entity(self,entity,keyword,synonyms = []):
        params = {}
        headers = {'Content-Type': 'application/json'}
        synonyms.append(keyword)
        synonyms = list(set(synonyms))
        data = dict({'keyword': keyword, 'synonyms': synonyms})
        # data = json.dumps(data)
        # print(data)
        resp = req(self.logger, self.access_token, 'POST', '/entities/'+entity + '/keywords', params=params, headers=headers, data=data)
        return resp
    ## Intents
    def create_intent(self, data={}):
        params = {}
        headers = {'Content-Type': 'application/json'}
        resp = req(self.logger, self.access_token, 'POST', '/intents', params=params, headers=headers, data=json.dumps(data))
        return resp

    ## Manage Apps
    def get_apps(self,limit=5,version=None):
        params = {}
        params['limit'] = limit
        params['offset'] = 1
        headers = {'Content-Type': 'application/json'}
        resp = req(self.logger, self.access_token, 'GET', '/apps', params=params,headers=headers)
        return resp

    def create_new_app(self,name):
        params = {}
        headers = {'Content-Type': 'application/json'}
        data = {"name": name, "lang": "he", "private": True}
        data = json.dumps(data)
        resp = req(self.logger, self.access_token, 'POST', '/apps', params=params,data=data, headers=headers)
        return resp

    def speech(self, audio_file, headers=None, verbose=None):
        """ Sends an audio file to the /speech API.
        Uses the streaming feature of requests (see `req`), so opening the file
        in binary mode is strongly recommended (see
        http://docs.python-requests.org/en/master/user/advanced/#streaming-uploads).
        Add Content-Type header as specified here: https://wit.ai/docs/http/20200513#post--speech-link

        :param audio_file: an open handler to an audio file
        :param headers: an optional dictionary with request headers
        :param verbose: for legacy versions, get extra information
        :return:
        """
        params = {}
        headers = headers or {}
        if verbose:
            params['verbose'] = True
        resp = req(self.logger, self.access_token, 'POST', '/speech', params,
                   data=audio_file, headers=headers)
        return resp

    def interactive(self, handle_message=None, context=None):
        """Runs interactive command line chat between user and bot. Runs
        indefinitely until EOF is entered to the prompt.

        handle_message -- optional function to customize your response.
        context -- optional initial context. Set to {} if omitted
        """
        if context is None:
            context = {}

        history = InMemoryHistory()
        while True:
            try:
                message = prompt(INTERACTIVE_PROMPT, history=history, mouse_support=True).rstrip()
            except (KeyboardInterrupt, EOFError):
                return
            if handle_message is None:
                print(self.message(message, context))
            else:
                print(handle_message(self.message(message, context)))
