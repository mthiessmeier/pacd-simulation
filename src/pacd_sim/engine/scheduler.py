"""Small deterministic SimPy scheduler for synthetic diagnostic events."""

from collections.abc import Generator, Iterable

import simpy

from pacd_sim.schema import ConsequentialRecord, NonNegativeFloat, StableId


class ScheduledEvent(ConsequentialRecord):
    """A synthetic event ordered by tick, priority, and stable identifier."""

    kind: StableId
    priority: int = 0
    identity_id: StableId | None = None
    target_id: StableId | None = None
    magnitude: NonNegativeFloat = 1.0


class DeterministicScheduler:
    """SimPy-backed scheduler whose output does not depend on insertion order."""

    def __init__(self, events: Iterable[ScheduledEvent] = ()) -> None:
        self._environment = simpy.Environment()
        self._pending: dict[str, ScheduledEvent] = {}
        self._current_tick = 0
        for event in events:
            self.schedule(event)

    @property
    def current_tick(self) -> int:
        return self._current_tick

    @property
    def environment(self) -> simpy.Environment:
        """Expose the local SimPy clock for harness inspection only."""

        return self._environment

    def schedule(self, event: ScheduledEvent) -> None:
        """Schedule an event, rejecting duplicate IDs and past events."""

        if event.id in self._pending:
            raise ValueError(f"duplicate event id: {event.id}")
        if event.tick < self._current_tick:
            raise ValueError("cannot schedule an event in the past")
        self._pending[event.id] = event

    def pending(self) -> tuple[ScheduledEvent, ...]:
        """Return pending events in deterministic execution order."""

        return tuple(
            sorted(
                self._pending.values(),
                key=lambda item: (item.tick, item.priority, item.id),
            )
        )

    def _deliver(
        self,
        event: ScheduledEvent,
        emitted: list[ScheduledEvent],
    ) -> Generator[simpy.events.Event]:
        delay = event.tick - int(self._environment.now)
        if delay < 0:
            raise ValueError("event tick precedes the SimPy clock")
        yield self._environment.timeout(delay)
        emitted.append(event)

    def run(self, until_tick: int | None = None) -> tuple[ScheduledEvent, ...]:
        """Drain events through ``until_tick`` (inclusive), or all events if omitted."""

        if until_tick is not None and until_tick < self._current_tick:
            raise ValueError("until_tick precedes the scheduler's current tick")
        due = tuple(
            event for event in self.pending() if until_tick is None or event.tick <= until_tick
        )
        emitted: list[ScheduledEvent] = []
        for event in due:
            self._pending.pop(event.id)
            self._environment.process(self._deliver(event, emitted))
        if due:
            self._environment.run()
            emitted.sort(key=lambda item: (item.tick, item.priority, item.id))
            self._current_tick = due[-1].tick
        if until_tick is not None:
            self._current_tick = until_tick
        return tuple(emitted)
