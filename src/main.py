import requests
from bs4 import BeautifulSoup
import urllib3
import sqlite3
from tqdm import tqdm
import time
import logging
from keep_alive import keep_alive, update_progress, add_log_message
import os

# Disable warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging to print to the console and add messages to the web log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_path='video_data.db'):
        self.db_path = db_path
        self.conn, self.cursor = self.setup_database()

    def setup_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_url TEXT UNIQUE,
                    poster_url TEXT,
                    title TEXT,
                    views TEXT,
                    tags TEXT
                )
            ''')
            conn.commit()
            return conn, cursor
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            if conn:
                conn.close()
            raise

    def save_to_database(self, video_data):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO videos (video_url, poster_url, title, views, tags)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                video_data.get('video_url'),
                video_data.get('poster_url'),
                video_data.get('title'),
                video_data.get('views'),
                ', '.join(video_data.get('tags', []))
            ))
            logging.info(f"Inserted video data into SQLite: {video_data['title']}")
            add_log_message(f"Inserted video: {video_data['title']}")
        except sqlite3.Error as e:
            logging.error(f"Failed to insert data into SQLite: {e}")

    def commit(self):
        try:
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to commit transaction: {e}")

    def close(self):
        if self.conn:
            self.conn.close()

class VideoScraper:
    def __init__(self, start_url, db_manager):
        self.start_url = start_url
        self.db_manager = db_manager

    def fetch_page(self, url, retries=3, backoff_factor=0.3):
        for i in range(retries):
            try:
                response = requests.get(url, verify=False)
                response.raise_for_status()  # Check for request errors
                return response.content
            except requests.RequestException as e:
                if i < retries - 1:
                    sleep_time = backoff_factor * (2 ** i)
                    logging.warning(f"Network error: {e}. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logging.error(f"Failed to fetch {url} after {retries} attempts. Error: {e}")
                    raise

    def scrape_all_pages(self):
        current_url = self.start_url
        vid_page_links = []

        while current_url:
            logging.info(f"Scraping: {current_url}")
            add_log_message(f"Scraping: {current_url}")
            page_content = self.fetch_page(current_url)
            soup = BeautifulSoup(page_content, 'html.parser')

            # Extract video links
            videos_list_div = soup.find('div', class_='videos-list')
            if videos_list_div:
                a_tags = videos_list_div.find_all('a')
                hrefs = [a['href'] for a in a_tags if 'href' in a.attrs]
                vid_page_links.extend(hrefs)
            else:
                logging.info("No 'videos-list' div found on this page.")
                add_log_message("No 'videos-list' div found on this page.")

            # Get the next page URL
            next_page = soup.find('a', text='Next')
            if next_page and 'href' in next_page.attrs:
                current_url = next_page['href']
            else:
                break

        return vid_page_links

    def scrape_video_data_from_links(self, vid_page_links):
        data_list = []

        for i, link in enumerate(tqdm(vid_page_links, desc="Scraping video data"), 1):
            try:
                logging.info(f"Scraping video data from: {link}")
                add_log_message(f"Scraping video data from: {link}")
                page_content = self.fetch_page(link)
                video_data = self.extract_video_data(page_content)
                self.db_manager.save_to_database(video_data)
                data_list.append(video_data)

                # Update progress on the web page
                progress_value = int((i / len(vid_page_links)) * 100)
                update_progress(progress_value)
            except requests.RequestException as e:
                logging.error(f"Failed to scrape {link}: {e}")
                add_log_message(f"Failed to scrape {link}: {e}")

        return data_list

    def extract_video_data(self, page_content):
        soup = BeautifulSoup(page_content, 'html.parser')
        video_data = {}

        video_tag = soup.find('video')
        if video_tag and video_tag.find('source'):
            video_data['video_url'] = video_tag.find('source')['src']

        if video_tag and 'poster' in video_tag.attrs:
            video_data['poster_url'] = video_tag['poster']

        title_views_div = soup.find('div', class_='title-views')
        if title_views_div:
            video_data['title'] = title_views_div.find('h1').text.strip()
            views_span = title_views_div.find('span', class_='views')
            if views_span:
                video_data['views'] = views_span.text.strip()

        tags_div = soup.find('div', class_='tags-list')
        if tags_div:
            tags = [tag.text.strip() for tag in tags_div.find_all('a', class_='label')]
            video_data['tags'] = tags

        return video_data

    def run(self):
        video_links = self.scrape_all_pages()
        logging.info("Collected video links:")
        add_log_message("Collected video links")
        for link in video_links:
            logging.info(link)
            add_log_message(link)

        try:
            video_data_list = self.scrape_video_data_from_links(video_links)
            self.db_manager.commit()

            # Save scraped data to a CSV file
            file_name = "scraped_data.csv"
            with open(file_name, 'w') as f:
                for video in video_data_list:
                    f.write(f"{video['title']}, {video['views']}, {video['video_url']}\n")

            logging.info(f"Saved scraped data to {file_name}")
            add_log_message(f"Saved scraped data to {file_name}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            add_log_message(f"An error occurred: {e}")
        finally:
            self.db_manager.close()

# Start the keep-alive server
keep_alive()

# Start the scraper
if __name__ == "__main__":
    db_manager = DatabaseManager()
    scraper = VideoScraper('https://www.camcam.cc/page/1', db_manager)
    scraper.run()
