from governance_ledger import build_review_report, extract_constraints, review_constraints


def test_builds_review_report_with_source_text():
    text = """
    Transfers above $1M require manager approval.
    Proposer and approver must be separate.
    """
    policy = extract_constraints(text)

    report = build_review_report(
        text,
        policy,
        review_id="review-001",
        created_at="2026-05-07T20:14:00Z",
        source_document="finance_policy.txt",
    )

    assert report == {
        "review_id": "review-001",
        "created_at": "2026-05-07T20:14:00Z",
        "source_document": "finance_policy.txt",
        "review_status": "pending",
        "detected_constraints": [
            {
                "type": "required_role",
                "value": "manager",
                "source_text": "require manager approval",
            },
            {
                "type": "separation_of_duties",
                "value": True,
                "source_text": "must be separate",
            },
            {
                "type": "approval_threshold",
                "operation": "transfer_funds",
                "value": 1_000_000,
                "source_text": "above $1M",
            },
        ],
        "warnings": [],
    }


def test_review_constraints_extracts_and_reports():
    report = review_constraints(
        "Only compliance may approve transfers.",
        review_id="review-002",
        created_at="2026-05-07T20:15:00Z",
    )

    assert report == {
        "review_id": "review-002",
        "created_at": "2026-05-07T20:15:00Z",
        "source_document": None,
        "review_status": "pending",
        "detected_constraints": [
            {
                "type": "required_role",
                "value": "compliance",
                "source_text": "Only compliance may",
            },
        ],
        "warnings": [],
    }


def test_review_id_is_stable_when_not_supplied():
    text = "Only compliance may approve transfers."
    policy = extract_constraints(text)

    first_report = build_review_report(
        text,
        policy,
        created_at="2026-05-07T20:15:00Z",
    )
    second_report = build_review_report(
        text,
        policy,
        created_at="2026-05-07T20:16:00Z",
    )

    assert first_report["review_id"] == second_report["review_id"]
    assert first_report["review_id"].startswith("review-")
