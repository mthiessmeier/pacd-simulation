"""Boolean dependency availability and mission continuity for the synthetic environment."""

from collections import Counter, defaultdict, deque

from pacd_sim.environment.model import EnvironmentState
from pacd_sim.reproducibility.canonical import canonical_sha256
from pacd_sim.schema import StrictFrozenModel


class AvailabilityReport(StrictFrozenModel):
    """Deterministically ordered entity and mission memberships at one state."""

    available_entity_ids: tuple[str, ...]
    unavailable_entity_ids: tuple[str, ...]
    service_ids: tuple[str, ...]
    available_service_ids: tuple[str, ...]
    mission_ids: tuple[str, ...]
    operational_mission_ids: tuple[str, ...]

    def audit_summary(self) -> dict[str, int | str]:
        """Bind all memberships while keeping the audit row size independent of ID lengths."""
        return {
            "entity_count": len(self.available_entity_ids) + len(self.unavailable_entity_ids),
            "available_entity_count": len(self.available_entity_ids),
            "service_count": len(self.service_ids),
            "available_service_count": len(self.available_service_ids),
            "mission_count": len(self.mission_ids),
            "operational_mission_count": len(self.operational_mission_ids),
            "availability_digest": canonical_sha256(self),
        }


def evaluate_availability(state: EnvironmentState) -> AvailabilityReport:
    """Propagate intrinsic failures through mandatory dependencies and mission service support."""
    intrinsic = {asset.id: asset.available for asset in state.assets}
    intrinsic.update((identity.id, identity.enabled) for identity in state.identities)
    intrinsic.update((s.id, s.active and not s.isolated) for s in state.sessions)
    intrinsic.update((credential.id, credential.active) for credential in state.credentials)
    intrinsic.update((service.id, service.available) for service in state.services)
    intrinsic.update((mission.id, mission.operational) for mission in state.mission_functions)

    dependents: defaultdict[str, set[str]] = defaultdict(set)
    for edge in state.dependencies:
        if edge.weight > 0:
            dependents[edge.upstream_id].add(edge.downstream_id)

    supporting_mission = {service.id: service.mission_id for service in state.services}
    remaining_services = Counter(supporting_mission.values())
    mission_ids = tuple(mission.id for mission in state.mission_functions)
    unavailable = {entity_id for entity_id, working in intrinsic.items() if not working}
    unavailable.update(mission for mission in mission_ids if not remaining_services[mission])

    # Start with every intrinsically working entity available. Each failed entity
    # is processed once, so a dependency cycle loses availability only if seeded.
    pending = deque(unavailable)
    while pending:
        failed = pending.popleft()
        affected = set(dependents.get(failed, ()))
        if failed in supporting_mission:
            mission = supporting_mission[failed]
            remaining_services[mission] -= 1
            if remaining_services[mission] == 0:
                affected.add(mission)
        newly_unavailable = affected - unavailable
        unavailable.update(newly_unavailable)
        pending.extend(newly_unavailable)

    return AvailabilityReport(
        available_entity_ids=tuple(sorted(intrinsic.keys() - unavailable)),
        unavailable_entity_ids=tuple(sorted(unavailable)),
        service_ids=tuple(supporting_mission),
        available_service_ids=tuple(s for s in supporting_mission if s not in unavailable),
        mission_ids=mission_ids,
        operational_mission_ids=tuple(m for m in mission_ids if m not in unavailable),
    )


def continuity_transition(
    before: AvailabilityReport, after: AvailabilityReport
) -> dict[str, int | str]:
    """Classify the continuity of each governed mission across one state transition."""
    if before.mission_ids != after.mission_ids:
        raise ValueError("continuity requires the same mission IDs before and after")

    previous = set(before.operational_mission_ids)
    current = set(after.operational_mission_ids)
    outcomes = {
        (True, True): "continued",
        (True, False): "interrupted",
        (False, True): "restored",
        (False, False): "unavailable_throughout",
    }
    by_mission = {
        mission: outcomes[mission in previous, mission in current] for mission in before.mission_ids
    }
    counts = Counter(by_mission.values())
    return {
        "continued_mission_count": counts["continued"],
        "interrupted_mission_count": counts["interrupted"],
        "restored_mission_count": counts["restored"],
        "unavailable_throughout_mission_count": counts["unavailable_throughout"],
        "continuity_digest": canonical_sha256(by_mission),
    }
