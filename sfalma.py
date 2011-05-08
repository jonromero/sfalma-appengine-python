"""
Sfalma middleware for Appengine

Jon Vlachoyiannis (jon@sfalma.com)
"""

import logging
import logging.handlers
import traceback

import urllib, urllib2
import os
from datetime import datetime
import simplejson as json

SFALMA_API_KEY = "f8c05a0b"
SFALMA_ADDRESS = "http://www.sfalma.com/api/errors"

class SfalmaHandler(logging.Handler):
    
    def __init__(self):
	logging.Handler.__init__(self)
	self.is_logging = False
    
    def emit(self, record):
	if self.is_logging:
	    return

	self.is_logging = True

        #signature = self.__GetSignature(record.exc_info)
        record_string = self.format(record)

        self.send_error(record_string)
        

    def _get_url(self):
        if os.environ['SERVER_PORT'] == '80':
            scheme = 'http://'
        else:
            scheme = 'https://'
        host = os.environ['SERVER_NAME']
        script_name = urllib.quote(os.environ['SCRIPT_NAME'])
        path_info = urllib.quote(os.environ['PATH_INFO'])
        qs = os.environ.get('QUERY_STRING', '')
        
        if qs:
            qs = '?' + qs
        return scheme + host + script_name + path_info + qs

    def _relative_path(self, path):
        cwd = os.getcwd()
        if path.startswith(cwd):
            path = path[len(cwd)+1:]
        return path

    def _get_signature(self, exc_info):
        ex_type, unused_value, trace = exc_info
        frames = traceback.extract_tb(trace)

        fulltype = '%s.%s' % (ex_type.__module__, ex_type.__name__)
        path, line_no = frames[-1][:2]
        path = self._relative_path(path)
        site = '%s:%d' % (path, line_no)
        signature = '%s@%s' % (fulltype, site)

        return signature

    def send_error(self, error_log):
	try:
            app_root = os.getcwd()
            app_version, tdeploy = os.environ['CURRENT_VERSION_ID'].split(".")

            error_lines = error_log.splitlines()
            message = error_lines[0]
            klass = error_lines[-1].split(":")[0]

            #maybe a regex?
            where = "/".join(filter(lambda x: app_root in x, error_lines)[0].split("/")[-3:]).split(", in")[0].replace('", line', ":")

            error = {"request": {"remote_ip": "",
                                 "req_method": os.environ['REQUEST_METHOD'],
                                 "parameters": {},
                                 "url": self._get_url(),
                                 "session": {}},
                     "clients": {"name": "sfalma-appengine",
                                 "protocol_version": 1,
                                 "version": "0.6"},
                     "exception": {"occured_at": str(datetime.now()),
                                   "message": message,  
                                   "where": where,
                                   "klass": klass,
                                   "backtrace": error_lines},           
                     "application_environment": {"headers": {},
                                                 "appver": app_version,
                                                 #"app_root": app_root, #nope
                                                 "lang": "python",
                                                 #"lang_ver": "bla",
                                                 "os": os.environ['SERVER_SOFTWARE'],
                                                 #"module": module[3:],
                                                 #"environment": "staging", #fixme
                                                 "appid": os.environ['APPLICATION_ID'],
                                                 "tdeploy": tdeploy}
                     }
            self._send_json(SFALMA_API_KEY, error)			
        except:
            pass
        finally:
            self.is_logging = False
        
        raise




    def _send_json(self, api_key, data):
        headers = {
            'X-Sfalma-Api-Key': api_key,
            }	
        
        data_encoded = urllib.urlencode({"data": json.dumps(data)})
        req = urllib2.Request(SFALMA_ADDRESS, data_encoded, headers)
        f = urllib2.urlopen(req)
	
        response = f.read()
        f.close()


    @classmethod
    def install(self):
        if hasattr(logging.handlers,'SfalmaHandler'):
            return
        logging.handlers.SfalmaHandler = self
        
        # create handler
        handler = SfalmaHandler()
        handler.setLevel(logging.ERROR)
        
        # add the handler
        logger = logging.getLogger()
        logger.addHandler(handler)
