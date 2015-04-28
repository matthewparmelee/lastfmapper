#################################
# Matthew Parmelee
# March 2015
# last.fm API class
#################################

import json
import requests

class LastFM:
  # initialize API access credentials
  def __init__(self):
    self.API_URL = "http://ws.audioscrobbler.com/2.0/"
    self.API_KEY = "db7b8b21ac8e3c20fcc5321bf53f9c4e"

  # base function for all API methods
  # @param method - the API action being called
  # @param args   - the list of method parameters
  # @return json reponse
  def api_call(self, method, args):
    payload = { "method" : method, "api_key" : self.API_KEY, "format" : "json" }

    for key, value in args.iteritems():
      payload[key] = value

    response = requests.get(self.API_URL, params=payload)
    return response.json()

  # get a list of top artists
  # @param count - the number of top artists to return
  # @return json response
  def get_artists(self, count):
    method = "chart.gettopartists"
    args   = {"limit" : count}
    return self.api_call(method, args)

  # get a list of top tags for a given artist
  # @param artist - the artist to obtain tags for
  # @return json response
  def get_toptags(self, artist):
    method = "artist.gettoptags"
    args   = {"artist" : artist}
    return self.api_call(method, args)
