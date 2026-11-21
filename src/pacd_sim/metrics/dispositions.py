"""Per-episode diagnostic measures derived from the verified raw-event counts."""

from pacd_sim.metrics.summarize import EpisodeRecord


def episode_dispositions(episode: EpisodeRecord) -> dict[str, object]:
    """Summarize one complete episode with one governor disposition per candidate."""
    if episode.completion_status != "EVENT_CHAIN_COMPLETED":
        raise ValueError("Disposition metrics require a completed episode")
    candidates = episode.candidate_action_count
    escalations = episode.escalated_action_count
    if episode.approved_action_count + escalations + episode.prohibited_action_count != candidates:
        raise ValueError("Governor disposition counts do not account for every candidate action")

    return {
        "format": "pacd-episode-dispositions-v1",
        "seed": episode.seed,
        "config_hash": episode.config_hash,
        "completion_status": episode.completion_status,
        "counts": {
            "candidate_action_count": candidates,
            "approved_action_count": episode.approved_action_count,
            "escalated_action_count": escalations,
            "prohibited_action_count": episode.prohibited_action_count,
            "simulated_execution_count": episode.simulated_execution_count,
            "verified_execution_count": episode.verified_execution_count,
            "prohibited_execution_count": episode.prohibited_execution_count,
        },
        "escalation_fraction": {
            "numerator": escalations,
            "denominator": candidates,
            "unit": "fraction_of_candidate_actions",
            "value": escalations / candidates if candidates else None,
        },
    }
