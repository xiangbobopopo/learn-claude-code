import threading

import dotenv
from anthropic import Anthropic
from pathlib import Path
import subprocess
import os
import re
import yaml
import time
import json
import threading
import uuid

dotenv.load_dotenv()
base_url = os.getenv("ANTHROPIC_BASE_URL")
model = os.getenv("MODEL_ID")

client = Anthropic(base_url=base_url)

WOKR_DIR = Path.cwd()
TRANSCRIPT_DIR = WOKR_DIR / ".transcript"
TASK_DIR = WOKR_DIR / '.tasks'


class SkillLoader:
    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skills = {}
        self._load_all()

    def _load_all(self):
        if not self.skill_dir.exists():
            return
        for f in sorted(self.skill_dir.rglob("SKILL.md")):
            meta, body = self._parse_frontmatter(f.read_text())
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    def _parse_frontmatter(self, text: str) -> tuple:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        return meta, match.group(2).strip()

    def get_description(self):
        if not self.skills:
            return "no skill find"
        result_list = [
            f"- {name}:{skill['meta'].get('description', 'No description')} [{skill['meta'].get('tags', '')}]" for
            name, skill in self.skills.items()]
        return "\n".join(result_list)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        return f"<skill name={skill['name']}>\n{skill['body']}\n</skill>"


SKILL = SkillLoader(Path.cwd().parent / "skills")
SYSTEM_MESSAGE = f"""
you are a joke teller， you always list todos before you start， answer the question finally directly and completely
Use load_skill to access specialized knowledge before tackling unfamiliar topics.

skills available:
{SKILL.skills}
"""
SUBAGENT_SYSTEM = "you are a secretory"
WORK_DIR = Path.cwd()
COMPACT_MESSAGE_KEEP = 3
THRESHHOLD = 20000


# compact context: messages

def estimate_token(messages: list) -> int:
    return len(str(messages)) // 4


def micro_compact(messages: list):
    """
    1,In place change.not on the message directly, but on a new list of reference to the content of the message.
    2,find the role of user.message_idx, content_idx, content.
    3,create a tool_use_id and tool_name map.

    """
    user_messages = []
    for msg_idx, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg["content"], list):
            for part_idx, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_use_result":
                    user_messages.append((msg_idx, part_idx, part))
    if len(user_messages) <= COMPACT_MESSAGE_KEEP:
        return messages
    # get the tool name an tool_use_id map
    tool_name_id_map = {}
    for msg in messages:
        if msg["role"] == "assistant":
            for block in msg["content"]:
                if block.type == "tool_use":
                    tool_name_id_map[block.tool_use_id] = block.name
    compact_list = user_messages[:-COMPACT_MESSAGE_KEEP]
    for _, _, part in compact_list:
        if not isinstance(part.content, str) or len(part.content) <= 100:
            continue
        tool_name = tool_name_id_map.get(part["tool_use_id"], "unknown")
        part["content"] = f"Previous: used {tool_name}"
    return messages


def auto_compact(messges: list) -> list:
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.json"
    with open(transcript_path, "w") as f:
        for msg in messges:
            f.write(json.dumps(msg, default=str) + "\n")
    conversion_text = json.dumps(messges, default=str)[-8000]
    response = client.messages.create(
        model=model,
        messages=conversion_text,
        max_tokens=2000
    )
    summary = next((block.text for block in response.content if block.type == "text"), "")
    if not summary:
        summary = "no summary generated"
    return [{"role": "user", "content": f"Conversation compressed. Transcript:{transcript_path} \n\n {summary}"}]


def sub_agent(prompt: str):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(30):
        response = client.messages.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            system=SUBAGENT_SYSTEM
        )
        if response.stop_reason != "tool_use":
            return
        messages.append({"role": "assistant", "context": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOLS_HANDLER.get(block.name)
                output = handler(block.input)
                results.append({"type": "too_result", "tool_use_id": block.id, "content": str(output)[:50]})
        messages.append({"role": "user", "content": results})
    return "".join([block for block in response.content if hasattr(block, "text")]) or "no summary"


class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list):
        validated = []
        in_progress_count = 0
        for idx, item in enumerate(items):
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(idx + 1)))
            if not text:
                raise ValueError(f"Item {item_id} have no text")
            if status not in ("pending", "completed", "in_progress"):
                raise ValueError(f"Invalid status:  {status}")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task should be in in_progress status at a time")
        self.items = validated
        return self.render()

    def render(self):
        lines = []
        if not self.items:
            return "no todos find"
        for item in self.items:
            marker = {"pending": "[ ]", "completed": "[x]", "in_progress": "[>]"}[item["status"]]
            lines.append(f"{marker} {item['id']}: {item['text']}")
        done_count = sum([1 for i in self.items if i["status"] == "completed"])
        lines.append(f"{done_count} out of {len(self.items)} tasks completed")
        return "\n".join(lines)


