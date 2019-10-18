import BwApi
import json


class Material:
    def __init__(self, garment_id: str, colorway_id: int, material_id: int):
        self.garment_id = garment_id
        self.colorway_id = colorway_id
        self.material_id = material_id

    def get_id(self) -> int:
        return self.material_id

    def update_from_file(self, data):
        BwApi.MaterialUpdateFromFile(self.garment_id, self.colorway_id, self.material_id, data)

    def update(self, data: object) -> None:
        BwApi.MaterialUpdate(self.garment_id, self.colorway_id, self.material_id, json.dumps(data))

    def group_update(self, material_group_json: object):
        if BwApi.MaterialGroup(self.garment_id, self.colorway_id, self.material_id) == 0:
            return

        BwApi.MaterialGroupUpdate(self.garment_id, self.colorway_id, self.material_id, json.dumps(material_group_json))

    def group_item_add(self, material_id: int, group_material_item_json: object):
        if BwApi.MaterialGroup(self.garment_id, self.colorway_id, self.material_id) == 0:
            return

        BwApi.MaterialGroupItemAdd(self.garment_id, self.colorway_id, self.material_id, material_id, json.dumps(group_material_item_json))

    def group_clear_items(self):
        if BwApi.MaterialGroup(self.garment_id, self.colorway_id, self.material_id) == 0:
            return

        group_material = BwApi.MaterialGroupGet(self.garment_id, self.colorway_id, self.material_id)
        group_material_obj = json.loads(group_material)

        if 'type' not in group_material_obj or group_material_obj['type'] == 'button' or group_material_obj['type'] == 'zipper':
            return

        group_material_ids = BwApi.MaterialGroupItemIds(self.garment_id, self.colorway_id, self.material_id)
        for material_id in group_material_ids:
            BwApi.MaterialGroupItemRemove(self.garment_id, self.colorway_id, self.material_id, material_id)
            BwApi.MaterialDelete(self.garment_id, self.colorway_id, material_id)

    def group_item_ids_get(self):
        if BwApi.MaterialGroup(self.garment_id, self.colorway_id, self.material_id) == 0:
            return

        return BwApi.MaterialGroupItemIds(self.garment_id, self.colorway_id, self.material_id)

    def group_item_get(self, group_material_id: int):
        if BwApi.MaterialGroup(self.garment_id, self.colorway_id, self.material_id) == 0:
            return

        group_material_item = BwApi.MaterialGroupItemGet(self.garment_id, self.colorway_id, self.material_id, group_material_id)
        return json.loads(group_material_item)
