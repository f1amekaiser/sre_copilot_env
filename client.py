"""SRE Copilot Environment Client."""

from typing import Dict

from openenv.core.client_types import StepResult
from openenv.core import EnvClient

# Import our models
try:
    from .models import SreAction, SreObservation, SreState
except ImportError:
    from models import SreAction, SreObservation, SreState


class SreCopilotEnv(EnvClient[SreAction, SreObservation, SreState]):
    """
    Client for the Autonomous Incident Response Agent (SRE Copilot) Environment.
    """

    def _step_payload(self, action: SreAction) -> Dict:
        """
        Convert SreAction to JSON payload for the step endpoint.
        """
        return {
            "action_type": action.action_type,
            "target_service": action.target_service,
            "parameter": action.parameter,
            "reason": action.reason,
        }

    def _parse_result(self, payload: Dict) -> StepResult[SreObservation]:
        """
        Parse server response into StepResult[SreObservation].
        """
        obs_data = payload.get("observation", {}) or {}

        observation = SreObservation(
            current_alert=obs_data.get("current_alert", {}),
            system_snapshot=obs_data.get("system_snapshot", {}),
            feedback=obs_data.get("feedback", ""),
            reward=obs_data.get("reward", 0.0),
            done=obs_data.get("done", False),
            info=obs_data.get("info", {}) or {},
        )

        raw_reward = payload.get("reward", obs_data.get("reward"))
        reward = 0.0 if raw_reward is None else float(raw_reward)

        raw_done = payload.get("done")
        done = bool(raw_done) if raw_done is not None else bool(observation.done)

        return StepResult(
            observation=observation,
            reward=reward,
            done=done,
        )

    def _parse_state(self, payload: Dict) -> SreState:
        """
        Parse server response into State object.
        """
        return SreState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )