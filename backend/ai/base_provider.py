"""AI Provider base interface and mock/fallback implementation."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import httpx
from backend.ai.schemas import AIAnalysisResponse, EntryZone
from backend.core.logging import logger
from backend.core.config import settings


SYSTEM_PROMPT = """You are a market-analysis assistant.
Analyze the supplied market data only.
Do not invent prices, indicators, news, volume, fundamentals, or market conditions.
Do not claim certainty. You are not the final execution authority.
Return a structured assessment containing:
signal ("BUY", "SELL", or "HOLD"),
confidence (0.0 to 1.0),
setup (concise title),
entry_zone ({"min": ..., "max": ...}),
stop_loss,
target,
risk_reward,
timeframe,
supporting_factors (list of strings),
risk_factors (list of strings),
invalidation_conditions (list of strings).
If the supplied evidence is insufficient or contradictory, return HOLD.
Do not make decisions outside the supplied data."""


class AIProvider(ABC):
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @abstractmethod
    async def analyze_market_setup(self, data: Dict[str, Any]) -> AIAnalysisResponse:
        pass


class LocalHeuristicProvider(AIProvider):
    """Deterministic local AI evaluator when API keys are not provided."""
    def __init__(self):
        super().__init__("LocalHeuristic", "heuristic-v1")

    async def analyze_market_setup(self, data: Dict[str, Any]) -> AIAnalysisResponse:
        price = data.get("price", 100.0)
        indicators = data.get("indicators", {})
        patterns = data.get("patterns", [])
        strategy_sig = data.get("strategy_signal", "HOLD")

        supporting = []
        risks = []
        invalidations = []

        rsi = indicators.get("rsi")
        ema20 = indicators.get("ema20")
        ema50 = indicators.get("ema50")

        if ema20 and ema50 and ema20 > ema50:
            supporting.append("Bullish trend: EMA20 is above EMA50")
        else:
            risks.append("EMA20 is not above EMA50 or data is missing")

        if rsi:
            if 50 <= rsi <= 68:
                supporting.append(f"Healthy RSI momentum ({rsi:.1f})")
            elif rsi > 70:
                risks.append(f"Overbought RSI condition ({rsi:.1f})")
            elif rsi < 35:
                risks.append(f"Oversold RSI condition ({rsi:.1f})")

        for p in patterns:
            p_name = p.get("pattern", "")
            if p.get("direction") == "BUY":
                supporting.append(f"Confirmed pattern: {p_name}")
            elif p.get("direction") == "SELL":
                risks.append(f"Conflicting bearish pattern: {p_name}")

        invalidations.append("Price closes below 20-period EMA")
        invalidations.append("Volume contraction on breakout candle")

        if strategy_sig == "BUY" and len(risks) <= 1:
            signal = "BUY"
            conf = 0.78
            sl = round(price * 0.992, 2)
            tgt = round(price * 1.016, 2)
        elif strategy_sig == "SELL":
            signal = "SELL"
            conf = 0.75
            sl = round(price * 1.008, 2)
            tgt = round(price * 0.984, 2)
        else:
            signal = "HOLD"
            conf = 0.60
            sl = round(price * 0.99, 2)
            tgt = round(price * 1.01, 2)

        rr = round(abs(tgt - price) / (abs(price - sl) + 1e-10), 2)

        return AIAnalysisResponse(
            signal=signal,
            confidence=conf,
            setup=f"{data.get('symbol', 'Asset')} Technical Analysis",
            entry_zone=EntryZone(min=round(price * 0.999, 2), max=round(price * 1.001, 2)),
            stop_loss=sl,
            target=tgt,
            risk_reward=rr,
            timeframe=data.get("timeframe", "5m"),
            supporting_factors=supporting or ["Technical alignment with local strategy"],
            risk_factors=risks or ["General market volatility"],
            invalidation_conditions=invalidations,
            provider=self.name,
            model=self.model
        )


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        super().__init__("OpenAI", model)
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def analyze_market_setup(self, data: Dict[str, Any]) -> AIAnalysisResponse:
        if not self.api_key:
            logger.info("OpenAI API key missing. Falling back to local heuristic provider.")
            return await LocalHeuristicProvider().analyze_market_setup(data)

        user_content = f"Analyze the following market setup:\n{json.dumps(data, indent=2)}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_content}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2
                    }
                )
                if res.status_code != 200:
                    logger.error("OpenAI API returned %s: %s", res.status_code, res.text)
                    return await LocalHeuristicProvider().analyze_market_setup(data)

                resp_json = res.json()
                raw_out = json.loads(resp_json["choices"][0]["message"]["content"])
                validated = AIAnalysisResponse(**raw_out)
                validated.provider = self.name
                validated.model = self.model
                return validated
        except Exception as e:
            logger.error("OpenAI analysis failed: %s", e)
            return await LocalHeuristicProvider().analyze_market_setup(data)


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str = None, model: str = "claude-3-5-haiku-20241022"):
        super().__init__("Claude", model)
        self.api_key = api_key or settings.ANTHROPIC_API_KEY

    async def analyze_market_setup(self, data: Dict[str, Any]) -> AIAnalysisResponse:
        if not self.api_key:
            logger.info("Anthropic API key missing. Falling back to local heuristic provider.")
            return await LocalHeuristicProvider().analyze_market_setup(data)

        user_content = f"{SYSTEM_PROMPT}\n\nAnalyze this setup and reply strictly in valid JSON:\n{json.dumps(data, indent=2)}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1000,
                        "temperature": 0.2,
                        "messages": [{"role": "user", "content": user_content}]
                    }
                )
                if res.status_code != 200:
                    logger.error("Claude API returned %s: %s", res.status_code, res.text)
                    return await LocalHeuristicProvider().analyze_market_setup(data)

                resp_json = res.json()
                text_content = resp_json["content"][0]["text"]
                # Extract JSON block if wrapped
                start = text_content.find("{")
                end = text_content.rfind("}") + 1
                raw_out = json.loads(text_content[start:end])
                validated = AIAnalysisResponse(**raw_out)
                validated.provider = self.name
                validated.model = self.model
                return validated
        except Exception as e:
            logger.error("Claude analysis failed: %s", e)
            return await LocalHeuristicProvider().analyze_market_setup(data)


def get_ai_provider(provider_name: str = None) -> AIProvider:
    provider = provider_name or settings.DEFAULT_AI_PROVIDER
    if provider.lower() == "openai":
        return OpenAIProvider()
    elif provider.lower() == "claude":
        return ClaudeProvider()
    return LocalHeuristicProvider()
