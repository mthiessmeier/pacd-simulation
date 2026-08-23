"""Property checks for globally unique synthetic environment identifiers."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacd_sim.environment.model import (
    Asset,
    Credential,
    Dependency,
    EnvironmentState,
    Identity,
    MissionFunction,
    Service,
    Session,
)

_COLLECTION_WITH_DUPLICATE = st.sampled_from(
    ("identity", "session", "credential", "service", "mission", "dependency")
)


@pytest.mark.property
@given(_COLLECTION_WITH_DUPLICATE)
@settings(max_examples=20, deadline=None)
def test_entity_id_duplicated_across_collections_is_always_rejected(
    duplicate_collection: str,
) -> None:
    duplicate_id = "cross-collection-duplicate"
    identity_id = duplicate_id if duplicate_collection == "identity" else "identity-synthetic"
    mission_id = duplicate_id if duplicate_collection == "mission" else "mission-synthetic"
    service_id = duplicate_id if duplicate_collection == "service" else "service-synthetic"
    session_id = duplicate_id if duplicate_collection == "session" else "session-synthetic"
    credential_id = duplicate_id if duplicate_collection == "credential" else "credential-synthetic"
    dependency_id = duplicate_id if duplicate_collection == "dependency" else "dependency-synthetic"

    with pytest.raises(ValueError, match="unique"):
        EnvironmentState(
            assets=(Asset(id=duplicate_id),),
            identities=(Identity(id=identity_id, role="synthetic_user"),),
            sessions=(
                Session(
                    id=session_id,
                    identity_id=identity_id,
                    service_id=service_id,
                ),
            ),
            credentials=(Credential(id=credential_id, identity_id=identity_id),),
            services=(Service(id=service_id, mission_id=mission_id),),
            mission_functions=(MissionFunction(id=mission_id, criticality=1.0),),
            dependencies=(
                Dependency(
                    id=dependency_id,
                    upstream_id=identity_id,
                    downstream_id=service_id,
                ),
            ),
        )
