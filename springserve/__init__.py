
#import all of this version information
__version__ = '0.0.6'
__author__ = 'dave@springserve.com'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2016 Springserve'
__title__ = 'springserve'


import sys as _sys
import json as _json

from link import lnk as _lnk

_API = None

def API():
    global _API

    if _API is None:
       _API = _lnk.springserve
    
    return _API

class _TabComplete(object):
    """
    this class exists to make any other class 
    have a tab completion function that is already 
    hooked into ipython 
    """
    def _tab_completions(self):
        return []



class _VDAPIResponse(_TabComplete):

    def __init__(self, service, api_response_data, path_params, query_params, ok):
        super(_VDAPIResponse, self).__init__()
        self._service = service
        self._raw_response = api_response_data
        self._path_params = path_params
        self._query_params = query_params or {}
        self._ok = ok
    
    @property
    def ok(self):
        return self._ok

    @property
    def raw(self):
        return self._raw_response

    def __getitem__(self, key):
        
        if isinstance(key, str):
            return self.raw[key]
        elif isinstance(key, int):
            return self.raw[key]

    def __getattr__(self, key):
        """
        This is where the magic happens that allows you to treat this as an
        object that has all of the fields that the api returns.  I seperate all
        of the returned data in self._data
        """

        # if it's not there then try to get it as an attribute
        try:
            return self.__getattribute__(key)
        except AttributeError as e:
            #makes unpickling work?
            if key.startswith("__"):
                raise e
            return self._raw_response[key]
    
    def _tab_completions(self):

        if not self.raw:
            return []

        return self.raw.keys()

    
class _VDAPISingleResponse(_VDAPIResponse):

    def __init__(self, service, api_response_data, path_params, query_params, ok):
        super(_VDAPISingleResponse, self).__init__(service, api_response_data,
                                             path_params, query_params, ok)

    def save(self):
        """
        Today you can only save on the single response
        """
        return self._service.put(self.id, self.raw)

    def __setattr__(self, attr, value):
        """
        If it's a property that was already defined when the class
        was initialized that let it exist.  If it's new than let's slap it into
        _data.  This allows us to set new attributes and save it back to the api
        """
        # allows you to add any private field in the init
        # I could do something else here but I think it makes
        # sense to enforce private variables in the ConsoleObject
        if attr.startswith('_'):
            self.__dict__[attr] = value

        if attr in self.__dict__:
            self.__dict__[attr] = value
        else:
            # TODO - this is the only place where appnexus object fields get changed?
            self._raw_response[attr] = value


class _VDAPIMultiResponse(_VDAPIResponse):

    def __init__(self, service, api_response_data, path_params, query_params,
                 response_object, ok):

        super(_VDAPIMultiResponse, self).__init__(service, api_response_data,
                                             path_params, query_params, ok)
        self._object_cache = []
        self._current_page = 1
        self._all_pages_gotten = False
        self.response_object = response_object
        #build out the initial set of objects
        self._build_cache(self.raw)
    
    def _build_cache(self, objects):
        self._object_cache.extend([self._build_response_object(x) for x in
                                   objects])
    
    def _is_last_page(self, resp):
        #this means we 
        return (not resp or not resp.json)

    def _get_next_page(self):

        if self._all_pages_gotten:
            return 

        params = self._query_params.copy()
        params['page'] = self._current_page+1
        resp = self._service.get_raw(self._path_params, **params)
        
        # this means we are donesky, we don't know 
        # how many items there will be, only that we hit the last page
        if self._is_last_page(resp):
            self._all_pages_gotten = True
            return

        self._build_cache(resp.json)
        self._current_page += 1 

    def _build_response_object(self, data):
        return self.response_object(self._service, data,
                                        self._path_params,
                                        self._query_params, True)
    def __getitem__(self, key):
        if not isinstance(key, int):
            raise Exception("Must be an index ")
        if key >= len(self._object_cache):
            if self._all_pages_gotten:
                raise IndexError("All pages gotten, no such object")
            self._get_next_page()
            return self[key]
        return self._object_cache[key]

    def __iter__(self):
        """
        this will automatically take care of pagination for us. 
        """
        idx = 0
        while True:
            # not sure I love this method, but it's the best 
            # one I can think of right now
            try:
                yield self[idx]
                idx += 1
            except IndexError as e:
                break


def _format_url(endpoint, path_param, query_params):

    _url = endpoint

    if path_param:
        _url += "/{}".format(path_param)

    if query_params and isinstance(query_params, dict):
        params = "&".join(["{}={}".format(key, value) for key,value in
                           query_params.iteritems()])
        _url += "?{}".format(params)

    return _url

 
class _VDAPIService(object):
    
    __API__ = None
    __RESPONSE_OBJECT__ = _VDAPISingleResponse
    __RESPONSES_OBJECT__ = _VDAPIMultiResponse
    
    def __init__(self):
        pass 

    @property
    def endpoint(self):
        return "/" + self.__API__
   
    def build_response(self, api_response, path_params, query_params):
        is_ok = api_response.ok

        resp_json = api_response.json
        
        if isinstance(resp_json, list):
            #wrap it in a multi container
            return self.__RESPONSES_OBJECT__(self, resp_json, path_params,
                                        query_params, self.__RESPONSE_OBJECT__,
                                            is_ok)

        return self.__RESPONSE_OBJECT__(self, resp_json, path_params,
                                        query_params,is_ok)
    
    def get_raw(self, path_param=None, **query_params):
        return API().get(_format_url(self.endpoint, path_param, query_params))

    def get(self, path_param=None, **query_params):
        global API
        return self.build_response(
            self.get_raw(path_param, **query_params),
            path_param, 
            query_params
        )
    
    def put(self, path_param, data, **query_params):
        global API
        return self.build_response(
                API().put(_format_url(self.endpoint, path_param, query_params),
                          data = _json.dumps(data)
                         ),
                path_param, 
                query_params
        )

    def new(self, data, path_param = "", **query_params):
        global API
        return self.build_response(
                API().post(_format_url(self.endpoint, path_param, query_params),
                          data = _json.dumps(data)
                         ),
                path_param, 
                query_params
        )
 

from _supply import _SupplyTagAPI
from _demand import _DemandTagAPI
from _common import _DomainListAPI

supply_tags = _SupplyTagAPI()
demand_tags = _DemandTagAPI()
domain_lists = _DomainListAPI()


def raw_get(path_param, **query_params):
    global API
    return API().get(_format_url("", path_param, query_params)).json


def _install_ipython_completers():  # pragma: no cover

    from IPython.utils.generics import complete_object

    @complete_object.when_type(_TabComplete)
    def complete_report_object(obj, prev_completions):
        """
        Add in all the methods of the _wrapped object so its
        visible in iPython as well
        """
        prev_completions+=obj._tab_completions()
        return prev_completions


# Importing IPython brings in about 200 modules, so we want to avoid it unless
# we're in IPython (when those modules are loaded anyway).
# Code attributed to Pandas, Thanks Wes 
if "IPython" in _sys.modules:  # pragma: no cover
    try:
        _install_ipython_completers()
    except Exception:
        msg.debug("Error loading tab completers")
        pass 
