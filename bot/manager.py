import asyncio
import logging.config

from bot.bot import Bot, BotConfig
from bot.config import config
from lib_common.app import app

app.app_context().push()


class Manager:
    def __init__(self, configs):
        self.configs = configs

    async def run(self):
        bots = []

        for config in self.configs:
            for pair in config["pairs"]:
                coin_1, coin_2 = pair.split("/")
                create_bot = config.get("bot") or Bot
                bot = create_bot(
                    {**config, "pair": pair, "coin_1": coin_1, "coin_2": coin_2}
                )
                bots.append(bot)

        await asyncio.gather(*[bot.run() for bot in bots])


configs = [

]

if __name__ == "__main__":
    logging.config.dictConfig(config["logger"])

    manager = Manager(configs)

    asyncio.run(manager.run())
