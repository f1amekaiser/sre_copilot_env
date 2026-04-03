import uuid
from typing import Dict, List
from openenv.core.env_server import Environment

try:
    from ..models import SreAction, SreObservation, SreState
except ImportError:
    from models import SreAction, SreObservation, SreState

class SreCopilotEnvironment(Environment):
    def __init__(self):
        super().__init__()
        self._state = SreState()
        self.max_steps = 8
        self.incidents = [
            # Task 1 - Easy
            {
                "id": 0,
                "title": "High CPU on web-service",
                "difficulty": "easy",
                "root_service": "web-service",
                "root_cause": "cpu_spike",
                "symptom_service": "web-service",
                "services": ["web-service"],
                "services_down": ["web-service"],
                "dependencies": {"web-service": []},
                "valid_fixes": [("scale", "web-service")],
            },
            # Task 2 - Medium
            {
                "id": 1,
                "title": "Database connection timeout",
                "difficulty": "medium",
                "root_service": "db-service",
                "root_cause": "database_failure",
                "symptom_service": "web-service",
                "services": ["db-service", "web-service"],
                "services_down": ["db-service", "web-service"],
                "dependencies": {"web-service": ["db-service"], "db-service": []},
                "valid_fixes": [("restart", "db-service")],
            },
            # Task 3 - Hard
            {
                "id": 2,
                "title": "Cascading outage - misleading alert",
                "difficulty": "hard",
                "root_service": "db-service",
                "root_cause": "database_failure",
                "symptom_service": "auth-service",
                "services": ["db-service", "auth-service", "api-gateway", "web-service"],
                "services_down": ["db-service", "auth-service", "api-gateway", "web-service"],
                "dependencies": {
                    "api-gateway": ["auth-service"],
                    "auth-service": ["db-service"],
                    "web-service": ["db-service"],
                    "db-service": [],
                },
                "valid_fixes": [("restart", "db-service")],
            }
        ]
        self.current_task = -1
        self.incident = None
        self.checked_services = set()
        self.service_status: Dict[str, str] = {}
        self.root_cause_identified = False
        self.root_cause_fixed = False
        self.current_diagnosis = "unknown"

    def _set_incident(self, incident: Dict):
        self.incident = incident
        self.checked_services = set()
        self.root_cause_identified = False
        self.root_cause_fixed = False
        self.current_diagnosis = "unknown"
        self.service_status = {service: "healthy" for service in incident["services"]}
        for service in incident["services_down"]:
            self.service_status[service] = "down"

    def _sync_state(self):
        self._state.checked_services = sorted(self.checked_services)
        self._state.services_down = sorted([name for name, status in self.service_status.items() if status != "healthy"])
        self._state.diagnosis = self.current_diagnosis
        self._state.root_cause_identified = self.root_cause_identified
        self._state.root_cause_fixed = self.root_cause_fixed

    def _is_valid_fix(self, action_type: str, target_service: str) -> bool:
        incident = self.incident if self.incident is not None else self.incidents[0]
        for valid_action, valid_target in incident["valid_fixes"]:
            if action_type == valid_action and target_service == valid_target:
                return True
        return False

    def _resolve_root_cause(self):
        incident = self.incident if self.incident is not None else self.incidents[0]
        root_service = incident["root_service"]
        self.service_status[root_service] = "healthy"
        for service in incident["services"]:
            self.service_status[service] = "healthy"
        self.root_cause_fixed = True

    def _build_info(self, reasoning: str, action_effect: str) -> Dict:
        return {
            "reasoning": reasoning,
            "diagnosis": self.current_diagnosis,
            "action_effect": action_effect,
        }

    def _normalize_action(self, action_type: str) -> str:
        mapping = {
            "check_status": "check",
            "check_metrics": "check",
            "check_logs": "check",
            "restart_service": "restart",
            "scale_service": "scale",
        }
        key = (action_type or "").strip().lower()
        return mapping.get(key, key)

    def _handle_check(self, target_service: str, incident: Dict) -> tuple[float, str, str]:
        self.checked_services.add(target_service)

        reward = 0.1
        reasoning = f"Checked status of {target_service}."
        action_effect = "status_checked"

        if target_service == incident["root_service"] and not self.root_cause_identified:
            self.root_cause_identified = True
            self.current_diagnosis = incident["root_cause"]
            self._state.correct_diagnoses += 1
            reward += 0.2
            feedback = f"Checked status of {target_service}. Root cause signal found."
        elif target_service == incident["root_service"]:
            feedback = f"Checked status of {target_service}. Root issue already identified."
        elif target_service in incident["dependencies"].get(incident["symptom_service"], []):
            feedback = f"Checked status of {target_service}. It is in the dependency path."
        else:
            feedback = f"Checked status of {target_service}."

        return reward, feedback, reasoning, action_effect

    def _handle_fix(self, action_type: str, target_service: str, incident: Dict) -> tuple[float, str, str, str]:
        if self._is_valid_fix(action_type, target_service):
            self._resolve_root_cause()
            self.current_diagnosis = incident["root_cause"]
            reward = 1.0
            feedback = "Root cause resolved successfully"
            reasoning = "Remediation matched the incident root cause."
            action_effect = "root_cause_resolved"
            return reward, feedback, reasoning, action_effect

        reward = -0.2
        if target_service != incident["root_service"]:
            feedback = f"{target_service} is not the root cause"
            reasoning = "Fix attempted on a non-root service while upstream issue remains."
            action_effect = "wrong_target"
        else:
            feedback = "Remediation action does not match required fix for root cause"
            reasoning = "Correct target service but incorrect remediation type."
            action_effect = "wrong_fix_type"

        return reward, feedback, reasoning, action_effect

    def _invalid_action(self, normalized_action: str) -> tuple[float, str, str, str]:
        return (
            -0.2,
            f"Unsupported action: {normalized_action}",
            "Action type is outside environment action space.",
            "invalid_action",
        )

    def reset(self, seed=None, episode_id=None, **kwargs) -> SreObservation:
        self._state = SreState(episode_id=episode_id or str(uuid.uuid4()))
        self.current_task = (self.current_task + 1) % len(self.incidents)
        self._set_incident(self.incidents[self.current_task])
        incident = self.incident if self.incident is not None else self.incidents[0]
        self._state.incident_id = incident["id"]
        self._sync_state()
        return self._get_observation()

    def _get_observation(self) -> SreObservation:
        if self.incident is None:
            self._set_incident(self.incidents[0])
        incident = self.incident if self.incident is not None else self.incidents[0]

        obs_payload = {
            "current_alert": {
                "title": incident["title"],
                "severity": "critical" if incident["difficulty"] == "hard" else "high",
                "service": incident["symptom_service"],
                "timestamp": "now",
            },
            "system_snapshot": {
                "metrics": {
                    service: (
                        {"status": self.service_status.get(service, "unknown"), "latency": "1200ms"}
                        if self.service_status.get(service) != "healthy"
                        else {"status": "healthy", "latency": "120ms"}
                    )
                    for service in incident["services"]
                },
                "logs": {
                    "root_service": incident["root_service"],
                    "summary": "Upstream dependency failures detected" if incident["difficulty"] == "hard" else "Service instability detected",
                },
                "dependencies": incident["dependencies"],
            },
            "feedback": "",
            "reward": 0.0,
            "done": False,
            "info": self._build_info("Initial observation generated.", "none"),
        }
        return SreObservation.model_validate(obs_payload)

    def step(self, action: SreAction, timeout_s=None, **kwargs) -> SreObservation:
        if self.incident is None:
            self._set_incident(self.incidents[0])
        incident = self.incident if self.incident is not None else self.incidents[0]

        self._state.step_count += 1
        action_type = (action.action_type or "").strip()
        normalized_action = self._normalize_action(action_type)
        self._state.actions_taken.append(normalized_action)
        target_service = (action.target_service or incident["symptom_service"]).strip()

        reward = 0.0
        feedback = ""
        reasoning = ""
        action_effect = "none"

        if normalized_action == "check":
            reward, feedback, reasoning, action_effect = self._handle_check(target_service, incident)

        elif normalized_action in ["restart", "scale", "rollback"]:
            reward, feedback, reasoning, action_effect = self._handle_fix(normalized_action, target_service, incident)

        elif normalized_action == "declare_incident_resolved":
            if self.root_cause_fixed:
                reward += 0.2
                feedback = "Incident correctly marked resolved."
                reasoning = "Resolution declaration matches system state."
                action_effect = "resolution_confirmed"
            else:
                reward -= 0.2
                feedback = "Incident declared resolved before root cause fix."
                reasoning = "Resolution declaration contradicted system state."
                action_effect = "false_resolution"

        elif normalized_action == "escalate":
            reward += 0.0
            feedback = "Escalation recorded; continue triage in parallel."
            reasoning = "Escalation is neutral unless paired with diagnosis/remediation."
            action_effect = "escalated"

        else:
            reward, feedback, reasoning, action_effect = self._invalid_action(normalized_action)

        done = False
        if self.root_cause_fixed:
            done = True
            self._state.mttr_steps = self._state.step_count
        elif self._state.step_count >= self.max_steps:
            done = True
            feedback = f"{feedback} Max steps reached before full resolution.".strip()
            action_effect = "max_steps_reached"

        self._sync_state()

        obs_payload = {
            "current_alert": {} if done else self._get_observation().current_alert,
            "system_snapshot": {} if done else self._get_observation().system_snapshot,
            "feedback": feedback,
            "reward": reward,
            "done": done,
            "info": self._build_info(reasoning, action_effect),
        }

        return SreObservation.model_validate(obs_payload)

    @property
    def state(self) -> SreState:
        return self._state

    def grade_task(self, task_id: int) -> float:
        """Returns score 0.0–1.0 for each task"""
        if task_id >= len(self.incidents):
            return 0.0
        score = 0.0
        if self._state.root_cause_fixed:
            score += 0.7
        if self._state.root_cause_identified:
            score += 0.2
        if self._state.step_count <= self.max_steps:
            score += 0.1
        return min(1.0, score)