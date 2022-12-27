# chatgpt-telegram

# Installation

on unix like platform, install `chatgpt-telegram` with the following command.

```bash
python3 -m pip install -U chatgpt-telegram
playwright install firefox
```

on the Windows platform, use the following command to install `chatgpt-telegram`:

```bash
python -m pip install -U chatgpt-telegram
playwright install firefox
```

# configuration

You can start this bot with the following command:

```bash
python3 -m chatgpt_telegram bot-config.yaml
```

On the Windows platform, with the following command:

```bash
python -m chatgpt_telegram bot-config.yaml
```

which bot-config.yaml contains telegram bot configuration and chatgpt accounts as shown below.

```yaml
telegram_api_key: ""
accounts:
 - user: ""
   psw: ""
```

`telegram_api_key` section specify telegram bot api key. `accounts` section specify chatgpt test accounts. `user` field can not be empty, but you can leave `psw` to empty. If it is left empty, the user will need to manually enter the password upon login. Multiple accounts can be specified in the accounts section to improve ChatGPT responses.

If you are running a bot in a server, you need to install `Xvfb` on the server, and use `VNC` at the client side to connect to `Xvfb`. For more information, refer to [Remote_control_over_SSH](https://en.wikipedia.org/wiki/Xvfb#Remote_control_over_SSH).


After you start this bot, send `/start` to bot to start the initialization process, wich will pop up a browser navigating to `https://chat.openai.com/chat`. On the first time you start the browser, you need to handle the login processes. Some automated processes such as auto-filling of account names and passwords will be carried out, but you will still need to manually solve CAPTCHAs during the login process.

# Acknowledgements

- [chatgpt-api](https://github.com/transitive-bullshit/chatgpt-api)
- [chatGPT-telegram-bot](https://github.com/altryne/chatGPT-telegram-bot)
- [ChatGPT](https://github.com/ChatGPT-Hackers/ChatGPT)
