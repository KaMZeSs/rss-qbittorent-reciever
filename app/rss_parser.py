
import feedparser

def parse_rss(feed_url, user_agent):
    return feedparser.parse(feed_url, agent=user_agent)

def get_anime_name(title):
    return title.split('|')[0].strip()
