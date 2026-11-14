"""Seeded visual-only graph. No generated entity is represented as live evidence."""
import math
import random

KINDS = ['PAPER','GRANT','MODEL','ALGORITHM','INDUSTRY','REPOSITORY']
TOPICS = ['Retrieval systems','Agent systems','Foundation models','Evaluation','Public funding','Deployment']


def seed_demo(db, count=144):
    if db.execute('SELECT COUNT(*) FROM entities').fetchone()[0]:
        return
    rng = random.Random(2401)
    for i in range(count):
        cluster = i % len(KINDS)
        db.execute('INSERT INTO entities(id,label,kind,description,demo) VALUES(?,?,?,?,1)',
                   (f'demo-{i}', f'{TOPICS[cluster]} / sample {i // 6 + 1:02d}', KINDS[cluster],
                    'Seeded visualization sample. This entity has no source record.'))
    seen = set()
    for i in range(count):
        for j in (1, 2, 3):
            target = (i + j * 6 + rng.randrange(0, 3) * 6) % count if j < 3 else rng.randrange(count)
            if target == i or (i, target) in seen:
                continue
            seen.add((i, target))
            db.execute('INSERT INTO relationships(id,source_id,target_id,kind,confidence,demo) VALUES(?,?,?,?,?,1)',
                       (f'demo-edge-{i}-{j}', f'demo-{i}', f'demo-{target}', 'DEMO_ASSOCIATION', 'similarity'))
