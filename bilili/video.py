import os
import re
import time
import math
import subprocess

from bilili.downloader.middleware import DownloaderMiddleware
from bilili.utils.quality import quality_map
from bilili.tools import ffmpeg


global_middleware = DownloaderMiddleware()

class BililiContainer():
    """ bilibili 媒体容器类
    即 B 站上的单个视频，其中可能包含多个媒体单元
    * 包含多个 flv 片段
    * 包含 m4s 的视频与音频流
    * 包含完整的一个 mp4
    """

    def __init__(self, id, name, path, meta, format="flv"):

        self.id = id
        self.name = name
        self.path = path
        self.meta = meta
        self.format = format

        self.medias = []
        self.qn = None
        self.height = None
        self.width = None
        self._ = DownloaderMiddleware(parent=global_middleware)

    def merge(self):
        if self._.merged or self._.merging:
            return
        for media in self.medias:
            media._.merging = True
        if self.format == 'mp4':
            with open(self.medias[0].path, 'rb') as fr:
                with open(self.path, 'wb') as fw:
                    fw.write(fr.read())
        elif self.format == 'flv':
            video_path_list = [media.path for media in self.medias]
            ffmpeg.join_videos(video_path_list, self.path)
        elif self.format == 'm4s':
            ffmpeg.join_video_audio(self.medias[0].path, self.medias[1].path, self.path)
        else:
            print("Unknown format {}".format(self.format))
        # 清除合并完成的视频片段
        for media in self.medias:
            os.remove(media.path)
        self._.merged = True
        for media in self.medias:
            media._.merging = False

    def append_media(self, *args, **kwargs):
        self.medias.append(BililiMedia(*args, **kwargs, container = self))

    def __str__(self):
        return '{} 「{}」'.format(self.name, quality_map[self.qn]['description'])


class BililiMedia():
    """ bilibili 媒体单元类
    从 B 站直接获取的可下载的媒体单元，可能是 flv、mp4、m4s
    """

    def __init__(self, id, url, qn, size, height, width, container, type="segment"):

        self.id = id
        self.qn = qn
        self.height = height
        self.width = width
        self.url = url
        self.container = container
        self.path = os.path.splitext(self.container.path)[0]
        if self.container.format == "flv":
            self.path += "_{:02d}.flv".format(id)
        elif self.container.format == "m4s":
            self.path += "_{}.m4s".format(type)
        elif self.container.format == "mp4":
            self.path += "_dl.mp4"
        self.name = os.path.split(self.path)[-1]
        self._ = DownloaderMiddleware(parent=self.container._)
        self._.total_size = size

        if self.container.qn is None:
            self.container.qn = qn
        if self.container.width is None:
            self.container.width = width
        if self.container.height is None:
            self.container.height = height
        if self._.total_size is None:
            print("[warn] {} 无法获取 size".format(self.name))
            self._.total_size = 0
