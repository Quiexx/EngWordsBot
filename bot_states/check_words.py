from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from . import neutral
from database_models import Words

from .bot_state import BotState
from .constants import WORDS_RE, CANCEL_REMIND, CANCEL_ALL_WORDS, SHOW_COUNT, MAX_SYMBOLS


class Remind(BotState):
    def start_text(self):
        return "Напишите слово, чтобы посмотреть его перевод"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        word = text.strip()
        if WORDS_RE.fullmatch(word) is None:
            return "Кажется, вы ввели что-то не то\n" \
                   "В сообщении не должно быть цифр или эмодзи\n" \
                   "Можно вводить только русские и английские буквы\n\n" \
                   + self.start_text(), self.get_keyboard()

        found_word = Words.get(word=word)
        dictionary = self.user_state.dictionary
        word_id = str(found_word.id) if found_word else None
        if word_id not in dictionary:
            text_to_send = "Вы не добавляли такое слово.\n" \
                           "Чтобы его добавить, напишите /new"
        else:
            text_to_send = f'"{word}" - это:\n'
            transl_indices = [int(w_id) for w_id in dictionary[word_id]]
            translations = [Words.get(id=w_id).word for w_id in transl_indices]

            for translation in translations:
                text_to_send += f"🟣 {translation}\n"

        new_state = neutral.NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return text_to_send + '\n\n' + new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/cancel", "❌ Отменить"):
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_REMIND + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard


