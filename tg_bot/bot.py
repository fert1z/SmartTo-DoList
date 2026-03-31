import telebot

bot = telebot.TeleBot("8571036130:AAEE09nxSvlBOOgrVOXHk58gHVaTgqrJcho", parse_mode=None)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Howdy, how are you doing?")
	

bot.infinity_polling()