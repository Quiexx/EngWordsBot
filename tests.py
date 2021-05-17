from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock

from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotMessageEvent

from main import Bot, UserState
import bot_states


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()

    return wrapper


@isolate_db
class Test(TestCase):
    RAW_EVENT = {'type': 'message_new',
                 'object': {'message': {'date': 1616486994,
                                        'from_id': 1,
                                        'id': 71,
                                        'out': 0,
                                        'peer_id': 1,
                                        'text': 'gg',
                                        'conversation_message_id': 64,
                                        'fwd_messages': [],
                                        'important': False,
                                        'random_id': 0,
                                        'attachments': [],
                                        'is_hidden': False},
                            'client_info': {'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link',
                                                               'callback', 'intent_subscribe', 'intent_unsubscribe'],
                                            'keyboard': True,
                                            'inline_keyboard': True,
                                            'carousel': False,
                                            'lang_id': 0}},
                 'group_id': 203296345,
                 'event_id': 'dfc8cca55bff4e4bbe083eb9524069e36800d71b'}

    user_state_mock = Mock()
    user_state_mock.dictionary = dict()

    GREETING_INPUTS = [
        'Привет',
        '/help',
    ]

    GREETING_EXPECTED_OUTPUTS = [
        bot_states.Greeting(user_state_mock).start_text(),
        bot_states.HELP_INFO + '\n\n'
    ]

    COMMANDS_INPUTS = [
        '/help',
        'random message',
        '/new',
        'word',
        'нет',
        '/delete',
        '/remind',
        '/test',
        '/stop',
    ]

    COMMANDS_EXPECTED_OUTPUTS = [
        bot_states.HELP_INFO + '\n\n',
        bot_states.NeutralState(user_state_mock).start_text(),
        bot_states.NewWord(user_state_mock).start_text(),
        bot_states.NewWordTranslation(user_state_mock).start_text(),
        bot_states.AddAnotherTranslation(user_state_mock).start_text(),
        bot_states.DeleteWord(user_state_mock).start_text(),
        bot_states.Remind(user_state_mock).start_text(),
        bot_states.StartTest(user_state_mock).start_text(),
        bot_states.TEST_EXIT_INFO + '\n\n' + bot_states.NeutralState(user_state_mock).start_text(),
    ]

    def test_normal(self):
        count = 5
        obj = {'a': 1}
        events = [obj] * count
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock
        with patch('main.vk_api.VkApi'):
            with patch('main.VkBotLongPoll', return_value=long_poller_listen_mock):
                bot = Bot('', '')
                bot.on_event = Mock()
                bot.run()

                bot.on_event.assert_called()
                bot.on_event.assert_any_call(obj)
                assert bot.on_event.call_count == count

    def test_greeting(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for message in self.GREETING_INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = message
            events.append(VkBotMessageEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('main.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.run()

        assert send_mock.call_count == len(self.GREETING_INPUTS)

        real_outputs = []
        for _, kwargs in send_mock.call_args_list:
            real_outputs.append(kwargs['message'])

        assert real_outputs == self.GREETING_EXPECTED_OUTPUTS

    def test_commands(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for message in self.COMMANDS_INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = message
            events.append(VkBotMessageEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('main.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            user_id = self.RAW_EVENT['object']['message']['peer_id']
            UserState(user_id=str(user_id), bot_state_name=bot_states.NeutralState.__name__, dictionary={})
            bot.run()

        assert send_mock.call_count == len(self.COMMANDS_INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])

        assert real_outputs == self.COMMANDS_EXPECTED_OUTPUTS
