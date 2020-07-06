from bot.stable_strategy import StableStrategy
from services.strategy import Strategy

strategies = {"stable": StableStrategy}


def get_strategy(name: str, **params) -> Strategy:
    return strategies.get(name)(**params)
