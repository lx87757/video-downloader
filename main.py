# main.py - 适配 Android 手机的万能视频下载器
import os
import re
import threading
import requests
import yt_dlp

# Kivy / KivyMD 移动端 UI 框架
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog

# Android 存储路径获取（如果在 Android 环境运行）
try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
    DOWNLOAD_DIR = os.path.join(primary_external_storage_path(), "Download")
except ImportError:
    DOWNLOAD_DIR = os.path.expanduser("~/Downloads")


class VideoDownloaderApp(MDApp):

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # 主布局
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=15)

        # 标题
        title = MDLabel(
            text="万能视频下载器",
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=40,
        )
        layout.add_widget(title)

        subtitle = MDLabel(
            text="支持 抖音 / YouTube / Bilibili / TikTok 等 1000+ 站点",
            font_style="Caption",
            halign="center",
            theme_text_color="Hint",
            size_hint_y=None,
            height=20,
        )
        layout.add_widget(subtitle)

        # 输入框
        self.url_input = MDTextField(
            hint_text="请粘贴视频链接或分享文案...",
            multiline=True,
            size_hint_y=None,
            height=100,
        )
        layout.add_widget(self.url_input)

        # 格式选择按钮
        self.format_mode = "MP4 (最高画质)"
        self.btn_format = MDRaisedButton(
            text=f"下载格式: {self.format_mode}",
            pos_hint={"center_x": 0.5},
            on_release=self.show_format_menu,
        )
        layout.add_widget(self.btn_format)

        # 下载按钮
        self.btn_download = MDRaisedButton(
            text="▶ 开始下载",
            pos_hint={"center_x": 0.5},
            size_hint_x=0.8,
            height=50,
            on_release=self.start_download,
        )
        layout.add_widget(self.btn_download)

        # 进度条与状态
        self.progress = MDProgressBar(value=0, size_hint_y=None, height=10)
        layout.add_widget(self.progress)

        self.status_label = MDLabel(
            text="准备就绪",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=30,
        )
        layout.add_widget(self.status_label)

        # 菜单初始化
        menu_items = [
            {
                "text": "MP4 (最高画质)",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="MP4 (最高画质)": self.set_format(x),
            },
            {
                "text": "仅 MP3 音频",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="仅 MP3 音频": self.set_format(x),
            },
        ]
        self.menu = MDDropdownMenu(
            caller=self.btn_format, items=menu_items, width_mult=4
        )

        return layout

    def show_format_menu(self, instance):
        self.menu.open()

    def set_format(self, text):
        self.format_mode = text
        self.btn_format.text = f"下载格式: {text}"
        self.menu.dismiss()

    def update_status(self, text, value=0):
        self.status_label.text = text
        self.progress.value = value

    def start_download(self, instance):
        raw_input = self.url_input.text.strip()
        url_match = re.search(r"https?://[^\s]+", raw_input)
        if not url_match:
            self.show_alert("错误", "请输入有效的网址！")
            return

        clean_url = url_match.group(0)
        self.btn_download.disabled = True
        self.update_status("正在解析视频地址...", 10)

        # 开启后台子线程下载，防止阻塞UI
        threading.Thread(
            target=self._download_worker, args=(clean_url,), daemon=True
        ).start()

    def _download_worker(self, url):
        try:
            # 判断是否为抖音链接（移动端采用 API 直链解析）
            if "douyin.com" in url or "v.douyin.com" in url:
                success = self._download_douyin_mobile(url)
                if success:
                    self.update_status("🎉 下载完成！已保存至 Download 文件夹", 100)
                    self.btn_download.disabled = False
                    return

            # 通用 yt-dlp 解析
            self._download_yt_dlp(url)
            self.update_status("🎉 下载完成！已保存至 Download 文件夹", 100)
        except Exception as e:
            self.update_status(f"下载失败: {str(e)}", 0)
        finally:
            self.btn_download.disabled = False

    def _download_douyin_mobile(self, share_url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
            )
        }
        res = requests.get(share_url, headers=headers, allow_redirects=True, timeout=10)
        vid_match = re.search(r"video/(\d+)", res.url) or re.search(r"modal_id=(\d+)", res.url)
        if not vid_match:
            return False

        vid = vid_match.group(1)
        api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={vid}"
        api_res = requests.get(api_url, headers=headers, timeout=10).json()
        item_list = api_res.get("item_list", [])
        if not item_list:
            return False

        item = item_list[0]
        title = re.sub(r'[\\/:*?"<>|]', "_", item.get("desc", f"douyin_{vid}"))
        play_url = item["video"]["play_addr"]["url_list"][0].replace("playwm", "play")

        file_path = os.path.join(DOWNLOAD_DIR, f"{title}.mp4")
        v_res = requests.get(play_url, headers=headers, stream=True, timeout=30)
        
        with open(file_path, "wb") as f:
            for chunk in v_res.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
        return True

    def _download_yt_dlp(self, url):
        opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
        }
        if self.format_mode == "仅 MP3 音频":
            opts["format"] = "bestaudio/best"
        else:
            opts["format"] = "best"

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    def show_alert(self, title, message):
        dialog = MDDialog(title=title, text=message)
        dialog.open()


if __name__ == "__main__":
    VideoDownloaderApp().run()