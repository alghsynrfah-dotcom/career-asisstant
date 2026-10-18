def failure_node(state):
    """أي فشل (تحقق أو agent) بيوصل هون ويرجع رسالة واضحة."""
    message = state.get("error") or "حدث خطأ غير متوقع."

    return {
        "final_response": "تعذر إكمال الطلب: " + message,
        "workflow_status": "failed",
    }
