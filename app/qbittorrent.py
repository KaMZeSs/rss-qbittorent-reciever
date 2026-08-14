
import httpx
from qbittorrentapi import Client

class QBittorrentClient:
    def __init__(self, url, username, password):
        self.client = Client(host=url, username=username, password=password)
        self.client.auth_log_in()

    async def add_torrent(self, torrent_url, save_path=None, download_path=None, rename=None):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(torrent_url)
                response.raise_for_status()
                torrent_content = response.content
                self.client.torrents_add(
                    torrent_files=torrent_content,
                    save_path=save_path,
                    download_path=download_path,
                    rename=rename,
                    use_download_path=True if download_path else False
                )
        except httpx.RequestError as e:
            print(f"Failed to download torrent file: {e}")

    async def move_torrents(self, old_path: str, new_path: str):
        """Move torrents from old_path to new_path in qBittorrent"""
        try:
            # Get all torrents
            torrents = self.client.torrents_info()
            
            # Filter torrents that are in the old path
            torrent_hashes = []
            for torrent in torrents:
                # Check if torrent's save_path starts with old_path
                torrent_save_path = torrent.save_path
                if torrent_save_path and torrent_save_path.startswith(old_path):
                    torrent_hashes.append(torrent.hash)
            
            if torrent_hashes:
                # Move torrents to new location
                # Calculate the relative path from old_path and append to new_path
                for torrent_hash in torrent_hashes:
                    torrent = self.client.torrents_info(torrent_hashes=[torrent_hash])[0]
                    old_save_path = torrent.save_path
                    # Get relative path from old_path
                    if old_save_path.startswith(old_path):
                        relative_path = old_save_path[len(old_path):].lstrip('\\/')
                        new_save_path = f"{new_path}\\{relative_path}" if relative_path else new_path
                        self.client.torrents_set_location(torrent_hashes=[torrent_hash], location=new_save_path)
                        print(f"Moved torrent {torrent.name} from {old_save_path} to {new_save_path}")
        except Exception as e:
            print(f"Failed to move torrents: {e}")
