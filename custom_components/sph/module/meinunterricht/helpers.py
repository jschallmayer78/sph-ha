"""Aggregation of "Mein Unterricht" entries per subject."""

from __future__ import annotations


def subject_overview(tasks) -> list[dict]:
    """Group entries by subject and summarise their status.

    Returns one entry per subject, sorted by open entries first and then by
    subject name, so the subjects that still need work are at the top.
    """
    grouped: dict[str, dict] = {}

    for task in tasks or []:
        subject = str(task.get("fach") or task.get("kurs") or "Ohne Fach").strip() or "Ohne Fach"
        entry = grouped.get(subject)
        if entry is None:
            entry = {
                "fach": subject,
                "kurse": [],
                "lehrer": [],
                "anzahl": 0,
                "offen": 0,
                "erledigt": 0,
                "letzter_eintrag": "",
                "offene_themen": [],
            }
            grouped[subject] = entry

        done = bool(task.get("erledigt"))
        entry["anzahl"] += 1
        entry["erledigt" if done else "offen"] += 1

        course = str(task.get("kurs") or "").strip()
        if course and course not in entry["kurse"]:
            entry["kurse"].append(course)

        teacher = str(task.get("lehrer") or "").strip()
        if teacher and teacher not in entry["lehrer"]:
            entry["lehrer"].append(teacher)

        date = str(task.get("datum") or "")
        if date > entry["letzter_eintrag"]:
            entry["letzter_eintrag"] = date

        if not done:
            topic = str(task.get("thema") or "").strip()
            if topic and topic not in entry["offene_themen"]:
                entry["offene_themen"].append(topic)

    for entry in grouped.values():
        entry["status"] = "offen" if entry["offen"] else "erledigt"

    return sorted(
        grouped.values(),
        key=lambda item: (-item["offen"], item["fach"].lower()),
    )
