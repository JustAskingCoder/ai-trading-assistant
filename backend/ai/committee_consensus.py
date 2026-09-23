"""Deterministic Committee Consensus engine for the pre-trade research desk.

Gate rule (from Epic 23):
- A BUY/SELL verdict requires a **weighted majority >= 3/6** on that side.
- The deterministic Risk/Execution analyst carries **veto** power: any veto
  downgrades the decision to HOLD (with the veto reasons attached).
- Otherwise the committee defaults to HOLD.
"""
from datetime import datetime, timezone
from typing import Dict, List

from backend.ai.analyst_schemas import AnalystVerdict, CommitteeDecision
from backend.core.logging import logger

RISK_ROLE = "RISK_EXECUTION"
MAJORITY_WEIGHT = 3.0
SIDE_WEIGHT_THRESHOLD = 3.0


class CommitteeConsensus:
    """Aggregates the 6 analyst verdicts into one deterministic decision."""

    def __init__(self, majority_weight: float = MAJORITY_WEIGHT) -> None:
        self.majority_weight = majority_weight

    def decide(self, verdicts: List[AnalystVerdict], symbol: str = None, timeframe: str = "5m") -> CommitteeDecision:
        if not verdicts:
            return CommitteeDecision(
                verdict="HOLD",
                overall_confidence=0.0,
                num_agree=0,
                risk_vetoed=False,
                reasons=["Committee received no analyst verdicts"],
                symbol=symbol,
                timeframe=timeframe,
            )

        if len(verdicts) == 6:
            total_analysts = 6
        else:
            total_analysts = max(len(verdicts), 6)

        risk_verdicts = [v for v in verdicts if v.analyst_role == RISK_ROLE]
        llm_verdicts = [v for v in verdicts if v.analyst_role != RISK_ROLE]

        risk_vetoed = any(getattr(v, "veto", False) for v in risk_verdicts)
        risk_reasons: List[str] = []
        for rv in risk_verdicts:
            if getattr(rv, "veto", False):
                flags = rv.risk_flags or ["Risk analyst vetoed the trade"]
                risk_reasons.extend(f"RISK VETO: {flag}" for flag in flags)

        side_weight: Dict[str, float] = {"BUY": 0.0, "SELL": 0.0}
        for v in llm_verdicts:
            if v.side in ("BUY", "SELL"):
                side_weight[v.side] += float(v.weight)

        high_side = max(side_weight, key=side_weight.get)
        side_reached_majority = side_weight[high_side] >= self.majority_weight

        num_agree = 0
        if risk_vetoed:
            verdict = "HOLD"
            reasons = [*risk_reasons]
            if side_reached_majority:
                reasons.insert(0, f"{high_side} reached {side_weight[high_side]:.1f}/6 but was vetoed by Risk/Execution")
            else:
                reasons.insert(0, "Risk/Execution vetoed the candidate trade")
            # Confidence collapsed by the veto.
            agreeing = [v for v in verdicts if v.side == "HOLD"]
            if risk_verdicts and not risk_verdicts[0].veto:
                pass
            overall = self._mean_confidence(verdicts)
            overall = min(overall, 0.35)
            num_agree = sum(1 for v in llm_verdicts if v.side == "HOLD")
        elif side_reached_majority:
            verdict = high_side
            agreeing = [v for v in llm_verdicts if v.side == high_side]
            num_agree = len(agreeing)
            overall = self._weighted_confidence(agreeing)
            reasons = [f"{high_side} achieved weighted majority ({side_weight[high_side]:.1f} of 6 votes)"]
            if supporting := [v.top_factor for v in agreeing if v.top_factor][:3]:
                reasons.append("Top factors: " + "; ".join(supporting))
        else:
            verdict = "HOLD"
            overall = self._mean_confidence(llm_verdicts)
            reasons = [
                f"No side reached weighted majority {self.majority_weight:g}/6 "
                f"(BUY {side_weight['BUY']:.1f} / SELL {side_weight['SELL']:.1f}); committee defaulted to HOLD"
            ]
            num_agree = sum(1 for v in llm_verdicts if v.side == "HOLD")

        if verdict == "HOLD" and "Committee gated" not in "".join(reasons):
            hold_notes = [v.risk_flags[0] for v in llm_verdicts if v.side == "HOLD" and v.risk_flags][:2]
            if hold_notes and verdict == "HOLD" and not risk_vetoed and not side_reached_majority:
                reasons.append("Unsatisfied analysts cite: " + "; ".join(hold_notes))

        return CommitteeDecision(
            verdict=verdict,
            overall_confidence=round(min(1.0, max(0.0, overall)), 3),
            num_agree=num_agree,
            total_analysts=total_analysts,
            risk_vetoed=risk_vetoed,
            reasons=reasons,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _weighted_confidence(verdicts: List[AnalystVerdict]) -> float:
        total_weight = sum(v.weight for v in verdicts) or 1.0
        return sum(v.confidence * v.weight for v in verdicts) / total_weight

    @staticmethod
    def _mean_confidence(verdicts: List[AnalystVerdict]) -> float:
        if not verdicts:
            return 0.0
        return sum(v.confidence for v in verdicts) / len(verdicts)


committee_consensus = CommitteeConsensus()


__all__ = ["CommitteeConsensus", "committee_consensus", "RISK_ROLE", "MAJORITY_WEIGHT"]