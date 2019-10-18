import BwApi
from .common import EventHandler
from abc import ABC, abstractmethod
import uuid

POST_INITIALIZE = 1
SESSION_REQUEST = 2

_callables = {}


class IBwApiEvents(ABC):
    @abstractmethod
    def on_post_initialize(self) -> None:
        raise NotImplementedError


class Callback:
    def __init__(self, callback: callable, data: object):
        self._callback = callback
        self._data = data

    def get_callback_func(self):
        return self._callback

    def get_data(self):
        return self._data


class BwApiWrapper:
    def __init__(self):
        self.event_handler = EventHandler(self.__event_handler)
        self.delegate = None

    def set_delegate(self, delegate: "IBwApiEvents"):
        self.delegate = delegate

    def __event_handler(self, garment_id: str, callback_id: int, data: str) -> int:
        if callback_id == POST_INITIALIZE:
            self.delegate.on_post_initialize()

        if callback_id == SESSION_REQUEST:
            if data in _callables:
                callback_func = _callables[data].get_callback_func()
                callback_data = _callables[data].get_data()
                callback_func(callback_data)
            else:
                print("something went wrong, can't find the callback function")

        return 1

    def init(self) -> int:
        BwApi.EventRegister(self.event_handler, POST_INITIALIZE, BwApi.BW_API_EVENT_POST_INTIALIZE)
        BwApi.UpdateSessionFunctionSet_v2(self.event_handler)
        return int(0x000e0030)

    @staticmethod
    def invoke_on_main_thread(callback: callable, data: object) -> None:
        # store the callable function and call it async
        global _callables
        callable_id = str(uuid.uuid4())
        _callables[callable_id] = Callback(callback, data)
        BwApi.UpdateSessionFunctionRequest_v2("com.beproduct.asset-library", SESSION_REQUEST, callable_id)
