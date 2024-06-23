import wx
import requests
import os
import json
from PIL import Image, ImageFilter, UnidentifiedImageError
from io import BytesIO

CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


class MovieApp(wx.Frame):
    def __init__(self, parent, title):
        super(MovieApp, self).__init__(parent, title=title, size=(800, 600))

        panel = wx.Panel(self)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        vbox_left = wx.BoxSizer(wx.VERTICAL)

        self.movie_name_input = wx.TextCtrl(panel)
        vbox_left.Add(self.movie_name_input, flag=wx.EXPAND | wx.ALL, border=10)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        search_button = wx.Button(panel, label='Search')
        search_button.Bind(wx.EVT_BUTTON, self.on_search)
        hbox1.Add(search_button, flag=wx.RIGHT, border=5)

        close_button = wx.Button(panel, label='Close')
        close_button.Bind(wx.EVT_BUTTON, self.on_close)
        hbox1.Add(close_button)

        vbox_left.Add(hbox1, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.movie_info = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        vbox_left.Add(self.movie_info, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        vbox_right = wx.BoxSizer(wx.VERTICAL)

        self.image_ctrl = wx.StaticBitmap(panel)
        vbox_right.Add(self.image_ctrl, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=10)

        hbox.Add(vbox_left, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        hbox.Add(vbox_right, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        panel.SetSizer(hbox)
        self.Centre()
        self.Show(True)

        # super(MovieApp, self).__init__(parent, title=title, size=(800, 600))
        #
        # panel = wx.Panel(self)
        # vbox = wx.BoxSizer(wx.VERTICAL)
        #
        # self.movie_name_input = wx.TextCtrl(panel)
        # vbox.Add(self.movie_name_input, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=10)
        #
        # hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        # search_button = wx.Button(panel, label='Search')
        # search_button.Bind(wx.EVT_BUTTON, self.on_search)
        # hbox1.Add(search_button)
        #
        # close_button = wx.Button(panel, label='Close')
        # close_button.Bind(wx.EVT_BUTTON, self.on_close)
        # hbox1.Add(close_button, flag=wx.LEFT, border=5)
        #
        # vbox.Add(hbox1, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)
        #
        # self.movie_info = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        # vbox.Add(self.movie_info, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)
        #
        # self.image_ctrl = wx.StaticBitmap(panel)
        # vbox.Add(self.image_ctrl, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)
        #
        # panel.SetSizer(vbox)
        # self.Centre()
        # self.Show(True)

    def on_search(self, event):
        movie_name = self.movie_name_input.GetValue().strip()
        if movie_name:
            movie_info, image_path = self.get_movie_info(movie_name)
            self.movie_info.SetValue(movie_info)
            if image_path:
                img = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
                self.image_ctrl.SetBitmap(wx.Bitmap(img))
                self.image_ctrl.Refresh()

    def on_close(self, event):
        self.Close(True)

    def get_movie_info(self, movie_name):
        movie_info = self.get_cached_info(movie_name)
        if movie_info:
            return movie_info['text'], movie_info['image_path']

        text, image_url = self.fetch_movie_info(movie_name)
        if text and image_url:
            image_path = self.download_and_process_image(image_url, movie_name)
            self.cache_info(movie_name, text, image_path)
            return text, image_path
        return "", None

    def get_cached_info(self, movie_name):
        cache_file = os.path.join(CACHE_DIR, f"{movie_name}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def cache_info(self, movie_name, text, image_path):
        cache_file = os.path.join(CACHE_DIR, f"{movie_name}.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'text': text, 'image_path': image_path}, f)

    def fetch_movie_info(self, movie_name):
        query_url = f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro=&explaintext=&titles={movie_name}"
        response = requests.get(query_url).json()

        pages = response.get('query', {}).get('pages', {})
        if not pages:
            return "", None

        page = next(iter(pages.values()))
        if 'extract' not in page:
            return "", None
        text = page['extract']

        image_url = self.get_image_url_from_wikipedia(movie_name)

        return text, image_url

    def get_image_url_from_wikipedia(self, movie_name):
        image_query_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=images&titles={movie_name}"
        image_response = requests.get(image_query_url).json()

        pages = image_response.get('query', {}).get('pages', {})
        if not pages:
            return None

        page = next(iter(pages.values()))
        images = page.get('images', [])

        poster_file_name = None
        for image in images:
            image_title = image['title'].replace("File:", "")
            if 'poster' in image_title.lower():
                poster_file_name = image_title
                break

        if poster_file_name == None:
            for image in images:
                image_title = image['title'].replace("File:", "")
                if 'logo' in image_title.lower():
                    poster_file_name = image_title
                    break

        if not poster_file_name:
            return None

        image_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=allimages&format=json&aifrom={poster_file_name}"
        image_search_response = requests.get(image_search_url).json()

        allimages = image_search_response.get('query', {}).get('allimages', [])
        for image in allimages:
            image_title = image['title'].replace("File:", "")
            if image_title == poster_file_name:
                poster_file_name = image['title']
                break
        image_info = next((img for img in allimages if img['title'] == poster_file_name), None)

        if image_info:
            return image_info['url']
        else:
            return self.get_image_url_from_commons(poster_file_name)

    def get_image_url_from_commons(self, poster_file_name):
        commons_query_url = f"https://commons.wikimedia.org/w/api.php?action=query&list=allimages&format=json&aifrom={poster_file_name}"
        commons_response = requests.get(commons_query_url).json()

        allimages = commons_response.get('query', {}).get('allimages', [])
        image_file_name = None
        for image in allimages:
            image_title = image['title'].replace("File:", "")
            if image_title == poster_file_name:
                image_file_name = image['title']
                break
        image_info = next((img for img in allimages if img['title'] == image_file_name), None)

        if image_info:
            return image_info['url']
        return None

    def download_and_process_image(self, url, movie_name):
        try:
            # Fetch image from URL
            response = requests.get(url)
            response.raise_for_status()  # Ensure the request was successful

            # Check the content type of the response
            content_type = response.headers.get('Content-Type')
            if 'image' not in content_type:
                print(f"URL does not point to an image. Content-Type: {content_type}")
                return None

            # Check the response content length
            content_length = response.headers.get('Content-Length')
            if content_length:
                print(f"Content-Length: {content_length}")

            # Log the first few bytes of the image content
            image_data = response.content[:10]
            print(f"First 10 bytes of the image data: {image_data}")

            # Load the image
            img = Image.open(BytesIO(response.content))

            # Define the kernel for filtering
            kernel = [
                0, 0, 0, 0, 0,
                0, 0, 0, 0, 0,
                0, 0, 1, 0, 0,
                0, 0, 0, 0, 0,
                0, 0, 0, 0, 0
            ]

            # Apply the kernel filter
            img = img.filter(ImageFilter.Kernel((5, 5), kernel, scale=1, offset=0))

            # Save the processed image
            image_path = os.path.join(CACHE_DIR, f"{movie_name}.jpg")
            img.save(image_path)

            return image_path

        except requests.RequestException as e:
            print(f"Error downloading the image: {e}")
            return None
        except (IOError, UnidentifiedImageError) as e:
            print(f"Error processing the image: {e}")
            return None


if __name__ == '__main__':
    app = wx.App(False)
    frame = MovieApp(None, "Movie Info")
    app.MainLoop()
