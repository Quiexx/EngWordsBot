from random import sample

from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from . import neutral
from database_models import Words
from .bot_state import BotState
from .constants import TEST_EXIT_INFO


class StartTest(BotState):
    def start_text(self):
        count = len(self.user_state.dictionary.keys())
        if count == 0:
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return 'Вы не добавили ни одного слова.\n' \
                   'Чтобы добавить слова, нажмите на кнопку "Добавить" или введите /new.\n' \
                   'После этого можете начинать тест'

        return "Напишите кол-во вопросов.\n" \
               f"Максимум {count}(столько вы добавили слов)\n" \
               "Чтобы отменить тест, введите /stop или нажмите на кнопочку"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        try:
            count = int(text.strip())
        except ValueError:
            return "Вы что-то не то ввели. Нужно написать число\n\n" + self.start_text(), self.get_keyboard()

        if count > len(self.user_state.dictionary.keys()):
            return "Слишком много, у вас нет столько слов\n\n" + self.start_text(), self.get_keyboard()

        if count <= 0:
            return "Нельзя составить тест с отрицательным количеством вопросов или вообще без вопросов -_-\n\n" \
                   + self.start_text(), self.get_keyboard()

        test_list = sample(self.user_state.dictionary.keys(), k=count)
        self.user_state.buffer = dict(list=test_list,
                                      count=count,
                                      correct=0)

        new_state = Testing(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/stop", "Остановить тест"):
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return TEST_EXIT_INFO + '\n\n' + new_state.start_text(), new_state.get_keyboard()
        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)

        count = len(self.user_state.dictionary.keys())
        if count == 0:
            new_state = neutral.NeutralState(self.user_state)
            return new_state.get_keyboard()

        keyboard.add_button('Остановить тест', color=VkKeyboardColor.NEGATIVE)

        return keyboard


class Testing(StartTest):
    def start_text(self):
        word_id = int(self.user_state.buffer['list'][0])
        word = Words.get(id=word_id).word
        return word

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        word_id = self.user_state.buffer['list'][0]
        answer = text.strip()
        translation = Words.get(word=answer)
        transl_id = None
        if translation is not None:
            transl_id = str(translation.id)

        dictionary = self.user_state.dictionary
        if transl_id in dictionary[word_id]:
            text_to_send = "Верно!\n\n"
            self.user_state.buffer['correct'] += 1
        else:
            transl_indices = [int(w_id) for w_id in dictionary[word_id]]
            translations = [Words.get(id=int(w_id)).word for w_id in transl_indices]
            text_to_send = f'Неправильно.\n\n{Words.get(id=int(word_id)).word} - {", ".join(translations)}\n\n'

        self.user_state.buffer['list'].pop(0)

        if len(self.user_state.buffer['list']) == 0:
            correct = self.user_state.buffer['correct']
            count = self.user_state.buffer['count']
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return text_to_send + \
                   "Тест окончен!\n" \
                   f"Ваш результат: {correct}/{count}\n\n" \
                   + new_state.start_text(), new_state.get_keyboard()

        return text_to_send + self.start_text(), self.get_keyboard()
