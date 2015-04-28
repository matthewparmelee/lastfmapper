#################################
# Matthew Parmelee
# March 2015
# last.fm tag comparator
#################################

from lastfm import LastFM
import json
import os.path
import copy
import time

DEBUG_OUTPUT         = True                  # allow debug output
SMALL_OUTPUT         = True                  # leave no-relation results out, to reduce filesize
COMPARE_ARTISTS      = True                 # compare artists in addition to tags
DATASET_FILENAME     = "tag_data.json"       # the filepath for the dataset
TAG_LIST_FILENAME    = "tag_list.json"       # the filepath for the tag list
ARTIST_LIST_FILENAME = "artist_list.json"    # the filepath for the tag list
TAGS_FILENAME        = "tag_results.json"    # the filepath of the final results
ARTISTS_FILENAME     = "artist_results.json" # the filepath of the final results
DATASET_SIZE         = 1000                  # the size of dataset to acquire
SIMILARITY_THRESHOLD = 100                   # distance at which two tags have "no similarity"
TAG_LIST             = set()                 # the global tag list used throughout
ARTIST_LIST          = set()                 # the global artist list used throughout

# helper function for pretty-printing graphs
# @return list
def set_default(obj):
    # json can't serialize sets
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

# helper function for debug output
# @param str - the string to be conditionally printed
def debug_print(str):
  if DEBUG_OUTPUT is True:
    print str

# get the master dataset
# @return dataset
def get_dataset():
  debug_print("Obtaining dataset...")
  # save time by loading any existing dataset
  if os.path.isfile(DATASET_FILENAME):
    dataset = json.load(open(DATASET_FILENAME))
    if len(dataset) == DATASET_SIZE:
      debug_print("Existing dataset found!")
      return dataset

  dataset = {}
  artists = set()

  # initialize LastFM API object and get artist list
  lastreq  = LastFM()
  response = lastreq.get_artists(DATASET_SIZE)

  # initialize all artist tag sets
  for artist in response["artists"]["artist"]:
    dataset[artist["name"]] = set()

  # get tags for each artist
  count = 1
  for artist in dataset.keys():
    debug_print("Acquiring tags for artist " + str(count) + " of " + str(DATASET_SIZE))
    response = lastreq.get_toptags(artist)
    for tag in response["toptags"]["tag"]:
      dataset[artist].add(tag["name"])
    count += 1

  # save the dataset, because it probably took a while to get
  debug_print("Dataset complete. Saving...")
  json.dump(dataset, open(DATASET_FILENAME, 'wb'), default=set_default)

  return dataset

# generate a tag/artist graph
# @param dataset - the parsed full dataset
# @return graph
def get_graph(dataset):
  debug_print("Building graph from dataset...")
  global TAG_LIST
  graph   = {}

  # build graph and master tag list
  for artist, artist_tags in dataset.iteritems():
    ARTIST_LIST.add(artist)
    tags = set(artist_tags)
    graph[artist] = tags

    for tag in artist_tags:
      TAG_LIST.add(tag)
      if tag not in graph:
        graph[tag] = set()
      graph[tag].add(artist)

  return graph

# calculate tag similarity
# @param graph   - an adjacency list of artist and tag nodes
# @return result - a dictionary of tags and their relational values to other tags
def compare_tags(graph, artists=False):
  debug_print("Starting comparison routine...")
  result = {}

  master_list = TAG_LIST
  if artists:
    master_list = ARTIST_LIST
  
  # initialize tag dicts
  for tag in master_list:
    result[tag] = {}

  count = 1
  total = pow(len(master_list), 2)
  for tag1 in master_list:
    for tag2 in master_list:
      debug_print("Getting paths for group " + str(count) + " of " + str(total))

      if tag2 in result[tag1]:
        count += 1
        continue
      if tag1 == tag2:
        count += 1
        result[tag1][tag2] = 1
        continue

      # find all paths between two given tags
      paths = list(dfs_paths(graph, tag1, tag2))

      # score paths by length
      scores = []
      for path in paths:
        if len(path) <= SIMILARITY_THRESHOLD:
          scores.append(len(path))

      # if there is any relation, calculate the average of all path lengths
      if len(scores) > 0:
        average = sum(scores) / float(len(scores))
        result[tag1][tag2] = average
        result[tag2][tag1] = average
      else:
        result[tag1][tag2] = 0
        result[tag2][tag1] = 0

      count += 1

  return result

# use depth-first to return all paths
# @param graph - a graph of nodes
# @param start - the starting node
# @param goal  - the ending node
# @yield generator of paths
def dfs_paths(graph, start, goal):
    stack = [(start, [start])]
    while stack and len(stack) <= SIMILARITY_THRESHOLD:
        (vertex, path) = stack.pop()
        for next in graph[vertex] - set(path):
            if next == goal:
                yield path + [next]
            else:
                stack.append((next, path + [next]))

# normalize scored dataset
# @param data - the scored dataset to normalize
# @return normalized scored dataset
def normalize_scores(data):
  debug_print("Normalizing scores...")
  normalized_data = copy.deepcopy(data)

  # minimum observed score
  minimum = False

  # maximum observed score
  maximum = False

  # find the minimum and maximum scores for normalization
  for tag1, tags in data.iteritems():
    for tag2 in tags:
      score = data[tag1][tag2]
      if score is 0:
        continue
      elif minimum is False or score < minimum:
        minimum = score
      elif maximum is False or score > maximum:
        maximum = score

  # adjust scores relative to the max and min
  for tag1, tags in data.iteritems():
    for tag2 in tags:
      score    = data[tag1][tag2]
      if score is 0:
        normalized_data[tag1][tag2] = score
      else:
        # normalization function
        newscore = (score - minimum) / (maximum - minimum)

        # invert scores for less-confusing output
        # we measured 'difference', but output should be 'similarity'
        normalized_data[tag1][tag2] = 1 - newscore

  # if enabled, remove unrelated tag data to lower result filesize
  if SMALL_OUTPUT is True:
    for tag1, tags in data.iteritems():
      for tag2 in tags:
        if data[tag1][tag2] is 0:
          normalized_data[tag1].pop(tag2, None)

  return normalized_data

# main execution
if __name__ == "__main__":
  # start debug timer
  start = time.clock()

  # obtain the dataset
  dataset = get_dataset()

  # create a traversable graph from the dataset
  graph = get_graph(dataset)

  # use pathfinding to assess tag similarity
  result = compare_tags(graph)

  # normalize the scored result
  normalized_result = normalize_scores(result)

  # save the output
  debug_print("Saving results to " + TAGS_FILENAME)
  json.dump(normalized_result, open(TAGS_FILENAME, 'wb'), sort_keys=True, indent=4, default=set_default)

  # save intermediary data
  json.dump(TAG_LIST, open(TAG_LIST_FILENAME, 'wb'), sort_keys=True, indent=4, default=set_default)

  # optionally run the comparator again for artist comparisons
  if COMPARE_ARTISTS:
    # use pathfinding to assess tag similarity
    result = compare_tags(graph, True)

    # normalize the scored result
    normalized_result = normalize_scores(result)

    # save the output
    debug_print("Saving results to " + ARTISTS_FILENAME)
    json.dump(normalized_result, open(ARTISTS_FILENAME, 'wb'), sort_keys=True, indent=4, default=set_default)

    # save intermediary data
    json.dump(ARTIST_LIST, open(ARTIST_LIST_FILENAME, 'wb'), sort_keys=True, indent=4, default=set_default)  

  # end debug timer
  end = time.clock()
  debug_print("Finished in " + str(end - start) + " seconds.")