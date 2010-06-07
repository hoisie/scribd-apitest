import mako
import MultipartPostHandler
import os
import sys
import tempfile
import urllib
import urllib2
import web
import yaml

from mako.runtime import Context
from mako.template import Template
from StringIO import StringIO

API_URL = "http://api.scribd.com/api"
API_KEY_COOKIE_NAME = "SCRIBD_APITEST_API_KEY"

basedir = os.path.dirname(os.path.realpath(__file__))
template_dir=os.path.join(basedir , 'templates')

urls = (
    '/', 'Index',
    '/method', 'GetMethod',
    '/execute', 'Execute',
)

def render(template, **context):
    buf = StringIO()
    ctx = Context(buf, **context)
    template.render_context(ctx)
    return buf.getvalue()

def execute(input):
    web.header('Content-Type','text/plain; charset=utf-8')
    params={}
    if input['api_key']:
        web.setcookie(API_KEY_COOKIE_NAME, input['api_key'], 3600*24*365)
    name = input['name']
    if name not in web.config.apimethods:
        return "Could not find method" + name
    params['method']=name
    method = web.config.apimethods[name]
    print method
    for param in method['required']:
        name = param['name']
        if name not in input:
            return "Missing param: '%s'"%name
        params[name] = input[name]
    if 'optional' in method:
        for param in method['optional']:
            name = param['name']
            if name in input and input[name]!="":
                params[name] = input[name]
    if method['method'] == 'get':
        data = urllib.urlencode(params)
        return urllib2.urlopen(API_URL+'?'+data)
    elif method['method'] == 'post':
        if method['enctype'] == 'multipart/form-data':
            #create a temp file
            print input
            fd, path = tempfile.mkstemp()
            print os.write(fd, params['file'])
            params['file']=file(path, 'rb')
            opener = urllib2.build_opener( MultipartPostHandler.MultipartPostHandler)
            return opener.open(API_URL, params).read()

class Execute:
    def GET(self):
        return execute(web.input())
    def POST(self):
        return execute(web.input())

class Index:
    def GET(self):
        template = Template(filename=os.path.join(template_dir, 'index.mako.html'))
        return render(template, methods=web.config.apimethods)

class GetMethod:
    def GET(self):
        name = web.input().name
        web.header('Content-Type','text/html; charset=utf-8')
        #Check if we have a cookie storing the api_key
        api_key = web.cookies().get(API_KEY_COOKIE_NAME) or ""
        template = Template(filename=os.path.join(template_dir, 'method.mako.html'))
        if name not in web.config.apimethods:
            return "Method '%s' not available"%name
        method=web.config.apimethods[name]
        print method
        #default to a HTTP GET request
        if 'method' not in method:
            method['method'] = 'get'
        return render(template, name=name, api_key=api_key, method=method)

if __name__ == "__main__":
    sys.argv[1:] = ['6080']+sys.argv[1:]
    web.config.apimethods = yaml.load(file(os.path.join(basedir, 'api.yaml'), 'r'))
    app = web.application(urls, globals())
    app.run()
