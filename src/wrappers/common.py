import BwApi


class EventHandler(BwApi.CallbackBase):
    def __init__(self, callback: callable):
        super().__init__()
        self.callback = callback

    def Run(self, garment_id: str, callback_id: int, data: str) -> int:
        if not self.callback:
            return 0

        value = self.callback(garment_id, callback_id, data)
        if value is None:
            return 1
        else:
            return value
