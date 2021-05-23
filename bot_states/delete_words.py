from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from . import neutral, check_words
from database_models import Words
from .bot_state import BotState
from .constants import WORDS_RE, DELETION_TEXT, CANCEL_DELETE


class DeleteWord(BotState):
    def start_text(self):
        return "Напишите слово, которое хотите удалить"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        written_word = text.strip()

        if WORDS_RE.fullmatch(written_word) is None:
            return "Кажется, вы ввели что-то не то\n" \
                   "В сообщении не должно быть цифр или эмодзи\n" \
                   "Можно вводить только русские и английские буквы\n\n" \
                   + self.start_text(), self.get_keyboard()

        word = Words.get(word=written_word)
        word_id = str(word.id) if word is not None else None
        if word_id not in self.user_state.dictionary:
            return "Вы не добавляли это слово. Список всех добавленных слов " \
                   "можно посмотреть, если написать /words\n\n" + self.start_text(), self.get_keyboard()

        transl_indices = self.user_state.dictionary[word_id]
        self.user_state.dictionary.pop(word_id)

        word.using_count -= 1
        if word.using_count == 0:
            Words.delete(word)

        for transl_id in transl_indices:
            self.user_state.dictionary[transl_id].remove(word_id)
            if not self.user_state.dictionary[transl_id]:
                self.user_state.dictionary.pop(transl_id)
                translation = Words.get(id=int(transl_id))
                translation.using_count -= 1
                if translation.using_count == 0:
                    Words.delete(translation)

        new_state = neutral.NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return DELETION_TEXT + '\n' + new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/cancel", "❌ Отменить"):
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_DELETE + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/remind", "🤔 Напомнить"):
            new_state = check_words.Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/words", "📔 Все слова"):
            new_state = check_words.CheckAllWords(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()
        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('🤔 Напомнить', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('📔 Все слова', color=VkKeyboardColor.SECONDARY)
        return keyboard