class CheckAllWords(BotState):
    def start_text(self):
        word_count = len(self.user_state.dictionary.keys())

        if word_count == 0:
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return "Вы еще не добавили слова\n" \
                   'Чтобы добавить слово, напишите /new\n' \
                   'или нажмите на кнопку "Добавить"' \
                   + '\n\n' + new_state.start_text()

        self.user_state.buffer.update({"word_count": word_count})
        return f"Всего слов: {word_count}\n\n" \
               f'🟢 /all (кнопка "📖 Показать все")\n\tпоказать все слова в алфавитном порядке\n' \
               f'🟢 /letter (кнопка "🔍 Найти по буквам")\n\tнайти слово по первой(ым) букве(ам)\n' \
               f'🟢 /cancel (кнопка "❌ Отменить")\n\tотменить просмотр слов\n'

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        new_state = neutral.NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_ALL_WORDS + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/all", "📖 Показать все"):
            new_state = ShowAll(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/letter", "🔍 Найти по буквам"):
            self.user_state.buffer.clear()
            new_state = WriteToFind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)

        word_count = len(self.user_state.dictionary.keys())
        if word_count == 0:
            new_state = neutral.NeutralState(self.user_state)
            return new_state.get_keyboard()

        keyboard.add_button('📖 Показать все', color=VkKeyboardColor.SECONDARY)
        keyboard.add_button('🔍 Найти по буквам', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard


class ShowAll(BotState):
    def start_text(self):
        word_count = self.user_state.buffer["word_count"]

        if "from_word_idx" in self.user_state.buffer.keys():
            from_idx = self.user_state.buffer["from_word_idx"]
        else:
            from_idx = 0
            self.user_state.buffer["from_word_idx"] = 0

        all_words, all_count = self.get_word_list(from_idx)

        if all_count == SHOW_COUNT and from_idx + SHOW_COUNT < word_count:
            text = f'Еще слов: {word_count - from_idx - SHOW_COUNT}\n' \
                   f'Чтобы показать еще, введите /more\n' \
                   f'Чтобы отменить показ слов, введите /cancel\n'
        else:
            text = "Это все слова"
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return ''.join(all_words) + '\n\n' + text + "\n\n" + new_state.start_text()

        return ''.join(all_words) + '\n\n' + text

    def handle_answer(self, text):

        command = self.handle_commands(text)
        if command:
            return command

        new_state = ShowAll(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return "Кажется, вы ввели что-то не то\n\n" + new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_ALL_WORDS + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/more", "📖 Показать еще"):
            self.user_state.buffer["from_word_idx"] += SHOW_COUNT
            new_state = ShowAll(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)

        if "word_count" not in self.user_state.buffer:
            new_state = neutral.NeutralState(self.user_state)
            return new_state.get_keyboard()

        keyboard.add_button('📖 Показать еще', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_word_list(self, from_idx):
        all_words = ''
        count = 0
        word_ids = [int(w_id) for w_id in self.user_state.dictionary.keys()]
        to_idx = from_idx + SHOW_COUNT
        words = Words.select(lambda x: x.id in word_ids).order_by(Words.word)[from_idx: to_idx]
        for word in words:
            count += 1
            transl_ids = [int(w_id) for w_id in self.user_state.dictionary[str(word.id)]]
            translations = [Words.get(id=int(w_id)).word for w_id in transl_ids]
            all_words += f"{word.word} - {', '.join(translations)}\n"
        return all_words, count


class WriteToFind(BotState):
    def start_text(self):
        return "Введите фрагмент слова\n" \
               f"Максимум можно ввести {MAX_SYMBOLS} символов\n" \
               "Введите /cancel, чтобы отменить поиск"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        fragment = text.strip()

        if len(fragment) > MAX_SYMBOLS:
            return "Вы ввели слишком много символов. Максимум - 100\n" \
                   "Попробуйте ввести что-то покороче\n\n" \
                   + self.start_text(), self.get_keyboard()

        indices = [int(w_id) for w_id in self.user_state.dictionary.keys()]
        words_selection = Words.select(lambda x: x.id in indices and fragment in x.word)
        selected_count = len(words_selection)

        if selected_count == 0:
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return "Нет слов, содержащих такой фрагмент\n\n" + new_state.start_text(), new_state.get_keyboard()

        self.user_state.buffer.update({"fragment": fragment})
        self.user_state.buffer.update({"idx_from": 0})
        self.user_state.buffer.update({"found_count": selected_count})

        new_state = FindWords(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_ALL_WORDS + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard


class FindWords(BotState):
    def start_text(self):
        idx_from = self.user_state.buffer["idx_from"]
        count = self.user_state.buffer["found_count"]

        all_words, all_count = self.get_word_list(idx_from)

        if all_count == SHOW_COUNT and idx_from + SHOW_COUNT < count:
            text = f'Еще слов: {count - idx_from - SHOW_COUNT}\n' \
                   f'Чтобы показать еще, введите /more\n' \
                   f'Чтобы отменить показ слов, введите /cancel\n'
        else:
            text = "Это все слова"
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return ''.join(all_words) + '\n\n' + text + "\n\n" + new_state.start_text()

        return ''.join(all_words) + '\n\n' + text

    def handle_answer(self, text):

        command = self.handle_commands(text)
        if command:
            return command

        new_state = FindWords(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return "Кажется, вы ввели что-то не то\n\n" + new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = neutral.NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_ALL_WORDS + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/more", "📖 Показать еще"):
            self.user_state.buffer["idx_from"] += SHOW_COUNT
            new_state = FindWords(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)

        if not self.user_state.buffer:
            new_state = neutral.NeutralState(self.user_state)
            return new_state.get_keyboard()

        keyboard.add_button('📖 Показать еще', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_word_list(self, idx_from):
        all_words = ''
        count = 0
        indices = [int(w_id) for w_id in self.user_state.dictionary.keys()]
        fragment = self.user_state.buffer["fragment"]
        words = Words.select(lambda x: x.id in indices and fragment in x.word).order_by(Words.word)[
                idx_from: idx_from + SHOW_COUNT]
        for word in words:
            count += 1
            transl_ids = [int(w_id) for w_id in self.user_state.dictionary[str(word.id)]]
            translations = [Words.get(id=int(w_id)).word for w_id in transl_ids]
            all_words += f"{word.word} - {', '.join(translations)}\n"
        return all_words, count