def run_bash(command: str):
    dangerour_act = ["rm -rf /"]
    if any(d in command for d in dangerour_act):
        return "Error: action not allowed"
    r = subprocess.run(
        command,
        cwd=WORK_DIR,
        shell=True,
        capture_output=True,
        text=True
    )
    out = (r.stdout + r.stderr).strip()
    return out


class BackgroundManager:
    def __init__(self):
        self.task = {}
        self._notification_queue = []
        self._lock = threading.Lock

    def run(self, command: str):
        task_id = str(uuid.uuid4())[:8]
        self.task[task_id] = {"status": "running", "result": "", "command": command}
        thread = threading.Thread(
            target=self._excecute, args=(task_id, command), daemon=True
        )
        thread.start()
        return f"Background task {task_id} running..."

    def _execute(self, task_id: str, command: str):
        try:
            r = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120
            )
            output = (r.stdout + r.stderr).strip()
            status = "complted"
        except subprocess.TimeoutExpired:
            output = "Error: timeout"
            status = "timeout"
        except Exception as e:
            output = f"Error: {e}"
            status = "error"
        self.task[task_id][status] = status
        self.task[task_id][output] = output
        with self._lock:
            self._notification_queue.append(
                {
                    "task_id": task_id,
                    "status": status,
                    "command": command,
                    "result": (output or "no output")[:500]
                }
            )

    def check_task(self, task_id: str = None):
        if task_id:
            task = self.task.get(task_id)
            return f"[{task['status']} {task['command']} \n {task.get('result', 'running')}]"
        else:
            lines = []
            for task_id, task in self.task.items():
                lines.append(f"{task_id} {task['status']} {task['command']} {task['result'][:100]}")
            return '\n'.join(lines) if lines else "no task running"


VALID_MESSAGE_TYPES = ["message"]


class MessageBus():
    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir,
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def send(self, sender: str, to: str, content: str, msg_type: str = "message", extra: dict = None):
        to_path = self.inbox_dir / f"{to}.jsonl"
        content = {
            "from": sender,
            'content': content,
            "type": msg_type
        }
        ...

    def read_inbox(self):
        ...


TOOLS = [
    {
        "name": "run_bash",
        "description": "run a shell command",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "todo",
        "description": "Update task list. Track progress on multi-step tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                            },
                        },
                        "required": ["id", "text", "status"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "load_skill",
        "description": "",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name to load"}
            },
            "required": ["name"]
        },

    },
    {
        "name": "compact",
        "description": "",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "what to preserve in the summary"
                }
            }
        }
    }
]

TODO = TodoManager()
BG_Task = BackgroundManager()

TOOLS_HANDLER = {
    "run_bash": lambda **kw: run_bash(kw["command"]),
    "todo": lambda **kw: TODO.update(kw["items"]),
    "load_skill": lambda **kw: SKILL.get_content(kw["name"]),
    "task_create": lambda **kw: TaskManager.create_task(kw["subject"], kw.get("description", "")),
    "task_update": lambda **kw: TaskManager.update_task(kw["task_id"], kw[""]),
    "background_run": lambda **kw: BG_Task.run(kw["command"]),
    "check_background": lambda **kw: BG_Task.check_task(kw.get("task_id", None))
}


