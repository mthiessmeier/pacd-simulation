"""Immutable, synthetic-only enterprise and mission state models."""

from typing import Self

import networkx as nx
from pydantic import field_validator, model_validator

from pacd_sim.schema import (
    ConsequentialRecord,
    NonNegativeFloat,
    Probability,
    StableId,
)


class Asset(ConsequentialRecord):
    """Synthetic asset represented inside the simulator."""

    kind: StableId = "synthetic_asset"
    criticality: Probability = 0.0
    available: bool = True
    compromised: bool = False


class Identity(ConsequentialRecord):
    """Synthetic identity with only simulation state."""

    role: StableId
    enabled: bool = True


class Session(ConsequentialRecord):
    """Synthetic identity session attached to one synthetic service."""

    identity_id: StableId
    service_id: StableId
    active: bool = True
    isolated: bool = False


class Credential(ConsequentialRecord):
    """Opaque synthetic credential state; no credential material is stored."""

    identity_id: StableId
    active: bool = True
    exposed: bool = False


class Service(ConsequentialRecord):
    """Synthetic service supporting a mission function."""

    mission_id: StableId
    available: bool = True


class MissionFunction(ConsequentialRecord):
    """Synthetic mission function and its bounded criticality."""

    criticality: Probability
    operational: bool = True


class Dependency(ConsequentialRecord):
    """Directed dependency between two synthetic entities."""

    upstream_id: StableId
    downstream_id: StableId
    weight: NonNegativeFloat = 1.0


