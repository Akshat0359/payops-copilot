from datetime import datetime


def compute_priority_score(
    amount_paise: int,
    created_at: datetime,
    respond_by: datetime | None = None,
) -> int:
    amount_pts = min(30, int((amount_paise / 100_000) * 30))

    age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
    age_pts = min(20, int((age_hours / 24) * 20))

    deadline_pts = 0
    if respond_by:
        hours_left = (respond_by - datetime.utcnow()).total_seconds() / 3600
        if hours_left < 24:
            deadline_pts = 50
        elif hours_left < 48:
            deadline_pts = 35
        elif hours_left < 96:
            deadline_pts = 20

    return min(100, amount_pts + age_pts + deadline_pts)
