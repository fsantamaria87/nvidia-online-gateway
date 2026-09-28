from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

MEMORY_ROOT = Path('/data/oauth/project_memory')
SOURCE_TITLE = 'PROJECT_MEMORY.md — Activity & Decision Log'

SIGNIFICANT_TERMS = {
    'lkg', 'last_known_good', 'release', 'released', 'baseline', 'validated',
    'validation', 'pass', 'fail', 'failed', 'bug', 'fix', 'fixed', 'repair',
    'architecture', 'decision', 'rule', 'governance', 'deploy', 'deployment',
    'migration', 'regression', 'root cause', 'workaround', 'source of truth',
    'template lock', 'milestone', 'production', 'approved', 'rejected',
}

SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_ -]?key|password|passwd|oauth[_ -]?token|master[_ -]?token|bearer[_ -]?token|client[_ -]?secret)\s*[:=]'),
    re.compile(r'(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]


def _clean(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, (list, tuple, set)):
        return ', '.join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def _contains_secret(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)


def _fingerprint(project: str, event: dict[str, Any]) -> str:
    canonical = '|'.join([
        project.strip().lower(),
        _clean(event.get('activity')).lower(),
        _clean(event.get('decision')).lower(),
        _clean(event.get('result')).lower(),
    ])
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]


def _score(event: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    decision = _clean(event.get('decision'))
    result = _clean(event.get('result'))
    evidence = _clean(event.get('evidence'))
    next_step = _clean(event.get('next_step'))
    activity = _clean(event.get('activity'))
    tags = _clean(event.get('tags'))
    joined = ' '.join([activity, decision, result, evidence, next_step, tags]).lower()

    if decision:
        score += 3; reasons.append('decision')
    if result:
        score += 2; reasons.append('result')
    if evidence:
        score += 2; reasons.append('evidence')
    if next_step:
        score += 1; reasons.append('next_step')
    hits = sorted(term for term in SIGNIFICANT_TERMS if term in joined)
    if hits:
        score += min(3, len(hits)); reasons.append('significant_terms:' + ','.join(hits[:5]))
    if len(activity) >= 80:
        score += 1; reasons.append('substantive_activity')
    return score, reasons


def _paths(project: str) -> tuple[Path, Path]:
    safe = re.sub(r'[^a-zA-Z0-9._-]+', '-', project.strip()).strip('-') or 'project'
    folder = MEMORY_ROOT / safe
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'events.jsonl', folder / 'PROJECT_MEMORY.md'


def _load_events(project: str) -> list[dict[str, Any]]:
    jsonl, _ = _paths(project)
    if not jsonl.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in jsonl.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            continue
    return rows


def _render(project: str, events: list[dict[str, Any]]) -> str:
    lines = [
        f'# PROJECT MEMORY — {project}',
        '',
        'Curated operational memory. Source-of-truth documents and project constitutions retain precedence.',
        'Entries capture material activity, decisions, validated outcomes, evidence and next steps.',
        '',
    ]
    for item in events:
        lines.extend([
            f"## {item['timestamp']} — {item.get('title') or 'Material project event'}",
            '',
            f"**Activity:** {_clean(item.get('activity')) or '—'}",
            '',
            f"**Decision:** {_clean(item.get('decision')) or '—'}",
            '',
            f"**Result:** {_clean(item.get('result')) or '—'}",
            '',
            f"**Next step:** {_clean(item.get('next_step')) or '—'}",
            '',
            f"**Evidence:** {_clean(item.get('evidence')) or '—'}",
            '',
            f"**Tags:** {_clean(item.get('tags')) or '—'}",
            '',
            f"**Memory score:** {item.get('score', 0)}/10",
            '',
        ])
    return '\n'.join(lines).strip() + '\n'


async def _sync_source(hub, project: str, markdown: str) -> dict[str, Any]:
    async with hub._client() as client:
        nb, _ = await hub._resolve_project(client, project)
        sources = await client.sources.list(nb.id)
        matches = [s for s in sources if str(getattr(s, 'title', '')).strip().casefold() == SOURCE_TITLE.casefold()]
        for source in matches:
            await client.sources.delete(nb.id, source.id)
        created = await client.sources.add_text(nb.id, SOURCE_TITLE, markdown)
        return {
            'notebook_id': nb.id,
            'notebook_title': nb.title,
            'replaced_sources': len(matches),
            'source_id': getattr(created, 'id', None),
            'source_title': SOURCE_TITLE,
        }


def register_memory_tool(mcp, hub) -> None:
    @mcp.tool
    async def project_memory(
        project: str,
        action: Literal['consider', 'force', 'status'] = 'consider',
        title: str | None = None,
        activity: str | None = None,
        decision: str | None = None,
        result: str | None = None,
        next_step: str | None = None,
        evidence: str | None = None,
        tags: list[str] | None = None,
        recent_limit: int = 8,
    ) -> dict[str, Any]:
        """Curate durable project memory. 'consider' writes only material events; 'force' explicitly persists; 'status' returns recent memory metadata. Never send secrets/credentials."""
        events = _load_events(project)
        if action == 'status':
            limit = max(1, min(int(recent_limit), 25))
            return {
                'project': project,
                'event_count': len(events),
                'recent': events[-limit:],
                'policy': 'material-events-only',
            }

        event = {
            'title': _clean(title),
            'activity': _clean(activity),
            'decision': _clean(decision),
            'result': _clean(result),
            'next_step': _clean(next_step),
            'evidence': _clean(evidence),
            'tags': tags or [],
        }
        combined = json.dumps(event, ensure_ascii=False)
        if _contains_secret(combined):
            return {
                'project': project,
                'persisted': False,
                'blocked': True,
                'reason': 'possible credential/secret detected; remove secrets before persisting memory',
            }
        if not event['activity']:
            raise ValueError('activity is required for consider/force')

        score, reasons = _score(event)
        threshold = 5
        if action == 'consider' and score < threshold:
            return {
                'project': project,
                'persisted': False,
                'score': score,
                'threshold': threshold,
                'reasons': reasons,
                'reason': 'event is not material enough for durable project memory',
            }

        fp = _fingerprint(project, event)
        if any(item.get('fingerprint') == fp for item in events):
            return {
                'project': project,
                'persisted': False,
                'duplicate': True,
                'fingerprint': fp,
                'reason': 'equivalent memory event already exists',
            }

        item = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'fingerprint': fp,
            'score': min(score, 10),
            'score_reasons': reasons,
            **event,
        }
        events.append(item)
        jsonl, md = _paths(project)
        with jsonl.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(item, ensure_ascii=False) + '\n')
        markdown = _render(project, events)
        tmp = md.with_suffix('.tmp')
        tmp.write_text(markdown, encoding='utf-8')
        tmp.replace(md)
        sync = await _sync_source(hub, project, markdown)
        return {
            'project': project,
            'persisted': True,
            'score': min(score, 10),
            'threshold': threshold,
            'reasons': reasons,
            'fingerprint': fp,
            'event_count': len(events),
            'sync': sync,
        }
