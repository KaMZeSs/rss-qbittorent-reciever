
import os
import sys
import shutil
from contextlib import asynccontextmanager

import datetime

from app.qbittorrent import QBittorrentClient
from app.rss_parser import get_anime_name
import feedparser
from app.scheduler import start_scheduler, check_rss_feeds, reschedule_job
from app.database import get_db, RSSFeed, RSSHistory, Settings, check_and_migrate_db, sanitize_filename
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
async def add_feed(url: str = Form(...), keyword_filter: str = Form(None), download_path: str = Form(None), db: Session = Depends(get_db)):
    parsed_feed = feedparser.parse(url)
    if parsed_feed.entries:
        title = get_anime_name(parsed_feed.entries[0].title)
    else:
        title = parsed_feed.feed.title
    feed = RSSFeed(url=url, title=title, keyword_filter=keyword_filter, download_path=download_path)
    db.add(feed)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete_feed/{feed_id}", response_class=RedirectResponse)
async def delete_feed(feed_id: int, db: Session = Depends(get_db)):
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    db.delete(feed)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/edit_feed/{feed_id}", response_class=HTMLResponse)
async def edit_feed_page(request: Request, feed_id: int, db: Session = Depends(get_db)):
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="edit_feed.html",
        context={"feed": feed}
    )

@app.post("/edit_feed/{feed_id}", response_class=RedirectResponse)
async def edit_feed(feed_id: int, title: str = Form(...), url: str = Form(...), keyword_filter: str = Form(None), download_path: str = Form(None), db: Session = Depends(get_db)):
    feed = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    if not feed:
        return RedirectResponse(url="/", status_code=303)
    
    old_download_path = feed.download_path
    old_title = feed.title
    new_title = title
    new_download_path = download_path
    
    # Sanitize new title for filesystem
    sanitized_new_title = sanitize_filename(new_title)
    sanitized_old_title = sanitize_filename(old_title)
    
    try:
        # If download_path changed, move the folder
        if old_download_path != new_download_path and new_download_path:
            old_full_path = os.path.join(old_download_path, sanitized_old_title)
            new_full_path = os.path.join(new_download_path, sanitized_new_title)
            
            if os.path.exists(old_full_path):
                # Create new parent directory if it doesn't exist
                os.makedirs(new_download_path, exist_ok=True)
                # Move the folder
                shutil.move(old_full_path, new_full_path)
                print(f"Moved folder from {old_full_path} to {new_full_path}")
            else:
                print(f"Old folder not found: {old_full_path}")
        
        # If title changed (but download_path same), rename the folder
        elif old_title != new_title and new_download_path:
            old_full_path = os.path.join(new_download_path, sanitized_old_title)
            new_full_path = os.path.join(new_download_path, sanitized_new_title)
            
            if os.path.exists(old_full_path):
                os.rename(old_full_path, new_full_path)
                print(f"Renamed folder from {old_full_path} to {new_full_path}")
            else:
                print(f"Folder not found for rename: {old_full_path}")
        
        # If both path and title changed, the first condition handles it (move with new name)
        
        # Update database
        feed.title = new_title
        feed.url = url
        feed.keyword_filter = keyword_filter
        feed.download_path = new_download_path
        db.commit()
        
    except Exception as e:
        print(f"Failed to move/rename folder: {e}")
        db.rollback()
        # Return error - could redirect with error message
        return RedirectResponse(url=f"/edit_feed/{feed_id}?error=move_failed", status_code=303)
    
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
            # Sanitize title for filename
            sanitized_title = sanitize_filename(item.title)
            # Use download_path as save_path, and .downloading subfolder as download_path
            save_path = feed.download_path
            download_path = f"{feed.download_path}\\.downloading" if feed.download_path else None
            await qbit_client.add_torrent(
                item.enclosures[0].href,
                save_path=save_path,
                download_path=download_path,
                rename=sanitized_title
            )
            history_item.downloaded = True
            db.commit()
            break

    return RedirectResponse(url=f"/history/{feed.id}", status_code=303)
