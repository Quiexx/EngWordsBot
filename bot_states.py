from random import sample
import re

from pony.orm import commit
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from database_models import Words

HELP_INFO = "Я знаю следующие команды:\n" \
            "✍ /new - Добавить новое слово и его перевод\n" \
            "🤔 /remind - Вспомнить перевод добавленного слова.\n" \
            "📔 /words - Посмотреть все добавленные слова.\n" \
            "❌ /delete - Удалить слово\n" \
            "📝 /test - Начать тест. Во время теста я буду выбирать случайные слова из тех, что вы " \
            "добавили, писать его русский или английский вариант, а вы должны написать перевод.\n" \
            "Например, я вам - apple, а вы мне - яблоко. Или наоборот."

TEST_EXIT_INFO = "Тест отменен"
EXISTING_TRANSLATION = "Такой перевод уже есть"
DELETION_TEXT = "Слово удалено"
CANCEL_WORD_ADDING = "Добавление слова отменено"
CANCEL_REMIND = "Напоминание отменено"
CANCEL_ALL_WORDS = "Просмотр слов отменен"
CANCEL_DELETE = "Удаление отменено"
SHOW_COUNT = 15

WORDS_RE = re.compile('[A-Za-zА-Яа-яЁё\s-]+')


class BotState:
    def __init__(self, user_state):
        self.user_state = user_state

    def handle_commands(self, text):
        return False

    def start_text(self):
        return "Этот state еще не готов"

    def handle_answer(self, text):
        return self.start_text(), self.get_keyboard()

    def get_keyboard(self):
        return None


# Neutral state

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
            new_state = NewWord(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/delete", "Удалить"):
            new_state = DeleteWord(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/remind", "Напомнить"):
            new_state = Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/words", "Все слова"):
            new_state = CheckAllWords(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/test", "Тест"):
            new_state = StartTest(self.user_state)
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


# Greeting state

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


# Add new word

class NewWord(BotState):
    def start_text(self):
        return "Напишите слово, чтобы добавить для него перевод\n" \
               "Чтобы отменить, введите /cancel или нажмите на кнопочку"

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

        self.user_state.buffer = {"word": written_word}

        new_state = NewWordTranslation(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_WORD_ADDING + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/remind", "🤔 Напомнить"):
            self.user_state.buffer.clear()
            new_state = Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/words", "📔 Все слова"):
            self.user_state.buffer.clear()
            new_state = CheckAllWords(self.user_state)
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
               "Чтобы отменить, введите /cancel или нажмите на кнопочку"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        word = self.user_state.buffer["word"]

        translation = text.strip()

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
        new_state = NeutralState(self.user_state)
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


# Remind word's translation

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
            transl_idices = [int(id) for id in dictionary[word_id]]
            translations = [Words.get(id=id).word for id in transl_idices]

            for translation in translations:
                text_to_send += f"🟣 {translation}\n"

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return text_to_send + '\n\n' + new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/cancel", "❌ Отменить"):
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_REMIND + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard


# Delete word

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
        word_id = str(word.id) if word else None
        if word_id not in self.user_state.dictionary:
            return "Вы не добавляли это слово. Список всех добавленных слов " \
                   "можно посмотреть, если написать /all\n\n" + self.start_text()

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

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return DELETION_TEXT + '\n' + new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()
        if command in ("/cancel", "❌ Отменить"):
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return CANCEL_DELETE + '\n\n' + new_state.start_text(), new_state.get_keyboard()

        if command in ("/remind", "🤔 Напомнить"):
            new_state = Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text(), new_state.get_keyboard()

        if command in ("/all", "📔 Все слова"):
            new_state = CheckAllWords(self.user_state)
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


# Check all added words

class CheckAllWords(BotState):
    def start_text(self):
        word_count = len(self.user_state.dictionary.keys())

        if word_count == 0:
            self.user_state.buffer.clear()
            new_state = NeutralState(self.user_state)
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

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text(), new_state.get_keyboard()

    def handle_commands(self, text):
        command = text.strip()

        if command in ("/cancel", "❌ Отменить"):
            self.user_state.buffer.clear()
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
            return new_state.get_keyboard()

        keyboard.add_button('📖 Показать еще', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_word_list(self, from_idx):
        all_words = ''
        count = 0
        word_ids = [int(id) for id in self.user_state.dictionary.keys()]
        words = Words.select(lambda x: x.id in word_ids).order_by(Words.word)[from_idx: from_idx + SHOW_COUNT]
        for word in words:
            count += 1
            transl_ids = [int(id) for id in self.user_state.dictionary[str(word.id)]]
            transls = [Words.get(id=int(id)).word for id in transl_ids]
            all_words += f"{word.word} - {', '.join(transls)}\n"
        return all_words, count


class WriteToFind(BotState):
    def start_text(self):
        return "Введите фрагмент слова\n" \
               "Введите /cancel, чтобы отменить поиск"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        fragment = text.strip()

        indices = [int(id) for id in self.user_state.dictionary.keys()]
        words_lambda = lambda x: x.id in indices and fragment in x.word
        words_selection = Words.select(words_lambda)
        selected_count = len(words_selection)

        if selected_count == 0:
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
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
            new_state = NeutralState(self.user_state)
            return new_state.get_keyboard()

        keyboard.add_button('📖 Показать еще', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('❌ Отменить', color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_word_list(self, idx_from):
        all_words = ''
        count = 0
        indices = [int(id) for id in self.user_state.dictionary.keys()]
        fragment = self.user_state.buffer["fragment"]
        words = Words.select(lambda x: x.id in indices and fragment in x.word).order_by(Words.word)[
                idx_from: idx_from + SHOW_COUNT]
        for word in words:
            count += 1
            transl_ids = [int(id) for id in self.user_state.dictionary[str(word.id)]]
            transls = [Words.get(id=int(id)).word for id in transl_ids]
            all_words += f"{word.word} - {', '.join(transls)}\n"
        return all_words, count


# Start test

class StartTest(BotState):
    def start_text(self):
        return "Напишите кол-во вопросов.\n" \
               f"Максимум {len(self.user_state.dictionary.keys())}(столько вы добавили слов)\n" \
               "Чтобы отменить тест, введите /stop или нажмите на кнопочку"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        try:
            count = int(text.strip())
        except ValueError:
            return "Вы что-то не то ввели. Нужно написать число\n\n" + self.start_text()

        if count > len(self.user_state.dictionary.keys()):
            return "Слишком много, у вас нет столько слов\n\n" + self.start_text()

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
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return TEST_EXIT_INFO + '\n\n' + new_state.start_text(), new_state.get_keyboard()
        return False

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=True)
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
            transl_indices = [int(id) for id in dictionary[word_id]]
            translations = [Words.get(id=int(id)).word for id in transl_indices]
            text_to_send = f'Неправильно.\n\n{Words.get(id=int(word_id)).word} - {", ".join(translations)}\n\n'

        self.user_state.buffer['list'].pop(0)

        if len(self.user_state.buffer['list']) == 0:
            correct = self.user_state.buffer['correct']
            count = self.user_state.buffer['count']
            self.user_state.buffer.clear()
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return text_to_send + \
                   "Тест окончен!\n" \
                   f"Ваш результат: {correct}/{count}\n\n" \
                   + new_state.start_text(), new_state.get_keyboard()

        return text_to_send + self.start_text(), self.get_keyboard()


START_STATE = Greeting.__name__
