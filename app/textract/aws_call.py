
def _safe_text(d):
    if not d:
        return None
    t = d.get("Text")
    return t if isinstance(t, str) else str(t)


def process_image(client, image_bytes):
    response = client.analyze_expense(Document={'Bytes': image_bytes})
    out = []

    for exp in response.get("ExpenseDocuments", []):
        for field in exp.get("SummaryFields", []):
            out.append({
                "source": "summary",
                "label_text": _safe_text(field.get("LabelDetection")),
                "label_conf": field.get("LabelDetection", {}).get("Confidence"),
                "value_text": _safe_text(field.get("ValueDetection")),
                "value_conf": field.get("ValueDetection", {}).get("Confidence"),
            })

        for group in exp.get("LineItemGroups", []):
            for item in group.get("LineItems", []):
                for field in item.get("LineItemExpenseFields", []):
                    out.append({
                        "source": "line_item",
                        "label_text": _safe_text(field.get("LabelDetection")),
                        "label_conf": field.get("LabelDetection", {}).get("Confidence"),
                        "value_text": _safe_text(field.get("ValueDetection")),
                        "value_conf": field.get("ValueDetection", {}).get("Confidence"),
                    })
    return out

