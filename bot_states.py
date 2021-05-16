from random import sample

from pony.orm import commit

from database_models import Words

HELP_INFO = "Я знаю следующие команды:\n" \
            "✍ /new - Добавить новое слово и его перевод" \
            "🤔 /remind - Вспомнить перевод добавленного слова.\n" \
            "📔 /all - Посмотреть все добавленные слова.\n" \
            "❌ /delete - Удалить слово\n" \
            "📝 /test - Начать тест. Во время теста я буду выбирать случайные слова из тех, что вы " \
            "добавили, писать его русский или английский вариант, а вы должны написать перевод.\n" \
            "Например, я вам - apple, а вы мне - яблоко.\n" \
            "⏹ /stop - Остановить тест."

TEST_EXIT_INFO = "Тест отменен"
EXISTING_TRANSLATION = "Такой перевод уже есть"
DELETION_TEXT = "Слово удалено"
CANCEL_WORD_ADDING = "Добавление слова отменено"


class BotState:
    def __init__(self, user_state):
        self.user_state = user_state

    def handle_commands(self, text, start_text=''):
        command = text.strip()

        if command == "/help":
            return HELP_INFO + '\n\n' + start_text

        if command == "/new":
            new_state = NewWord(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text()

        if command == "/delete":
            new_state = DeleteWord(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text()

        if command == "/remind":
            new_state = Remind(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text()

        if command == "/all":
            new_state = CheckAllWords(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text()

        if command == "/test":
            new_state = StartTest(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text()

        if command == "/stop":
            if self.user_state.bot_state_name in (StartTest.__name__, Testing.__name__, AddAnotherTranslation.__name__):
                new_state = NeutralState(self.user_state)
                self.user_state.bot_state_name = new_state.__class__.__name__
                return TEST_EXIT_INFO + '\n\n' + new_state.start_text()

            return 'Нечего отменять🌚\nЕсли что-то хотите отменить, начните тест коммандой /test,' \
                   ' а потом отмените командой /stop 😌' + start_text

        if command == "/cancel":
            if self.user_state.bot_state_name in (NewWord.__name__, AddAnotherTranslation.__name__):
                new_state = NeutralState(self.user_state)
                self.user_state.bot_state_name = new_state.__class__.__name__
                return CANCEL_WORD_ADDING + '\n\n' + new_state.start_text()

            return start_text

        return False

    def start_text(self):
        return "Этот state еще не готов"

    def handle_answer(self, text):
        command = self.handle_commands(text, self.start_text())
        if command:
            return command

        return self.start_text()


# Neutral state

class NeutralState(BotState):
    def start_text(self):
        return "😌 Если хотите узнать, какие у меня есть команды, введите /help"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        return self.start_text()


# Greeting state

class Greeting(NeutralState):
    def start_text(self):
        return "Привет!!! 😀🖐\nЧтобы узнать, какие я знаю команды, введите /help 😉"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text()


# Add new word

class NewWord(BotState):
    def start_text(self):
        return "Напишите слово, чтобы добавить для него перевод\n" \
               "Чтобы отменить, введите /cancel"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        written_word = text.strip()

        self.user_state.last_word = written_word

        new_state = NewWordTranslation(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text()


class NewWordTranslation(BotState):
    def start_text(self):
        return "Добавьте перевод\n" \
               "Чтобы отменить, введите /cancel"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        word = self.user_state.last_word
        translation = text.strip()

        found_word = Words.get(word=word)
        found_translation = Words.get(word=translation)

        if found_word is None:
            found_word = Words(word=word, using_count=0)

        if found_translation is None:
            found_translation = Words(word=translation, using_count=0)
            commit()

        word_id = str(found_word.id)
        translation_id = str(found_translation.id)

        dictionary = self.user_state.dictionary

        # TODO: сделать подсчет кол-ва юзеров, использующих слово

        if word_id in dictionary:
            self.user_state.dictionary[word_id].append(translation_id)
        else:
            self.user_state.dictionary[word_id] = [translation_id]

        if translation_id in dictionary:
            self.user_state.dictionary[translation_id].append(word_id)
        else:
            self.user_state.dictionary[translation_id] = [word_id]

        new_state = AddAnotherTranslation(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text()


class AddAnotherTranslation(BotState):
    def start_text(self):
        return "Хотите добавить еще один вариант перевода? (да/нет)"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        answer = text.strip().lower()
        if answer in ('да', 'хочу', 'давай'):
            new_state = NewWordTranslation(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return new_state.start_text()

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text()


# Remind word's translation

class Remind(BotState):
    def start_text(self):
        return "Напишите слово, чтобы посмотреть его перевод"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        text_to_send = ""

        word = text.strip()

        found_word = Words.get(word=word)
        dictionary = self.user_state.dictionary
        word_id = str(found_word.id)
        if word_id not in dictionary:
            text_to_send = "Вы не добавляли такое слово.\n" \
                           "Чтобы его добавить, напишите /new"
        else:
            transl_idices = [int(id) for id in dictionary[word_id]]
            translations = [Words.get(id=id).word for id in transl_idices]

            for i, translation in enumerate(translations, 1):
                text_to_send += f"{i}) {translation}\n"

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return text_to_send + '\n\n' + new_state.start_text()


# Delete word

class DeleteWord(BotState):
    def start_text(self):
        return "Напишите слово, которое хотите удалить"

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        written_word = text.strip()
        word = Words.get(word=written_word)
        word_id = str(word.id)
        if word_id not in self.user_state.dictionary:
            return "Вы не добавляли это слово. Список всех добавленных слов " \
                   "можно посмотреть, если написать /all\n\n" + self.start_text()

        transl_indices = self.user_state.dictionary[word_id]
        self.user_state.dictionary.pop(word_id)

        for transl_id in transl_indices:
            print(transl_id, type(transl_id))
            self.user_state.dictionary[transl_id].remove(word_id)
            if not self.user_state.dictionary[transl_id]:
                self.user_state.dictionary.pop(transl_id)

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return DELETION_TEXT + '\n' + new_state.start_text()


# Check all added words

class CheckAllWords(BotState):
    def start_text(self):
        all_words = ''
        for word_id, transl_indices in self.user_state.dictionary.items():
            word = Words.get(id=int(word_id)).word
            translations = [Words.get(id=int(id)).word for id in transl_indices]
            all_words += f"{word} - {', '.join(translations)}\n"
        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return all_words + '\n\n' + new_state.start_text()

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        new_state = NeutralState(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text()


# Start test

class StartTest(BotState):
    def start_text(self):
        return "Напишите кол-во вопросов.\n" \
               f"Максимум {len(self.user_state.dictionary.keys())}(столько вы добавили слов)"

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
        self.user_state.test_list = dict(list=test_list,
                                         count=count,
                                         correct=0)

        new_state = Testing(self.user_state)
        self.user_state.bot_state_name = new_state.__class__.__name__
        return new_state.start_text()


class Testing(BotState):
    def start_text(self):
        word_id = int(self.user_state.test_list['list'][0])
        word = Words.get(id=word_id).word
        return word

    def handle_answer(self, text):
        command = self.handle_commands(text)
        if command:
            return command

        word_id = self.user_state.test_list['list'][0]
        answer = text.strip()
        translation = Words.get(word=answer)
        transl_id = None
        if translation is not None:
            transl_id = str(translation.id)

        dictionary = self.user_state.dictionary
        if transl_id in dictionary[word_id]:
            text_to_send = "Верно!\n\n"
            self.user_state.test_list['correct'] += 1
        else:
            transl_indices = [int(id) for id in dictionary[word_id]]
            translations = [Words.get(id=int(id)).word for id in transl_indices]
            text_to_send = f'Неправильно.\n\n{Words.get(id=int(word_id)).word} - {", ".join(translations)}\n\n'

        self.user_state.test_list['list'].pop(0)

        if len(self.user_state.test_list['list']) == 0:
            new_state = NeutralState(self.user_state)
            self.user_state.bot_state_name = new_state.__class__.__name__
            return text_to_send + \
                   "Тест окончен!\n" \
                   f"Ваш результат: {self.user_state.test_list['correct']}/{self.user_state.test_list['count']}\n\n" \
                   + new_state.start_text()

        return text_to_send + self.start_text()


START_STATE = Greeting.__name__
