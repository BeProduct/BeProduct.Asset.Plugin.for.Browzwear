import BwApi
import json
from .common import EventHandler
from abc import ABC, abstractmethod

LOAD = BwApi.BW_API_EVENT_HTML_LOAD
CLOSE = BwApi.BW_API_EVENT_HTML_CLOSE
MSG = BwApi.BW_API_EVENT_HTML_MSG
UNCAUGHT_EXCEPTION = BwApi.BW_API_EVENT_HTML_UNCAUGHT_EXCEPTION

class IBwApiWndEvents(ABC):
    @abstractmethod
    def on_load(self, garment_id: str, callback_id: int, data: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_close(self, garment_id: str, callback_id: int, data: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_msg(self, garment_id: str, callback_id: int, data: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_uncaught_exception(self, garment_id: str, callback_id: int, data: str) -> None:
        raise NotImplementedError


class Wnd:

    def __init__(self, url: str, title: str, width: int, height: int, style: object):
        self.width = width
        self.height = height
        self.handle = -1
        self.url = url
        self.title = title
        self.style = style

        self.event_handler = EventHandler(self.__event_handler)
        self.delegate = None

    def set_delegate(self, delegate: "IBwApiWndEvents"):
        self.delegate = delegate

    def __event_handler(self, garment_id: str, callback_id: int, data: str) -> int:

        if self.delegate:
            if callback_id == LOAD:
                self.delegate.on_load(garment_id, callback_id, data)
            elif callback_id == CLOSE:
                self.delegate.on_close(garment_id, callback_id, data)
            elif callback_id == MSG:
                self.delegate.on_msg(garment_id, callback_id, data)
            elif callback_id == UNCAUGHT_EXCEPTION:
                self.delegate.on_uncaught_exception(garment_id, callback_id, data)

        return 0

    def get_rect(self) -> BwApi.WndRect:
        left = 0
        top = 0

        # center the window relatively to main app window
        host_application = json.loads(BwApi.HostApplicationGet())
        if 'window_rect' in host_application:

            left = host_application['window_rect']['left'] + (host_application['window_rect']['width'] - self.width) / 2
            if left < 0:
                left = 0

            top = host_application['window_rect']['top'] + (host_application['window_rect']['height'] - self.height) / 2
            if top < 0:
                top = 0

        rect = BwApi.WndRect(int(left), int(top), self.width, self.height)

        return rect

    def show(self):
        style = json.dumps(self.style)

        rect = self.get_rect()

        self.handle = BwApi.WndHTMLCreateUrl(self.url,
                                             self.title,
                                             style,
                                             rect
                                             )

        BwApi.WndHTMLEventRegister(self.handle, LOAD, self.event_handler, LOAD)
        BwApi.WndHTMLEventRegister(self.handle, CLOSE, self.event_handler, CLOSE)
        BwApi.WndHTMLEventRegister(self.handle, MSG, self.event_handler, MSG)
        BwApi.WndHTMLEventRegister(self.handle, UNCAUGHT_EXCEPTION, self.event_handler, UNCAUGHT_EXCEPTION)

    def send_message(self, data):
        BwApi.WndHTMLMessageSend(self.handle, json.dumps(data))

    def focus(self):
        BwApi.WndHTMLSetFocus(self.handle)
    
    def close(self):
        BwApi.WndHTMLClose(self.handle)
