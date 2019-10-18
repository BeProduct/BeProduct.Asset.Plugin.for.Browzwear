import BwApi
import json

class Colorway:
    def __init__(self, garment_id: str, colorway_id: int):
        self.garment_id = garment_id
        self.colorway_id = colorway_id

    def get_id(self) -> int:
        return self.colorway_id

    def create_material(self, material_json: object) -> int:
        return BwApi.MaterialCreate(self.garment_id, self.colorway_id, json.dumps(material_json))

    def delete_material(self, material_id: int):
        BwApi.MaterialDelete(self.garment_id, self.colorway_id, material_id)
