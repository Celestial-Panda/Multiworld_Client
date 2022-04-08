import asyncio
from asyncio import Task
from typing import List

from base_logger import logging
logger = logging.getLogger(__name__)

from Dolphin.dolphinGameHandler import DolphinGameHandler
from Model.itemDto import ItemDto
from util.abstractGameHandler import AbstractGameHandler

from View.guiWriter import GuiWriter
from PySide6.QtCore import Signal
from random import Random
from Model.itemDto import output_strs

class ClientGameConnection(GuiWriter):
    _items_to_process: List[ItemDto] = list()
    _items_to_send: List[ItemDto] = list()
    _world_id: int = 0

    _console_handler: AbstractGameHandler

    def __init__(self, world_id: int, signal: Signal = None):
        super().__init__(signal)
        self._console_handler = DolphinGameHandler(world_id)
        self._world_id = world_id
        self._random = Random()

    async def process_items(self) -> None:
        while len(self._items_to_process) > 0:
            item_dto = self._items_to_process[-1]
            chosen_str = self._random.choice(output_strs)
            await self.write(item_dto.make_output_str(chosen_str))
            try:
                if not await self._console_handler.give_item(item_dto.itemId):
                    await asyncio.sleep(3)
                    continue
                self._items_to_process.pop()
                await asyncio.sleep(0)
            except RuntimeError as exc:
                logger.error(exc)
                del exc

    async def handle(self) -> None:
        await self.write("Connected to Dolphin")
        while await self._console_handler.is_connected():  # Thread set interval instead of a while loop would be better
            try:
                state = await self._console_handler.get_queued_items()
                if state[0] != 0 and state[1] != 0 and state[1] != 0xFF:
                    item_dto = ItemDto(self._world_id, state[0], state[1])  # World ID should be set in client
                    chosen_str = self._random.choice(output_strs)
                    await self.write(item_dto.make_output_str(chosen_str))
                    self._items_to_send.append(item_dto)
                    await self._console_handler.clear_queued_items()
            except RuntimeError as rne:
                del rne
            finally:
                if len(self._items_to_process) > 0:
                    asyncio.create_task(self.process_items())
            await asyncio.sleep(0)
        await self.write("Unexpected Disconnect from Dolphin, attempting to reconnect.....")

    async def connect(self) -> Task:
        await self.write("Connecting to Console")
        while not await self._console_handler.is_connected():
            await self._console_handler.connect()
            if await self._console_handler.is_connected():
                break
            await asyncio.sleep(15)
            await self.write("Dolphin was not found, trying again in 15 seconds.")
        return asyncio.create_task(self.handle())

    def get_item_to_send(self) -> List[ItemDto]:
        return self._items_to_send

    def remove_item_to_send(self, item_dto:ItemDto):
        self._items_to_send.remove(item_dto)

    def push_item_to_process(self, item_dto: ItemDto) -> None:
        self._items_to_process.append(item_dto)
