
import os
import sys
from contextlib import asynccontextmanager

import datetime

from app.qbittorrent import QBittorrentClient
from app.rss_parser import get_anime_name
import feedparser
from app.scheduler import start_scheduler, check_rss_feeds, reschedule_job
from app.database import get_db, RSSFeed, RSSHistory, Settings, check_and_migrate_db
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Depends, Form

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_and_migrate_db()
    db = next(get_db())
    settings = db.query(Settings).first()
    if settings:
        start_scheduler(settings.rss_refresh_interval)
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=resource_path("app/static")), name="static")
templates = Jinja2Templates(directory=resource_path("app/templates"))

def format_datetime_local(dt: datetime.datetime):
    if dt is None:
        return "N/A"
    utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
    local_tz = datetime.timezone(datetime.timedelta(hours=3))
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt.strftime('%Y-%m-%d %H:%M')

templates.env.filters['local_time'] = format_datetime_local

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    feeds = db.query(RSSFeed).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"feeds": feeds}
    )

@app.post("/add_feed", response_class=RedirectResponse)
async def add_feed(url: str = Form(...), keyword_filter: str = Form(None), qbit_category: str = Form(None), db: Session = Depends(get_db)):
    parsed_feed = feedparser.parse(url)
    if parsed_feed.entries:
        title = get_anime_name(parsed_feed.entries[0].title)
    else:
        title = parsed_feed.feed.title
    feed = RSSFeed(url=url, title=title, keyword_filter=keyword_filter, qbit_category=qbit_category)
    db.add(feed)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete_feed/{feed_id}", response_class=RedirectResponse)
async def delete_feed(feed_id: int, db: Session = Depends(get_db)):
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    db.delete(feed)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/history/{feed_id}", response_class=HTMLResponse)
async def read_history(request: Request, feed_id: int, db: Session = Depends(get_db)):
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    history = db.query(RSSHistory).filter(RSSHistory.feed_id == feed_id).all()
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"feed": feed, "history": history}
    )


@app.get("/settings", response_class=HTMLResponse)
async def read_settings(request: Request, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"settings": settings}
    )

@app.post("/settings", response_class=RedirectResponse)
async def update_settings(qbit_url: str = Form(...), qbit_username: str = Form(...), qbit_password: str = Form(...), rss_refresh_interval: int = Form(...), user_agent: str = Form(...), db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
    settings.qbit_url = qbit_url
    settings.qbit_username = qbit_username
    settings.qbit_password = qbit_password
    settings.rss_refresh_interval = rss_refresh_interval
    settings.user_agent = user_agent
    db.commit()
    reschedule_job(rss_refresh_interval)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/refresh_feed/{feed_id}", response_class=RedirectResponse)
async def refresh_feed(feed_id: int, db: Session = Depends(get_db)):
    await check_rss_feeds(feed_id=feed_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/refresh_all", response_class=RedirectResponse)
async def refresh_all(db: Session = Depends(get_db)):
    await check_rss_feeds()
    return RedirectResponse(url="/", status_code=303)

@app.post("/download_torrent/{history_id}", response_class=RedirectResponse)
async def download_torrent(history_id: int, db: Session = Depends(get_db)):
    history_item = db.query(RSSHistory).filter(RSSHistory.id == history_id).first()
    feed = db.query(RSSFeed).filter(RSSFeed.id == history_item.feed_id).first()
    settings = db.query(Settings).first()

    parsed_feed = feedparser.parse(feed.url, agent=settings.user_agent)
    for item in parsed_feed.entries:
        if item.guid == history_item.guid:
            qbit_client = QBittorrentClient(settings.qbit_url, settings.qbit_username, settings.qbit_password)
            await qbit_client.add_torrent(item.enclosures[0].href, feed.qbit_category)
            history_item.downloaded = True
            db.commit()
            break

    return RedirectResponse(url=f"/history/{feed.id}", status_code=303)
