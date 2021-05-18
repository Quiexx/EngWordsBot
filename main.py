
# В settings.py хранится токен и id группы
import logging
from random import randint

import vk_api
from pony.orm import db_session
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from bot_states import START_STATE
import bot_states
from database_models import UserState
import settings

log = logging.getLogger("bot")


def log_configure():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler("bot.log", encoding="UTF-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%d-%m-%Y %H:%M"))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


class Bot:
    """
    VK-bot for learning English words

    Use python 3.9
    """

    def __init__(self, group_id, token):
        """
        :param group_id: id of vk group
        :param token: secret token of vk group
        """
        self.group_id = group_id
        self.token = token

        self.vk = vk_api.VkApi(token=token, api_version='5.130')
        self.long_poller = VkBotLongPoll(self.vk, group_id)
        self.api = self.vk.get_api()

    def run(self):
        """bot launch"""
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception as exc:
                log.exception(f"Event processing error: {exc}")

    @db_session
    def on_event(self, event):
        """
        :param event: VkBotEventType object
        :return: None
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.debug("Wrong event type: %s", event.type)
            return

        user_id = event.message.peer_id
        text = event.message.text

        user_state = UserState.get(user_id=str(user_id))

        if user_state is not None:
            bot_state = getattr(bot_states, user_state.bot_state_name)(user_state)
            text_to_send, keyboard = bot_state.handle_answer(text)
        else:
            bot_state = getattr(bot_states, START_STATE)(user_state)
            UserState(user_id=str(user_id), bot_state_name=START_STATE, dictionary={})
            text_to_send = bot_state.start_text()
            keyboard = bot_state.get_keyboard()

        keyboard_to_send = keyboard.get_keyboard() if keyboard else None

        self.api.messages.send(
            user_id=event.message.peer_id,
            random_id=randint(0, 2 ** 20),
            message=text_to_send,
            keyboard=keyboard_to_send
        )

        # log.info("bot sent message to user %d", user_id)


if __name__ == '__main__':
    log_configure()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)

    bot.run()


