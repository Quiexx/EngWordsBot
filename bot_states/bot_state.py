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
