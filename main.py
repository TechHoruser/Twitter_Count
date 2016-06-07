# #!/usr/bin/env python
# -*- coding: utf-8 -*-

import twitter
import json
import time
import requests
import urlparse
import datetime
import oauth2
import re
import sys
import httplib, urllib

from datetime import timedelta
from flask import Flask, request, render_template, redirect
from flask.ext.googlemaps import GoogleMaps
from flask.ext.googlemaps import Map

CONSUMER_KEY='OLDLHqzjpVgOndpKVOlv2Wt23'
CONSUMER_SECRET='y5q0NHmRRiTZZrcWcTnCgIiXBsU29FGUC2cqtcYGca9eADFZrk'
OAUTH_TOKEN = ""
OAUTH_TOKEN_SECRET = ""

consumer = ""
request_token = ""

tweetsList = {}


"""   FICHERO   """


"""   FICHERO   """

def cargarFichero():
    global tweetsList

    f=file("tweets", "r")
    lines=f.read().split()
    f.close()
    expresion = re.compile('(.*)?<->(.*)?<->(.*)?')
    
    for line in lines:
        g = expresion.findall(line)
        tweetsList[int(g[0][0])]=[int(g[0][1]), float(g[0][2])]


def guardarFichero():
    f=file("tweets","w");
    for e in tweetsList:
        f.write(str(e)+"<->"+str(tweetsList[e][0])+"<->"+str(tweetsList[e][1])+"\n")
        
    f.close()



"""   THINGSPEAK   """

def actualizarTL(vec):
    for e in vec:
        tweetsList[e][1] = (tweetsList[e][1]*tweetsList[e][0]+vec[e])/(tweetsList[e][0]+1)
        tweetsList[e][0] += 1

def clearChannel():
    params = urllib.urlencode({'key': 'L9TUFV056YFBZKV5'})
    f = urllib.urlopen("https://api.thingspeak.com/channels/119515/clear", data=params)

def addTS(fecha, valor):
    # ThingSpeak
    params = urllib.urlencode({'field2': valor, 'key':'L9TUFV056YFBZKV5', 'created_at':fecha})
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection("api.thingspeak.com:80")
    conn.request("POST", "/update", params, headers)
    response = conn.getresponse()
    print "Thingspeak - ", response.status, response.reason

    data = response.read()
    conn.close()

def streamFun(valor):
    global tweetsList

    print "----------------\n\nActualizando diccionario y fichero"
    cargarFichero()
    actualizarTL(valor)
    guardarFichero()
    print "Diccionario y fichero actualizado\n"

    print "----------------\n\nLimpiado de canal"
    clearChannel()
    time.sleep(15)

    print "Empezando a subir valores..."
    for e in tweetsList:
        fecha = datetime.datetime(2016, 1, 1, e, 1, 1, 1)
        addTS(fecha, tweetsList[e][1])
        print ("Subida de la hora " + str(e))
        time.sleep(15)
    print "Finalizada sincronización ThingSpeak\n"



"""   TWITTER   """

def numTweets(lista):
    num = {}
    for i in range(0,24):
        num[i] = 0
    for resultado2 in lista:
        for resultado in resultado2:
            # Coge los tweets del último día
            if ( datetime.datetime.strptime(resultado["created_at"], '%a %b %d %H:%M:%S +0000 %Y') + timedelta(hours=1) <
                datetime.datetime.now() and 
                datetime.datetime.strptime(resultado["created_at"], '%a %b %d %H:%M:%S +0000 %Y') + timedelta(hours=1) >
                datetime.datetime.now() - timedelta(hours=24) ):
                # Selecciona la fecha del tweet
                fechaTweet = datetime.datetime.strptime(resultado["created_at"], '%a %b %d %H:%M:%S +0000 %Y') + timedelta(hours=1)
                # Selecciona la hora del tweet
                horaTweet = int(datetime.datetime.strftime(fechaTweet, "%H"))

                # Incrementa en uno los tweets hallados en esa hora
                num[horaTweet] += 1
            
    streamFun(num)

    return num

def oauth_login():
    global access_token
    global api

    auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)
    #twitter_api = twitter.Twitter(auth=access_token) tenias esto puesto pero da error
    twitter_api = twitter.Twitter(auth=auth)
    return twitter_api

def friendlist(tw):
    user = tw.account.verify_credentials()

    query = tw.friends.ids(screen_name = user['screen_name'])
    twetts = []

    print "----------------\n\nObteniendo tweets de los amigos..."
    numAmigo = 1

    for e in query['ids']:
        print ("Amigo: " + str(numAmigo) + "/" + str(len(query['ids'])))
        numAmigo += 1
        twetts.append(tw.statuses.user_timeline(user_id = e, count = 100))
    print "Tweets obtenidos\n"

    
    return numTweets(twetts)


def friends():
    num = friendlist(oauth_login())

    return render_template('stadis.html')



"""   WEB   """

def login1():
    global consumer
    global request_token
    
    request_token_url='https://api.twitter.com/oauth/request_token'
    authorize_url='https://api.twitter.com/oauth/authorize'

    consumer=oauth2.Consumer(CONSUMER_KEY,CONSUMER_SECRET)
    client=oauth2.Client(consumer)
    resp, content = client.request(request_token_url, "GET")

    if resp['status'] != '200':
        raise Exception("Invalid response %s." % resp['status'])

    request_token = dict(urlparse.parse_qsl(content))
    url = "%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'])

    return render_template('twitter.html', url=url)


def login2(pin):
    global consumer
    global request_token
    global OAUTH_TOKEN
    global OAUTH_TOKEN_SECRET
    global access_token

    access_token_url='https://api.twitter.com/oauth/access_token'

    token = oauth2.Token(request_token['oauth_token'],request_token['oauth_token_secret'])
     
    token.set_verifier(pin)
    client = oauth2.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urlparse.parse_qsl(content))

    OAUTH_TOKEN = access_token["oauth_token"]
    OAUTH_TOKEN_SECRET = access_token["oauth_token_secret"]

    return friends()

cargarFichero()

app = Flask(__name__)
GoogleMaps(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/twitter/')
def twitter_function():
    return login1()

@app.route('/twitter/pin/', methods=['POST'])
def twitterpin():
    return login2(request.form['pin'])

if __name__ == "__main__":
    if len(sys.argv) == 1:
        app.run(port=5001,debug=True, host="localhost")
    else:
        app.run(port=5001,debug=True, host=sys.argv[1])

