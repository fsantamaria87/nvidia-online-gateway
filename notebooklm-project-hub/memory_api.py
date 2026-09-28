from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

import memory_curator as mc


async def handle_project_memory(
    hub,
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
):
    events = mc._load_events(project)
    if action == 'status':
        limit = max(1, min(int(recent_limit), 25))
        return {
            'project': project,
            'event_count': len(events),
            'recent': events[-limit:],
            'policy': 'material-events-only',
            'dedupe_policy': 'exact+semantic-v1',
        }

    event = {
        'title': mc._clean(title),
        'activity': mc._clean(activity),
        'decision': mc._clean(decision),
        'result': mc._clean(result),
        'next_step': mc._clean(next_step),
        'evidence': mc._clean(evidence),
        'tags': tags or [],
    }
    combined = json.dumps(event, ensure_ascii=False)
    if mc._contains_secret(combined):
        return {
            'project': project,
            'persisted': False,
            'blocked': True,
            'reason': 'possible credential/secret detected; remove secrets before persisting memory',
        }
    if not event['activity']:
        raise ValueError('activity is required for consider/force')

    score, reasons = mc._score(event)
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

    duplicate = mc._find_duplicate(project, event, events)
    if duplicate:
        return {
            'project': project,
            'persisted': False,
            'duplicate': True,
            'duplicate_kind': duplicate['kind'],
            'fingerprint': duplicate['fingerprint'],
            'matched_fingerprint': duplicate['matched_fingerprint'],
            'semantic_score': duplicate['semantic_score'],
            'shared_anchors': duplicate['shared_anchors'],
            'reason': (
                'semantically equivalent memory event already exists'
                if duplicate['kind'] == 'semantic'
                else 'equivalent memory event already exists'
            ),
        }

    fp = mc._fingerprint(project, event)
    item = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'fingerprint': fp,
        'score': min(score, 10),
        'score_reasons': reasons,
        **event,
    }
    events.append(item)
    jsonl, md = mc._paths(project)
    with jsonl.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + '\n')
    markdown = mc._render(project, events)
    tmp = md.with_suffix('.tmp')
    tmp.write_text(markdown, encoding='utf-8')
    tmp.replace(md)
    sync = await mc._sync_source(hub, project, markdown)
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
