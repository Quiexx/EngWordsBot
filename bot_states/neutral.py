from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from . import add_words, delete_words, check_words, testing_mode
from .bot_state import BotState
from .constants import HELP_INFO


class NeutralState(BotState):
    def start_text(self):
        return "😌 Если хотите узнать, какие у меня есть команды, введите /help или нажмите на кнопочку"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        return self.start_text(), self.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/help", "Команды"):
            return HELP_INFO + '\n\n' + self.start_text(), self.get_keyboard()

        if command in ("/new", "Добавить"):
            new_state = add_words.NewWord(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/delete", "Удалить"):
            new_state = delete_words.DeleteWord(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/remind", "Напомнить"):
            new_state = check_words.Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/words", "Все слова"):
            new_state = check_words.CheckAllWords(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/test", "Тест"):
            new_state = testing_mode.StartTest(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Добавить', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Удалить', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Напомнить', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('Все слова', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('Команды', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Тест', color=VkKeyboardColor.PRIMARY)
        return keyboard


class Greeting(NeutralState):
    def start_text(self):
        return "Привет!!! 😀🖐\nЧтобы узнать, какие я знаю команды, введите /help или нажмите на кнопочку😉"

    def handle_answer(self, text):

        command = self.handle_commands(text)
        if command:
            return command

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/help", "Команды"):
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return HELP_INFO + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        command = super().handle_commands(command)
        if command:
            return command

        return False
