"""Live paper-trading bot.

Runs a backtested strategy on live Binance data against a virtual portfolio,
reusing the *exact* strategy signal code and cost model from the backtesting
package — so the paper bot and the backtest cannot silently diverge.
"""

from .portfolio import PaperPortfolio
from .bot import PaperBot, BotConfig

__all__ = ["PaperPortfolio", "PaperBot", "BotConfig"]
