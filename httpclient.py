#!/usr/bin/env python
# coding: utf-8
# Copyright 2016 Alice Wu, Abram Hindle, https://github.com/tywtyw2002, and https://github.com/treedust
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib

def help():
    print "httpclient.py [GET/POST] [URL]\n"

class HTTPResponse(object):
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body

    def __str__(self):
        return "HTTPResponse " + str(self.code) + " \n" + self.body

class HTTPRequest(object):
    # Just saw the post that we're allowed to use urlparse, what a relief...
    # but I probably won't switch anyways as mine's working properly too.
    # source: https://www.safaribooksonline.com/library/view/regular-expressions
    #         -cookbook/9781449327453/ch08s01.html
    urlPattern = "^([a-z][a-z0-9+\-.]*):(//([a-z0-9\-._~%!$&'()*+,;=]+@)?"\
               + "(?P<host>([a-z0-9\-._~%]+|\[[a-f0-9:.]+\]|\[v[a-f0-9]"\
               + "[a-z0-9\-._~%!$&'()*+,;=:]+\]))(:(?P<port>[0-9]+))?"\
               + "(?P<path>(/([a-z0-9\-._~%!$&'()*+,;=:@]+))*)/?|"\
               + "(/?[a-z0-9\-._~%!$&'()*+,;=:@]+"\
               + "(/[a-z0-9\-._~%!$&'()*+,;=:@]+)*/?)?)"\
               + "(?P<query>(\?[a-z0-9\-._~%!$&'()*+,;=:@/?]*))?"\
               + "(\#[a-z0-9\-._~%!$&'()*+,;=:@/?]*)?$"

    def __init__(self, method, requestUrl, args):
        self.method = method
        self.requestUrl = requestUrl
        self.args = args

        self.host = ""
        self.path = "/"
        self.port = "80"
        self.query = ""

        self.__parseUrl()

        self.request = self.__composeRequest()

    def __parseUrl(self):
        # fillin the scheme if the url is relative
        if not self.requestUrl.startswith("http:") and \
            not self.requestUrl.startswith("https:"):
            self.requestUrl = "http://" + self.requestUrl

        urlComponents = re.match(self.urlPattern, self.requestUrl, \
                        flags=re.IGNORECASE)

        # If it's a match, then update related values
        if urlComponents:
            urlComponentsDictionary = urlComponents.groupdict()
            self.host = self.__retrieveValue(urlComponentsDictionary, "host") \
                        or self.host
            self.path = self.__retrieveValue(urlComponentsDictionary, "path") \
                        or self.path
            self.port = self.__retrieveValue(urlComponentsDictionary, "port") \
                        or self.port
            self.query = self.__retrieveValue(urlComponentsDictionary, "query") \
                        or self.query
        else:
            return

    def __composeExactGetPath(self):
        # See if the user has specified a uri with queries but entered args too
        if self.method == "GET":
            if self.args:
                additionalQuery = urllib.urlencode(self.args)
                self.query += ("&" if self.query else "?") + additionalQuery
            self.path += self.query

    def __composeRequest(self):
        self.__composeExactGetPath()

        # Common headers
        request = self.method + " " + self.path + " " \
                + "HTTP/1.1\r\n" \
                + "Host: " + self.host + ":" + self.port + " \r\n" \
                + "Accept: text/plain\r\n" \
                + "Connection: close\r\n"

        # Set additional headers for a POST request
        if self.method == "POST":
            data = urllib.urlencode(self.args) if self.args else ""
            request += "Content-Type: application/x-www-form-urlencoded\r\n"
            request += "Content-Length: " + str(len(data))+ " \r\n"

        request += "\r\n"

        # Append data to the request if it's a POST
        # ignore query in this case since we're using form-urlencoded as
        # content-type
        if self.method == "POST":
            request += data
        print request
        return request


    def __retrieveValue(self, dict, key):
        return dict[key] if key in dict.keys() and dict[key] is not None \
            else None


class HTTPClient(object):
    #def get_host_port(self,url):

    def connect(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))   # self.host, self.port
        except socket.error as e:
            print "Socket Error: %s" % e
            sys.exit()
        return sock

    def get_code(self, data):
        return int(data.split()[1]) if data and len(data.split()) > 1 else 500

    def get_headers(self,data):
        return data.split('\r\n\r\n')[0] if data else ""

    def get_body(self, data):
        return data.split('\r\n\r\n')[1] if data \
            and len(data.split('\r\n\r\n')) > 1 else ""

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if (part):
                buffer.extend(part)
            else:
                done = not part
        return str(buffer)

    def doRequest(self, url, command, args):
        self.httpRequest = HTTPRequest(command, url, args)

        # establish connection and send request
        connection = self.connect(self.httpRequest.host, self.httpRequest.port)

        try:
            connection.sendall(self.httpRequest.request)
        except socket.error as e:
            print "Socket Error: %s" % e
            sys.exit()

        # This bit should probably go into try block for a better error handling
        # to increase stability of the program
        response = self.recvall(connection)

        code = self.get_code(response) or 500
        body = self.get_body(response) or ""
        return HTTPResponse(code, body)

    def GET(self, url, args=None):
        return self.doRequest(url, 'GET', args)

    def POST(self, url, args=None):
        return self.doRequest(url, 'POST', args)


    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST(url, args)
        else:
            return self.GET(url, args)

if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print client.command( sys.argv[2], sys.argv[1] )
    else:
        print client.command( sys.argv[1] )
