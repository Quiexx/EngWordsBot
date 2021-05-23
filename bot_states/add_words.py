from pony.orm import commit
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from . import neutral, check_words
from .bot_state import BotState
from .constants import MAX_SYMBOLS, WORDS_RE, CANCEL_WORD_ADDING
from database_models import Words


class NewWord(BotState):
    def start_text(self):
        return "Напишите слово, чтобы добавить для него перевод\n" \
               f"Максимум можно ввести {MAX_SYMBOLS} символов\n" \
               "Чтобы отменить, введите /cancel или нажмите на кнопочку"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        written_word = text.strip().lower()

        if len(written_word) > MAX_SYMBOLS:
            return "Вы ввели слишком много символов. Максимум - 100\n" \
                   "Попробуйте ввести что-то покороче\n\n" \
                   + self.start_text(), self.get_keyboard()

        if WORDS_RE.fullmatch(written_word) is None:
            return "Кажется, вы ввели что-то не то\n" \
                   "В сообщении не должно быть цифр или эмодзи\n" \
                   "Можно вводить только русские и английские буквы\n\n" \
                   + self.start_text(), self.get_keyboard()

        self.user_state.buffer = {"word": written_word}

        new_state = NewWordTranslation(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_WORD_ADDING + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/remind", "🤔 Напомнить"):
            self.user_state.buffer.clear()
            new_state = check_words.Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/words", "📔 Все слова"):
            self.user_state.buffer.clear()
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


class NewWordTranslation(NewWord):
    def start_text(self):
        word = self.user_state.buffer["word"]
        return f'Добавьте перевод для "{word}"\n' \
               f"Максимум можно ввести {MAX_SYMBOLS} символов\n" \
               "Чтобы отменить, введите /cancel или нажмите на кнопочку"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        word = self.user_state.buffer["word"]

        translation = text.strip().lower()

        if word == translation:
            return "Вы ввели то же самое\n\n" \
                   + self.start_text(), self.get_keyboard()

        if len(translation) > MAX_SYMBOLS:
            return "Вы ввели слишком много символов. Максимум - 100\n" \
                   "Попробуйте ввести что-то покороче\n\n" \
                   + self.start_text(), self.get_keyboard()

        if WORDS_RE.fullmatch(translation) is None:
            return "Кажется, вы ввели что-то не то\n" \
                   "В сообщении не должно быть цифр или эмодзи\n" \
                   "Можно вводить только русские и английские буквы\n\n" \
                   + self.start_text(), self.get_keyboard()

        found_word = Words.get(word=word)
        found_translation = Words.get(word=translation)

        if found_word is None:
            found_word = Words(word=word, using_count=0)
            commit()

        if found_translation is None:
            found_translation = Words(word=translation, using_count=0)
            commit()

        word_id = str(found_word.id)
        translation_id = str(found_translation.id)

        dictionary = self.user_state.dictionary

        if word_id in dictionary:
            if translation_id in dictionary[word_id]:
                new_state = AddAnotherTranslation(self.user_state)
                self.user_state.bot_state_name = new_state.__class__.__name__
                return "Вы уже добавляли такой перевод\n\n" + new_state.start_text(), new_state.get_keyboard()
            else:
                self.user_state.dictionary[word_id].append(translation_id)
        else:
            self.user_state.dictionary[word_id] = [translation_id]
            found_word.using_count += 1

        if translation_id in dictionary:
            self.user_state.dictionary[translation_id].append(word_id)
        else:
            self.user_state.dictionary[translation_id] = [word_id]
            found_translation.using_count += 1

        new_state = AddAnotherTranslation(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()


class AddAnotherTranslation(NewWord):
    def start_text(self):
        return "Хотите добавить еще один вариант перевода? (да/нет)"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        answer = text.strip().lower()
        if answer in ('да', 'хочу', 'давай', 'yes'):
            new_state = NewWordTranslation(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        self.user_state.buffer.clear()
        new_state = neutral.NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('Да', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Нет', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('🤔 Напомнить', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('📔 Все слова', color=VkKeyboardColor.SECONDARY)
        return keyboard
