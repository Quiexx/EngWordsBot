from bot_states import add_words, check_words, delete_words, neutral, testing_mode, bot_state

STATES = {
    add_words.NewWord.__name__: add_words.NewWord,
    add_words.NewWordTranslation.__name__: add_words.NewWordTranslation,
    add_words.AddAnotherTranslation.__name__: add_words.AddAnotherTranslation,
    check_words.CheckAllWords.__name__: check_words.CheckAllWords,
    check_words.ShowAll.__name__: check_words.ShowAll,
    check_words.WriteToFind.__name__: check_words.WriteToFind,
    check_words.FindWords.__name__: check_words.FindWords,
    delete_words.DeleteWord.__name__: delete_words.DeleteWord,
    neutral.NeutralState.__name__: neutral.NeutralState,
    neutral.Greeting.__name__: neutral.Greeting,
    check_words.Remind.__name__: check_words.Remind,
    testing_mode.StartTest.__name__: testing_mode.StartTest,
    testing_mode.Testing.__name__: testing_mode.Testing,
    bot_state.BotState.__name__: bot_state.BotState,
}

START_STATE = neutral.Greeting.__name__