class EnvironmentState(ConsequentialRecord):
    """Complete immutable state used by the diagnostic broker."""

    id: StableId = "environment-synthetic-root"
    assets: tuple[Asset, ...] = ()
    identities: tuple[Identity, ...] = ()
    sessions: tuple[Session, ...] = ()
    credentials: tuple[Credential, ...] = ()
    services: tuple[Service, ...] = ()
    mission_functions: tuple[MissionFunction, ...] = ()
    dependencies: tuple[Dependency, ...] = ()

    @field_validator("assets")
    @classmethod
    def _sort_assets(cls, value: tuple[Asset, ...]) -> tuple[Asset, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @field_validator("identities")
    @classmethod
    def _sort_identities(cls, value: tuple[Identity, ...]) -> tuple[Identity, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @field_validator("sessions")
    @classmethod
    def _sort_sessions(cls, value: tuple[Session, ...]) -> tuple[Session, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @field_validator("credentials")
    @classmethod
    def _sort_credentials(cls, value: tuple[Credential, ...]) -> tuple[Credential, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @field_validator("services")
    @classmethod
    def _sort_services(cls, value: tuple[Service, ...]) -> tuple[Service, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @field_validator("mission_functions")
    @classmethod
    def _sort_missions(cls, value: tuple[MissionFunction, ...]) -> tuple[MissionFunction, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @field_validator("dependencies")
    @classmethod
    def _sort_dependencies(cls, value: tuple[Dependency, ...]) -> tuple[Dependency, ...]:
        return tuple(sorted(value, key=lambda item: item.id))

    @model_validator(mode="after")
    def _validate_graph(self) -> Self:
        records = (
            *self.assets,
            *self.identities,
            *self.sessions,
            *self.credentials,
            *self.services,
            *self.mission_functions,
            *self.dependencies,
        )
        ids = tuple(item.id for item in records)
        if len(ids) != len(set(ids)):
            raise ValueError("entity IDs must be globally unique across all collections")
        for record in records:
            if record.configuration_version != self.configuration_version:
                raise ValueError("entity configuration version must match environment state")
            if record.schema_version != self.schema_version:
                raise ValueError("entity schema version must match environment state")

        identity_ids = {item.id for item in self.identities}
        service_ids = {item.id for item in self.services}
        mission_ids = {item.id for item in self.mission_functions}
        for session in self.sessions:
            if session.identity_id not in identity_ids:
                raise ValueError(f"session references unknown identity: {session.identity_id}")
            if session.service_id not in service_ids:
                raise ValueError(f"session references unknown service: {session.service_id}")
        for credential in self.credentials:
            if credential.identity_id not in identity_ids:
                raise ValueError(
                    f"credential references unknown identity: {credential.identity_id}"
                )
        for service in self.services:
            if service.mission_id not in mission_ids:
                raise ValueError(f"service references unknown mission: {service.mission_id}")

        entity_ids = set().union(
            {item.id for item in self.assets},
            identity_ids,
            {item.id for item in self.sessions},
            {item.id for item in self.credentials},
            service_ids,
            mission_ids,
        )
        for dependency in self.dependencies:
            if dependency.upstream_id not in entity_ids:
                raise ValueError(
                    f"dependency references unknown upstream entity: {dependency.upstream_id}"
                )
            if dependency.downstream_id not in entity_ids:
                raise ValueError(
                    f"dependency references unknown downstream entity: {dependency.downstream_id}"
                )
        return self

    def get_session(self, session_id: str) -> Session | None:
        """Look up a session without exposing mutable state."""

        return next((item for item in self.sessions if item.id == session_id), None)

    def isolate_session(self, session_id: str) -> Self:
        """Return a new state with one known session safely isolated."""

        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"unknown synthetic session: {session_id}")
        replacement = session.model_copy(update={"active": False, "isolated": True})
        sessions = tuple(replacement if item.id == session_id else item for item in self.sessions)
        return self._revalidated(sessions=sessions)

    def restore_session(self, session: Session) -> Self:
        """Return a new state with a prior version of an existing session restored."""

        existing = self.get_session(session.id)
        if existing is None:
            raise KeyError(f"unknown synthetic session: {session.id}")
        if (
            session.identity_id != existing.identity_id
            or session.service_id != existing.service_id
            or session.configuration_version != self.configuration_version
            or session.schema_version != self.schema_version
            or session.source != existing.source
            or session.tick != existing.tick
        ):
            raise ValueError("replacement session changes immutable session context")
        sessions = tuple(session if item.id == session.id else item for item in self.sessions)
        return self._revalidated(sessions=sessions)

    def at_tick(self, tick: int) -> Self:
        """Return a state snapshot advanced to a nondecreasing simulation tick."""

        if isinstance(tick, bool) or not isinstance(tick, int) or tick < self.tick:
            raise ValueError("tick must be a nondecreasing integer")
        return self._revalidated(tick=tick)

    def _revalidated(
        self,
        *,
        sessions: tuple[Session, ...] | None = None,
        tick: int | None = None,
    ) -> Self:
        """Rebuild through Pydantic so relationship and provenance invariants rerun."""

        return type(self)(
            id=self.id,
            schema_version=self.schema_version,
            configuration_version=self.configuration_version,
            source=self.source,
            tick=self.tick if tick is None else tick,
            assets=self.assets,
            identities=self.identities,
            sessions=self.sessions if sessions is None else sessions,
            credentials=self.credentials,
            services=self.services,
            mission_functions=self.mission_functions,
            dependencies=self.dependencies,
        )

    def to_graph(self, *, multigraph: bool = False) -> nx.DiGraph:
        """Build a detached view. A multigraph retains every parallel relationship."""

        return environment_to_graph(self, multigraph=multigraph)


def environment_to_graph(state: EnvironmentState, *, multigraph: bool = False) -> nx.DiGraph:
    """Derive a stable directed graph from immutable synthetic environment state."""

    graph = nx.MultiDiGraph() if multigraph else nx.DiGraph()
    for asset in state.assets:
        graph.add_node(
            asset.id,
            entity_type="asset",
            available=asset.available,
            compromised=asset.compromised,
            criticality=asset.criticality,
        )
    for identity in state.identities:
        graph.add_node(
            identity.id,
            entity_type="identity",
            enabled=identity.enabled,
            role=identity.role,
        )
    for session in state.sessions:
        graph.add_node(
            session.id,
            entity_type="session",
            active=session.active,
            isolated=session.isolated,
        )
    for credential in state.credentials:
        graph.add_node(
            credential.id,
            entity_type="credential",
            active=credential.active,
            exposed=credential.exposed,
        )
        graph.add_edge(credential.id, credential.identity_id, relationship="authenticates")
    for service in state.services:
        graph.add_node(
            service.id,
            entity_type="service",
            available=service.available,
        )
        graph.add_edge(service.id, service.mission_id, relationship="supports_mission")
    for mission in state.mission_functions:
        graph.add_node(
            mission.id,
            entity_type="mission_function",
            criticality=mission.criticality,
            operational=mission.operational,
        )
    for session in state.sessions:
        graph.add_edge(session.identity_id, session.id, relationship="owns_session")
        graph.add_edge(session.id, session.service_id, relationship="uses_service")
    for dependency in state.dependencies:
        graph.add_edge(
            dependency.upstream_id,
            dependency.downstream_id,
            relationship="depends_on",
            weight=dependency.weight,
            dependency_id=dependency.id,
        )
    return graph
