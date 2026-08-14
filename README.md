# RSS qBittorrent Autodownloader

This project automatically downloads torrents from RSS feeds and integrates with qBittorrent via its Web API.

## Requirements

* Windows
* Python 3.12+
* [uv](https://docs.astral.sh/uv/)
* qBittorrent with Web UI enabled (tested on v5.1.4)

## Installation

1. Clone the repository.

2. Install [uv](https://docs.astral.sh/uv/) if it is not already installed.

3. Install the project dependencies:

   ```bash
   uv sync
   ```

   `uv` will automatically create the virtual environment and install the required dependencies.

## Running the application

Run the FastAPI application:

```bash
uv run uvicorn app.main:app --reload
```

The application will be available at:

```text
http://127.0.0.1:8000
```

The Python version used by the project is specified in `.python-version`.

## Configuration

1. Open the **Settings** page in the web UI.
2. Enter your qBittorrent connection details:

   * URL
   * Username
   * Password
3. Set the RSS refresh interval and a custom User-Agent.
4. Save the settings.

## Usage

1. Open the **Home** page.
2. Add a new RSS feed by providing:

   * RSS feed URL
   * Optional keyword filter
   * qBittorrent category
3. The application will periodically fetch the RSS feed and download new torrents that match the keyword filter.
4. View the history of parsed torrents for each feed using the **History** button.
5. Manually trigger a feed refresh using the **Refresh** button.

## Running on Startup (Windows)

To run the application automatically when you log in to Windows, you can place a shortcut to the executable in the Windows Startup folder.

1. Navigate to the `dist` folder in the project directory.

2. Right-click `rss-downloader.exe` and select **Create shortcut**.

3. Press `Win + R` to open the Run dialog.

4. Enter:

   ```text
   shell:startup
   ```

5. Press Enter to open the Startup folder.

6. Move the created shortcut into the Startup folder.

The application will then start automatically when you log in to Windows.

The application runs on port `21632` when started using the packaged executable.

## Development

Install or update dependencies:

```bash
uv sync
```

Run the development server with automatic reload:

```bash
uv run uvicorn app.main:app --reload
```

Add a new dependency:

```bash
uv add <package>
```

Update dependencies:

```bash
uv lock --upgrade
uv sync
```

The `uv.lock` file is committed to the repository to ensure reproducible dependency versions.
