# Tweet Graph Skill

Store and retrieve tweets in a Neo4j graph database with automatic entity extraction.

## Purpose

This skill enables storing tweets (from URLs or manual entry) in a graph database, automatically extracting entities (hashtags, mentions, URLs), and retrieving related tweets using vector similarity and graph traversal.

## Setup

Set the following environment variables:
- `TWEET_GRAPH_API_URL` - URL of the Tweet Graph API (default: http://tweet-graph-api:8000)

## Usage

### Store a Tweet

From a URL:
```
store this tweet: https://twitter.com/user/status/123456789
```

Manual entry:
```
store tweet:
id: manual-001
text: "This is a manually stored tweet #example @user"
author: myuser
```

### Search Tweets

```
find tweets about: machine learning
search for tweets about: artificial intelligence
```

### Get Related Tweets

```
show related to tweet: 123456789
what's connected to: abc123
```

### Statistics

```
tweet graph stats
```

## Examples

**User:** Store this tweet: https://twitter.com/elonmusk/status/123456

**Assistant:** ✅ Tweet stored successfully!
- Author: @elonmusk
- Hashtags: #SpaceX, #Mars
- Mentions: @NASA
- Relationships: 5 nodes connected

**User:** Find tweets about Mars colonization

**Assistant:** Found 12 related tweets:

1. [Score: 0.92] "Mars colonization will require..." by @SpaceXFan
2. [Score: 0.87] "The path to Mars goes through..." by @ElonMusk
...

## Installation

Copy this skill directory to your OpenClaw skills folder and restart OpenClaw.
