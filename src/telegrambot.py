# -*- coding: utf-8 -*-

import os
import sys
import time
import asyncio
import base64
import logging
import yaml
import traceback
import websockets
import platform
from typing import Optional, List, Dict, Any, Union, Set

import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from dataclasses import dataclass
from playwright.async_api import async_playwright

from .chatgpt import ChatGPTBot, get_logger

logger = get_logger(__name__)

class SavedQuestion:
    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.update = update
        self.context = context

class TelegramBot:
    def __init__(self, config_file):
        f = open(config_file)
        config = yaml.safe_load(f)

        self.telegram_api_key = config['telegram_api_key']
        self.chatgpt_accounts = config['accounts']
        self.tasks: List[SavedQuestion] = []
        self.saved_questions: Dict[str, SavedQuestion] = {}

        self.developer_conversation_id = None
        self.developer_user_id = None

        if 'developer_conversation_id' in config:
            self.developer_conversation_id = config['developer_conversation_id']
            self.developer_user_id = config['developer_user_id']

        self.bots: List[ChatGPTBot] = []
        self._paused = False

        self.application = ApplicationBuilder().token(self.telegram_api_key).build()    
        start_handler = CommandHandler('start', self.start)
        self.application.add_handler(start_handler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.bots:
            await self.init()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Done!")

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        if not self.bots:
            await self.init()

        logger.info("++++++++update.message.chat.type: %s", update.message.chat.type)
        chat_type = update.message.chat.type
        if chat_type == "private":
            asyncio.create_task(self.handle_private_message(update, context))
        # elif chat_type == "supergroup":
        else:
            asyncio.create_task(self.handle_super_group_message(update, context))

    @property
    def paused(self):
        return self._paused
    
    @paused.setter
    def paused(self, value):
        self._paused = value

    async def init(self):
        asyncio.create_task(self.handle_questions())
        PLAY = await async_playwright().start()
        for account in self.chatgpt_accounts:
            user = account['user']
            psw = account['psw']
            bot = ChatGPTBot(PLAY, user, psw)
            await bot.init()
            self.bots.append(bot)

    def choose_bot(self, user_id) -> ChatGPTBot:
        bots = []
        for bot in self.bots:
            if bot.standby:
                continue
            bots.append(bot)

        for bot in bots:
            try:
                user = bot.users[user_id]
                return bot
            except KeyError:
                pass

        bot_index = 0
        user_counts = [len(bot.users) for bot in bots]
        try:
            bot_index = user_counts.index(min(user_counts))
            return bots[bot_index]
        except ValueError:
            return None

    # async def echo(self, conversation_id: str, user_id: str, message: str):
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        message = update.message.text
        bot = self.choose_bot(user_id)
        if not bot:
            logger.info('no available bot')
            self.save_question(update, context)
            #queue message
            return False
        try:
            async for msg in bot.send_message(user_id, message):
                await update.message.reply_text(msg)
            await update.message.reply_text("[END]")
            return True
        except Exception as e:
            logger.exception(e)
        self.save_question(update, context)
        return False

    async def echo_supergroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        message = update.message.text
        bot = self.choose_bot(user_id)
        if not bot:
            logger.info('no available bot')
            self.save_question(update, context)
            #queue message
            return False
        try:
            msgs = []
            async for msg in bot.send_message(user_id, message):
                if msg == '[BEGIN]\n':
                    await self.application.bot.send_chat_action(update.effective_chat.id, "typing")
                    continue
                msgs.append(msg)
            await update.message.reply_text(''.join(msgs))
            return True
        except Exception as e:
            logger.exception(e)
        self.save_question(update, context)
        return False

    async def handle_questions(self):
        while True:
            await asyncio.sleep(15.0)
            handled_question = []
            saved_questions = self.saved_questions.copy()
            for user_id, question in saved_questions.items():
                try:
                    user_id = str(question.update.effective_user.id)
                    message = question.update.message.text
                    logger.info("++++++++handle question: %s", message)
                    bot = self.choose_bot(user_id)
                    if not bot:
                        break
                    msgs: List[str] = []
                    async for msg in bot.send_message(user_id, message):
                        if msg == '[BEGIN]\n':
                            await self.application.bot.send_chat_action(question.update.effective_chat.id, "typing")
                        else:
                            msgs.append(msg)
                    await question.update.message.reply_text(''.join(msgs))
                    handled_question.append(user_id)
                except Exception as e:
                    logger.exception(e)
                    continue
            for question in handled_question:
                del self.saved_questions[question]

    def save_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        self.saved_questions[user_id] = SavedQuestion(update, context)

    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.echo(update, context)
        except Exception as e:
            logger.exception(e)
            if self.developer_user_id:
                await self.sendUserText(self.developer_conversation_id, self.developer_user_id, f"exception occur at:{time.time()}: {traceback.format_exc()}")

    async def handle_super_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.echo_supergroup(update, context)
        except Exception as e:
            logger.exception(e)
            if self.developer_user_id:
                await self.sendUserText(self.developer_conversation_id, self.developer_user_id, f"exception occur at:{time.time()}: {traceback.format_exc()}")

    async def close(self):
        for bot in self.bots:
            await bot.close()

    def run(self):
        self.application.run_polling()

bot: Optional[TelegramBot]  = None

async def get_bot():
    global bot
    if not bot:
        bot = TelegramBot(sys.argv[1])
    if not bot.bots:
        await bot.init()
    return bot

async def resume():
    bot = await get_bot()
    bot.paused = False
    while not bot.paused:
        await asyncio.sleep(1.0)

def run():
    global bot
    logger.info('++++++pid: %s', os.getpid())
    logger.info('send `/start` to the bot with telegram to initialize chatgpt')
    if len(sys.argv) < 2:
        if platform.system() == 'Windows':
            print("usage: python -m chatgpt_telegram config_file")
        else:
            print("usage: python3 -m chatgpt_telegram config_file")
        return

    bot = TelegramBot(sys.argv[1])
    bot.run()

if __name__ == '__main__':
    run()
