import json
import os
from typing import List, Optional

from openai import OpenAI

from client import SreCopilotEnv
from models import SreAction


# === Required env variables ===
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))

SYSTEM_PROMPT = """You are an expert SRE controlling an incident response environment.
Respond with exactly one valid JSON object:
{
  "action_type": "one of allowed actions",
  "target_service": "service name or empty string",
  "parameter": "optional parameter",
  "reason": "brief reason"
}
Return only JSON."""


# === Logging ===
def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None):
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}",
        flush=True
    )


def log_end(success: bool, steps: int, rewards: List[float]):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}", flush=True)


# === Parse action ===
def _parse_action(content: str) -> SreAction:
    try:
        data = json.loads(content)
        return SreAction(
            action_type=str(data.get("action_type", "check_status")).strip(),
            target_service=str(data.get("target_service", "")).strip(),
            parameter=str(data.get("parameter", "")).strip(),
            reason=str(data.get("reason", "")).strip(),
        )
    except Exception:
        return SreAction(action_type="check_status", reason="parse fallback")


def main():
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is required for inference as per submission requirements")

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    base_url = os.getenv("OPENENV_BASE_URL", "http://localhost:8000")
    print(f"[INFO] Using OpenEnv base URL: {base_url}", flush=True)

    env = SreCopilotEnv(base_url=base_url)

    rewards: List[float] = []
    steps_taken = 0
    success = False

    log_start(task="sre-incident-response", env="sre-copilot-env", model=MODEL_NAME)

    try:
        result = env.reset()
        history: List[str] = []

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            obs = result.observation

            obs_dict = {
                "current_alert": getattr(obs, "current_alert", {}),
                "system_snapshot": getattr(obs, "system_snapshot", {}),
                "feedback": getattr(obs, "feedback", ""),
            }

            user_prompt = (
                f"Step: {step}\n"
                f"Alert: {json.dumps(obs_dict['current_alert'])}\n"
                f"Snapshot: {json.dumps(obs_dict['system_snapshot'])}\n"
                f"Feedback: {obs_dict['feedback']}\n"
                f"History: {' | '.join(history[-3:]) or 'none'}\n"
                "Reply with only JSON."
            )

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=150,
            )

            content = (response.choices[0].message.content or "").strip()
            action = _parse_action(content)

            result = env.step(action)

            reward = float(result.reward or 0.0)
            done = result.done

            action_str = f"{action.action_type}(svc={action.target_service})"

            log_step(step=step, action=action_str, reward=reward, done=done)

            rewards.append(reward)
            steps_taken = step
            history.append(action_str)

            if done:
                success = True
                break

    except Exception as e:
        print(f"[ERROR] {str(e)}", flush=True)
        success = False

    finally:
        try:
            env.close()
        except:
            pass

        log_end(success=success, steps=steps_taken, rewards=rewards)


if __name__ == "__main__":
    main()