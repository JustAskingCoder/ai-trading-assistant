import { CommitteeDecision } from '../types';

export type GatingSide = 'BUY' | 'SELL';

export function committeeApproved(
  committee: CommitteeDecision | null | undefined,
  side: GatingSide
): boolean {
  if (!committee) return true;
  return committee.verdict === side;
}

export function committeeDowngraded(
  committee: CommitteeDecision | null | undefined,
  side: GatingSide
): boolean {
  return !!committee && committee.verdict !== side;
}

export function committeeHoldReasons(
  committee: CommitteeDecision | null | undefined,
  fallback?: string
): string[] {
  if (committee) {
    const list = Array.isArray(committee.reasons) ? committee.reasons : [];
    if (list.length > 0) return list;
    if (committee.risk_vetoed) {
      return ['Risk & Execution analyst vetoed the trade — downgraded to HOLD.'];
    }
    if (committee.verdict === 'HOLD') {
      return ['Committee did not reach majority consensus on a directional side.'];
    }
  }
  return [fallback ?? 'Committee sign-off not available yet.'];
}