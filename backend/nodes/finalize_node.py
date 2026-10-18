REQUIRED_SECTIONS = {
    "match": [
        "match score",
        "strengths",
        "gaps",
        "suggested cv improvements",
    ],
    "interview": [
        "technical questions",
        "behavioral questions",
        "preparation tips",
    ],
    "advice": [],
}

DISCLAIMER = (
    "ملاحظة: هذه النتيجة مساعدة إرشادية فقط وليست قرار توظيف "
    "ولا ضماناً للحصول على الوظيفة. راجعي الاقتراحات قبل اعتمادها."
)


def finalize_node(state):
    """مراجعة الجواب (الأقسام المطلوبة) + إضافة التنبيه + حفظ بالـ history."""
    answer = str(state.get("agent_answer", "")).strip()

    if not answer:
        return {
            "final_response": "تعذر إكمال الطلب: لم يرجع الوكيل أي جواب.",
            "workflow_status": "failed",
            "error": "لم يرجع الـ Agent أي جواب.",
        }

    task = state.get("task_type", "")
    lowered = answer.lower()
    missing = [
        section
        for section in REQUIRED_SECTIONS.get(task, [])
        if section not in lowered
    ]

    final = answer
    status = "completed"

    if missing:
        status = "completed_with_warnings"
        final += "\n\n(تنبيه: بعض الأقسام المتوقعة غير موجودة: " + ", ".join(missing) + ")"

    final += "\n\n---\n" + DISCLAIMER

    return {
        "final_response": final,
        "workflow_status": status,
        "history": [
            {"task_type": task, "answer": answer[:1500]}
        ],
    }
