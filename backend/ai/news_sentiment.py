"""News & Sentiment analyst module.

Consumes an optional sentiment feed from the supplied context (``sentiment`` /
``news_headlines``). Without a live news source the analyst remains neutral and
low-confidence; it never fabricates headlines or invents fundamentals, and it
only corroborates or flags the strategy side.
"""
from typing import Any, Dict, List, Literal

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.analyst_base import BaseAnalyst


class NewsSentimentAnalyst(BaseAnalyst):
    role = "NEWS_SENTIMENT"
    focus = "News headlines and sentiment read-through to the strategy side"
    weight = 1.0

    def _local_heuristic(self, ctx: Dict[str, Any]) -> AnalystVerdict:
        strategy_side: Literal["BUY", "SELL", "HOLD"] = ctx.get("strategy_signal", "HOLD")
        sentiment = ctx.get("sentiment")
        headlines = ctx.get("news_headlines") or []
        supporting: List[str] = []
        risks: List[str] = []

        if isinstance(sentiment, (int, float)):
            sentiment = float(sentiment)
            if sentiment >= 0.6:
                supporting.append(f"Positive sentiment read ({sentiment:.2f})")
            elif sentiment <= 0.4:
                supporting.append(f"Negative sentiment read ({sentiment:.2f})")
        elif isinstance(sentiment, dict):
            label = str(sentiment.get("label", "NEUTRAL")).upper()
            if label in ("BULLISH", "POSITIVE"):
                supporting.append(f"Sentiment {label}")
            elif label in ("BEARISH", "NEGATIVE"):
                supporting.append(f"Sentiment {label}")
            else:
                supporting.append("Sentiment neutral")
        elif sentiment is None:
            supporting.append("No live news feed configured - treating as neutral")
            risks.append("News risk unmonitored by this desk")

        if headlines:
            supporting.append(f"Monitoring {len(headlines)} headline(s)")

        if strategy_side in ("BUY", "SELL"):
            if strategy_side == "BUY":
                if any("Negative sentiment" in s or s == "Sentiment BEARISH" or s == "Sentiment NEGATIVE" for s in supporting):
                    return self._default_verdict(
                        ctx, "HOLD", 0.40, "Bearish sentiment read",
                        list(supporting), ["Headline/sentiment flow opposes long", *risks],
                        "Negative sentiment against the long; news analyst abstains."
                    )
                confidence = 0.50 + (0.08 if any("Positive sentiment" in s for s in supporting) else 0.0)
                return self._default_verdict(
                    ctx, "BUY", confidence, "Sentiment neutral-positive",
                    supporting, risks or ["No headline confirmation"],
                    "No material negative headline against the long."
                )

            if any("Positive sentiment" in s or s == "Sentiment BULLISH" or s == "Sentiment POSITIVE" for s in supporting):
                return self._default_verdict(
                    ctx, "HOLD", 0.40, "Bullish sentiment read",
                    list(supporting), ["Headline/sentiment flow opposes short", *risks],
                    "Positive sentiment against the short; news analyst abstains."
                )
            confidence = 0.50 + (0.08 if any("Sentiment BEARISH" in s or "Sentiment NEGATIVE" in s for s in supporting) else 0.0)
            return self._default_verdict(
                ctx, "SELL", confidence, "Sentiment neutral-negative",
                supporting, risks or ["No headline confirmation"],
                "No material positive headline against the short."
            )

        return self._default_verdict(
            ctx, "HOLD", 0.45, "Sentiment neutral",
            supporting, risks or ["No news catalyst"],
            "No news-driven trigger."
        )


news_sentiment_analyst = NewsSentimentAnalyst()