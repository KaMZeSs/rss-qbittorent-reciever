
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
