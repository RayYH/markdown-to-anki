import json
import urllib.request
from typing import Dict, List

from markdown_to_anki.config import ANKI_BASE_URL
from markdown_to_anki.helpers.dict import safe_get


class AnkiApi:
    def __init__(self, anki_uri: str = ANKI_BASE_URL):
        self.anki_uri = anki_uri
        self.version_no = 6

    def anki_request(self, action: str, **params):
        return {"action": action, "params": params, "version": self.version_no}

    def invoke_action(self, action: str, **params):
        r_json = json.dumps(self.anki_request(action, **params)).encode("utf-8")
        response = json.load(
            urllib.request.urlopen(
                urllib.request.Request(self.anki_uri, r_json)
            )
        )
        if len(response) != 2:
            raise Exception("response has an unexpected number of fields")
        if "error" not in response:
            raise Exception("response is missing required error field")
        if "result" not in response:
            raise Exception("response is missing required result field")
        if response["error"] is not None:
            raise Exception(response["error"])
        return response["result"]

    #################################################################
    # Deck Actions
    #################################################################

    def deck_names(self):
        return self.invoke_action("deckNames")

    def deck_names_and_ids(self):
        return self.invoke_action("deckNamesAndIds")

    def get_decks(self, cards: List[int]):
        return self.invoke_action("getDecks", cards=cards)

    def create_deck(self, deck: str):
        return self.invoke_action("createDeck", deck=deck)

    def change_deck(self, cards: List[int], deck: str):
        return self.invoke_action("changeDeck", cards=cards, deck=deck)

    def delete_decks(self, decks: List[str]):
        return self.invoke_action("deleteDecks", decks=decks, cardsToo=True)

    def get_deck_config(self, deck: str):
        return self.invoke_action("getDeckConfig", deck=deck)

    def model_names(self, **params):
        return self.invoke_action("modelNames", **params)

    def create_model(self, **params):
        return self.invoke_action("createModel", **params)

    def update_model_styling(self, name: str, css: str):
        model = {
            "name": name,
            "css": css,
        }
        return self.invoke_action("updateModelStyling", model=model)

    def update_model_templates(self, name: str, templates: Dict):
        model = {
            "name": name,
            "templates": templates,
        }
        return self.invoke_action("updateModelTemplates", model=model)

    #################################################################
    # Card Actions
    #################################################################

    def get_ease_factors(self, **params):
        return self.invoke_action("getEaseFactors", **params)

    def set_ease_factor(self, **params):
        return self.invoke_action("setEaseFactors", **params)

    def card_info(self, cards: List[int]):
        return self.invoke_action("cardsInfo", cards=cards)

    def card_deck_name(self, card_id: int):
        cards = self.card_info(cards=[card_id])
        if not cards or not cards[0]:
            return ""
        return cards[0].get("deckName", "")

    def model_info(self, model_name: str):
        result = {
            "model_name": model_name,
            "fields_on_templates": self.invoke_action(
                "modelFieldsOnTemplates", modelName=model_name
            ),
            "templates": self.invoke_action(
                "modelTemplates", modelName=model_name
            ),
            "css": safe_get(
                self.invoke_action("modelStyling", modelName=model_name), "css"
            ),
        }
        return result

    def version(self):
        return self.invoke_action("version")

    #################################################################
    # Note Actions
    #################################################################
    def add_note(
        self,
        deck_name: str,
        model_name: str,
        fields: Dict | None = None,
        options: Dict | None = None,
        tags: List | None = None,
        audio: List | None = None,
        video: List | None = None,
        picture: List | None = None,
    ):
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields if fields else {},
            "options": options if options else {},
            "tags": tags if tags else [],
            "audio": audio if audio else [],
            "video": video if video else [],
            "picture": picture if picture else [],
        }
        return self.invoke_action("addNote", note=note)

    def update_note_fields(
        self,
        anki_id: int,
        fields: Dict | None = None,
        audio: List | None = None,
        video: List | None = None,
        picture: List | None = None,
    ):
        note = {
            "id": anki_id,
            "fields": fields if fields else {},
            "audio": audio if audio else [],
            "video": video if video else [],
            "picture": picture if picture else [],
        }
        return self.invoke_action("updateNoteFields", note=note)

    def get_tags(self):
        return self.invoke_action("getTags")

    def clear_unused_tags(self):
        return self.invoke_action("clearUnusedTags")

    def remove_empty_notes(self):
        return self.invoke_action("removeEmptyNotes")

    def notes_info(self, notes: List[int]):
        return self.invoke_action("notesInfo", notes=notes)

    def note_tags(self, note_id: int):
        r = self.notes_info([note_id])
        if not r or not r[0]:
            return []
        return r[0].get("tags") or []

    def delete_notes(self, notes: List[int]):
        return self.invoke_action("deleteNotes", notes=notes)

    #################################################################
    # Tag Actions
    #################################################################
    def add_tags(self, notes: List[int], tags: List[str]):
        for tag in tags:
            self.invoke_action("addTags", notes=notes, tags=tag)
        return True

    def remove_tags(self, notes: List[int], tags):
        for tag in tags:
            self.invoke_action("removeTags", notes=notes, tags=tag)
        return True

    def store_media_file_from_path(self, filename: str, path: str):
        return self.invoke_action(
            "storeMediaFile", filename=filename, path=path
        )

    def retrieve_media_file(self, filename):
        return self.invoke_action("retrieveMediaFile", filename=filename)

    def sync(self):
        return self.invoke_action("sync")
