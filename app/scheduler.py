
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal, RSSFeed, RSSHistory, Settings
from app.rss_parser import parse_rss, get_anime_name
from app.qbittorrent import QBittorrentClient

scheduler = BackgroundScheduler()
JOB_ID = "rss_check"

async def check_rss_feeds():
    db = SessionLocal()
    settings = db.query(Settings).first()
    if not settings:
        db.close()
        return

    qbit_client = QBittorrentClient(settings.qbit_url, settings.qbit_username, settings.qbit_password)
    feeds = db.query(RSSFeed).all()

    for feed in feeds:
        parsed_feed = parse_rss(feed.url, settings.user_agent)
        for item in parsed_feed.entries:
            history_item = db.query(RSSHistory).filter_by(guid=item.guid).first()
            if not history_item:
                anime_name = get_anime_name(item.title)
                new_history_item = RSSHistory(feed_id=feed.id, guid=item.guid, title=item.title)
                if feed.keyword_filter and feed.keyword_filter.lower() in item.title.lower():
                    await qbit_client.add_torrent(item.enclosures[0].href, feed.qbit_category)
                    new_history_item.downloaded = True
                db.add(new_history_item)
    db.commit()
    db.close()

def start_scheduler(rss_refresh_interval):
    if not scheduler.running:
        scheduler.add_job(check_rss_feeds, 'interval', minutes=rss_refresh_interval, id=JOB_ID)
        scheduler.start()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()

def reschedule_job(rss_refresh_interval):
    if scheduler.running:
        scheduler.reschedule_job(JOB_ID, trigger='interval', minutes=rss_refresh_interval)
