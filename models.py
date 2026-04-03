from typing import Dict, List
from pydantic import Field
from openenv.core.env_server import Action, Observation, State

class SreAction(Action):
    action_type: str                    # "check_metrics", "check_logs", "restart", "scale", "rollback", "declare_incident_resolved", "escalate"
    target_service: str = ""
    parameter: str = ""                 # e.g. "replicas=3" or service name
    reason: str = ""

class SreObservation(Observation):
    current_alert: Dict
    system_snapshot: Dict               # metrics + logs summary
    feedback: str = ""
    reward: bool | int | float | None = 0.0
    done: bool = False
    info: Dict = Field(default_factory=dict)

class SreState(State):
    step_count: int = 0
    incident_id: int = 0
    actions_taken: List[str] = Field(default_factory=list)
    checked_services: List[str] = Field(default_factory=list)
    services_down: List[str] = Field(default_factory=list)
    diagnosis: str = "unknown"
    root_cause_identified: bool = False
    root_cause_fixed: bool = False
    correct_diagnoses: int = 0
    mttr_steps: int = 0                 # mean time to recovery in steps


SreCopilotAction = SreAction
SreCopilotObservation = SreObservation