def agent_loop(messages: list):
    while True:
        micro_compact(messages)
        if estimate_token(messages) > THRESHHOLD:
            messages[:] = auto_compact(messages)

        response = client.messages.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            tools=TOOLS,
            system=SYSTEM_MESSAGE
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        mannual_compact = False
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "compact":
                    mannual_compact = True
                    output = "Compressing..."
                else:
                    handler = TOOLS_HANDLER.get(block.name)
                    output = handler(**block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        if mannual_compact:
            auto_compact(messages)
            messages[:] = auto_compact(messages)
            return


def main():
    history = []
    while True:
        # query = input("\033[36ms02 >> \033[0m")
        query = "给我讲个猫有关的笑话"
        if query in ["q", "quit", ""]:
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        result = history[-1]["content"]
        if isinstance(result, list):
            for item in result:
                if hasattr(item, "text"):
                    print(item.text)


class TaskManager():
    def __init__(self):
        self.task_dir = TASK_DIR
        self.task_dir.mkdir(exist_ok=True)

    def _max_num(self):
        return max([int(i.stem.split("_")[1]) for i in self.task_dir.rglob("task_*.json")])

    def _save_task(self, task: dict):
        path = self.task_dir / f"task_{task.get('id')}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False))

    def create_task(self, subject: str, description: str):
        task_no = self._max_num() + 1
        task = {
            "id": task_no,
            "subject": subject,
            "description": description,
            "status": "pending",
            "blocked_by": [],
            "owner": ""
        }
        self._save_task(task)

    def _load(self, task_id: int) -> dict:
        path = self.task_dir / f"task_{task_id}.json"
        return json.loads(path.read_text())

    def update_task(self, task_id: int, add_block_by: list[int], remove_block_by: list[int], status: str):
        task = self._load(task_id)
        if status and status not in ["pending", "completed", "in_progress"]:
            raise ValueError(f"invalid status: {status}")
        if status == "completed":
            self._clear_dependency(task_id)
        task["status"] = status
        if add_block_by:
            task["block_by"] = list(set(task["blocked_by"] + add_block_by))
        if remove_block_by:
            task["block_by"] = [i for i in task["blocked_by"] if i not in remove_block_by]
        self._save_task(task)

    def _clear_dependency(self, task_id):
        for file in self.task_dir.rglob("task_*.json"):
            task = json.loads(file)
            if task_id in task["blocked_by"]:
                task["blocked_by"].remove(task_id)
                self._save_task(task)

    def list_task(self) -> dict:
        tasks = [self._load(item) for item in self.task_dir.rglob("task_*.json")]
        if not tasks:
            return "no task find"
        lines = []
        for t in tasks:
            marker = {"pending": "[]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            owner = f"@{tasks.get('owner', '')}"
            lines.append(f"{marker} # {t['id']} {t['subject']} {owner}")
        return "\n".join(lines)

    def get(self, id: int):
        return json.dumps(self._load(id), indent=2, ensure_ascii=False)


# agent teams.1,create teammate. 2, teammate communication.
VALID_MESSAGES = ["message", "broad_cast"]


class MessageBus:
    def __init__(self):
        self.inbox_dir = WOKR_DIR / ".team" / ".inbox"
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def send_message(self, sender: str, receiver: str, message: str):
        ...

    def read_message(self, receiver: str):
        ...


class TeamManager(object):
    def __init__(self, team_name: str):
        self.team_dir = WORK_DIR / ".team"
        self.config_path = self.team_dir / ".config.txt"
        self.team_dir.mkdir(parents=True, exist_ok=True)
        self._create_team(team_name)
        self.config = self._load_config()
        self.threads={}

    def _load_config(self):
        return json.loads(self.config_path.read_text())

    def _create_team(self, team_name: str):
        team = {
            "name": team_name,
            "description": "",
            "members": [],
            "create_time": time.time()
        }
        with open(self.config, 'w') as f:
            f.write(json.dumps(team, ensure_ascii=False, indent=2))

    def find_teammate(self, name):
        for item in self.config["members"]:
            return item[name]

    def spawn_teammate(self, name: str, role: str, prompt: str):
        teammate = self.find_teammate("name")
        if teammate:
            if teammate["status"] not in ["idle", "shut_down"]:
                return f"Error: {name} is currently in {teammate['status']}"
            teammate['status'] = "working"
            teammate['role'] = role
        else:
            teammate = {
                "name": name,
                "role": role,
                "status": "working"
            }
            self.config["members"].append(teammate)
            self._save_config()
        thread=threading.Thread(
            target=self._teammate_loop(),args=(name,role,prompt),
            daemon=True
        )
        self.threads[name]=thread
        thread.start()


    def _save_config(self):
        self.config_path.write_text(json.dumps(self.config,indent=2,ensure_ascii=False))

        
    def _teammate_loop(self,name,role, prompt: str):
        system_message=f"""
        your name is {name} and you are a {role}, you work at {WORK_DIR} 
"""
        messages = [{"role": "user", "content": prompt}]
        for _ in range(50):
            response = client.messages.create(
                model=model,
                system=system_message,
                messages=messages,
                tools=TOOLS,
                max_tokens=2000
            )
            result = []
            if response.stop_reason != "tool_use":
                return

            for block in response.content:
                if block.type=="tool_use":
                    handler=TOOLS_HANDLER.get(block.name)


if __name__ == "__main__":
    msg_bus = MessageBus()
    team_manager = TeamManager("development_department")
