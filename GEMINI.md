# MalgeunTube (맑은튜브)

**MalgeunTube** is a web-based application designed to provide an ad-free YouTube viewing experience. It leverages `yt-dlp` to fetch video streams and metadata, presenting them in a clean, user-friendly interface built with **Flask**. The project emphasizes privacy and simplicity by storing user data (history, subscriptions, playlists) locally in JSON files.

## Project Overview

*   **Core Functionality:** Ad-free video playback, playlist management, channel subscriptions, video recommendations, and playback history.
*   **Architecture:**
    *   **Backend:** Python (Flask) handles routing, data management (JSON), and interactions with YouTube via `yt-dlp`.
    *   **Frontend:** HTML5, CSS3, and JavaScript provide a responsive UI with custom video controls and gestures.
    *   **Data Persistence:** Local JSON files (`data/*.json`) are used instead of a traditional database.

## Key Files & Directories

*   `app.py`: The main application entry point. Contains all Flask routes, API endpoints, and data management logic.
*   `requirements.txt`: Lists Python dependencies (Flask, yt-dlp, Werkzeug).
*   `templates/`: Contains Jinja2 HTML templates for various pages (e.g., `index.html`, `watch.html`, `search.html`).
*   `static/`: Stores static assets like CSS stylesheets (`css/style.css`) and JavaScript files (`js/main.js`).
*   `data/`: Directory for local data storage (`history.json`, `channels.json`, `playlists.json`).
*   `setup.bat` / `run.bat`: Windows batch scripts for easy setup and execution.

## Building and Running

### Windows

1.  **Setup:** Run the setup script to create a virtual environment and install dependencies.
    ```batch
    setup.bat
    ```
2.  **Run:** Start the application.
    ```batch
    run.bat
    ```
    The server will start at `http://localhost:5000`.

### Linux / macOS

1.  **Setup:** Create a virtual environment and install dependencies.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Run:** Start the application.
    ```bash
    python app.py
    ```

## Development Conventions

*   **Dependency Management:** Python dependencies are managed via `pip`. Ensure `requirements.txt` is updated if new packages are added.
*   **Data Handling:** All user data is stored in `data/`. Functions like `load_json` and `save_json` in `app.py` handle file I/O.
*   **Frontend:** The UI is server-side rendered using Jinja2 templates. Client-side interactivity is handled by `static/js/main.js`.
*   **YouTube Integration:** `yt_dlp` is used for all YouTube interactions (searching, fetching metadata, extracting video URLs).
*   **Environment:** A virtual environment (`venv`) is recommended for development to isolate dependencies.
