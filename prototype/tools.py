"""
Tool definitions and handlers for Chat Agent.
Each tool simulates a real data source — replace the body with live API calls.
"""

import re
from datetime import datetime

# ── Tool schemas (passed to Claude) ──────────────────────────────────────────

TOOLS = [
    {
        "name": "search_similar_cases",
        "description": (
            "Search historical Salesforce support cases for issues similar to the one described. "
            "Returns matching cases with their resolution steps. "
            "Use this first when given any issue description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or error message to search for in historical cases"
                },
                "product": {
                    "type": "string",
                    "description": "Revenue Cloud product area (e.g. CPQ, Configurator, Billing, Price Management)",
                    "enum": ["CPQ", "Configurator", "Billing", "Price Management", "Transaction Management", "Product Catalog", "Any"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of cases to return (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_documentation",
        "description": (
            "Search Salesforce knowledge base articles, product documentation, and known issues. "
            "Use this to find official guidance, workarounds, or release notes relevant to the issue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms for documentation lookup"
                },
                "doc_type": {
                    "type": "string",
                    "description": "Type of documentation to search",
                    "enum": ["KB Article", "Known Issue", "Release Notes", "Help Doc", "Any"]
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_error_log",
        "description": (
            "Analyze an error log, stack trace, or debug output. "
            "Extracts key error codes, exception types, and patterns to help identify the root cause. "
            "Use this when the customer has shared a log or error message."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "log_text": {
                    "type": "string",
                    "description": "The raw error log, stack trace, or debug output to analyze"
                }
            },
            "required": ["log_text"]
        }
    }
]


# ── Mock data (replace with live API calls) ───────────────────────────────────

MOCK_CASES = [
    {
        "case_number": "CS-2024-041892",
        "subject": "CPQ quote line totals incorrect after adding bundle product",
        "product": "CPQ",
        "resolution": "Bundle pricing rule had a cascading condition that overrode line-level discounts. Fix: set 'Apply to Bundle Components' to false on the pricing rule. See KB0048821.",
        "root_cause": "Pricing rule misconfiguration on bundle parent",
        "closed_date": "2024-09-12"
    },
    {
        "case_number": "CS-2025-003441",
        "subject": "Quote total shows 0 after applying discount schedule",
        "product": "CPQ",
        "resolution": "Discount schedule was set to override unit price rather than add. Changed schedule type from 'Override' to 'Discount' and totals calculated correctly.",
        "root_cause": "Discount schedule type set to Override",
        "closed_date": "2025-01-08"
    },
    {
        "case_number": "CS-2024-078233",
        "subject": "RCA Configurator attribute validation blocking order submission",
        "product": "Configurator",
        "resolution": "Custom attribute validation rule referenced a deleted picklist value. Removed stale value from validation logic and redeployed the configuration.",
        "root_cause": "Stale picklist value in attribute validation rule",
        "closed_date": "2024-11-30"
    },
    {
        "case_number": "CS-2025-011044",
        "subject": "Billing invoice not generating for active contract",
        "product": "Billing",
        "resolution": "Billing treatment on the product was set to 'In Arrears' but the order activation date fell outside the billing period. Adjusted billing date anchor on the order product.",
        "root_cause": "Billing period date anchor mismatch",
        "closed_date": "2025-02-14"
    },
    {
        "case_number": "CS-2025-022187",
        "subject": "CPQ price book entries missing after sandbox refresh",
        "product": "CPQ",
        "resolution": "CPQ custom settings (SBQQ__CustomAction__c) were not included in the sandbox refresh template. Re-imported price book entries via the CPQ Setup UI.",
        "root_cause": "Sandbox refresh missing CPQ custom settings",
        "closed_date": "2025-04-01"
    },
    {
        "case_number": "CS-2025-031882",
        "subject": "Governor limit exception on large quote with 200+ line items",
        "product": "CPQ",
        "resolution": "Large data volume triggered SOQL row limit in the pricing engine. Enabled Large Quote Optimization in CPQ Settings (SBQQ__LargeQuoteThreshold__c = 100) to batch pricing calculations.",
        "root_cause": "SOQL row limit exceeded in pricing engine",
        "closed_date": "2025-05-20"
    },
    {
        "case_number": "CS-2025-038014",
        "subject": "Price Management waterfall not applying tiered pricing correctly",
        "product": "Price Management",
        "resolution": "Tier boundaries in the price schedule had overlapping ranges. Corrected boundary definitions so each tier is mutually exclusive. After save, recalculated all affected quotes.",
        "root_cause": "Overlapping tier boundaries in price schedule",
        "closed_date": "2025-06-03"
    },
    {
        "case_number": "CS-2025-044901",
        "subject": "System.LimitException Too many SOQL queries 101 in CPQ calculation",
        "product": "CPQ",
        "resolution": "Custom apex trigger on Quote Line was firing on every field update during CPQ price calculations, consuming SOQL queries. Added a static flag guard to prevent re-entrant trigger execution.",
        "root_cause": "Re-entrant apex trigger consuming SOQL limit during CPQ calc",
        "closed_date": "2025-06-28"
    }
]

MOCK_DOCS = [
    {
        "title": "KB0048821 — CPQ Bundle Pricing Rule Behavior",
        "type": "KB Article",
        "summary": "Explains how 'Apply to Bundle Components' flag controls whether pricing rules cascade to component lines. When enabled, parent bundle rules override component-level discounts.",
        "url": "https://help.salesforce.com/kb0048821"
    },
    {
        "title": "Known Issue — CPQ Quote Total Recalculation Delay in Summer '25",
        "type": "Known Issue",
        "summary": "Quote totals may show stale values after applying a discount schedule if the quote was last saved in a prior release. Workaround: force recalculate via 'Recalculate' button or API.",
        "url": "https://help.salesforce.com/known-issue-cpq-summer25"
    },
    {
        "title": "Configure Billing Treatment for Revenue Recognition",
        "type": "Help Doc",
        "summary": "Guide on setting billing treatment types (In Advance, In Arrears, Evergreen) and how the billing date anchor affects invoice generation on active contracts.",
        "url": "https://help.salesforce.com/billing-treatment-guide"
    },
    {
        "title": "KB0061203 — Resolving Governor Limits in CPQ Large Quote Scenarios",
        "type": "KB Article",
        "summary": "Steps to enable Large Quote Optimization and set the SBQQ__LargeQuoteThreshold__c custom setting to batch CPQ pricing calculations and avoid SOQL/CPU limit exceptions.",
        "url": "https://help.salesforce.com/kb0061203"
    },
    {
        "title": "Revenue Cloud Summer '25 Release Notes",
        "type": "Release Notes",
        "summary": "New features: RCA Configurator attribute inheritance improvements, Billing invoice PDF redesign, Price Management waterfall visualization in Setup, CPQ Quote Clone performance enhancements.",
        "url": "https://help.salesforce.com/release-notes-summer25"
    },
    {
        "title": "KB0055910 — Sandbox Refresh Checklist for CPQ",
        "type": "KB Article",
        "summary": "Required objects to include in sandbox refresh templates for CPQ: SBQQ__CustomAction__c, SBQQ__PriceBook__c, SBQQ__PricingGuidance__c. Missing any of these causes post-refresh pricing failures.",
        "url": "https://help.salesforce.com/kb0055910"
    },
    {
        "title": "KB0070112 — RCA Configurator Attribute Validation Rule Troubleshooting",
        "type": "KB Article",
        "summary": "Common causes of attribute validation failures: deleted picklist values, missing required attributes on base configuration, rule ordering conflicts. Includes step-by-step debug process.",
        "url": "https://help.salesforce.com/kb0070112"
    }
]


# ── Tool handlers ─────────────────────────────────────────────────────────────

def search_similar_cases(query: str, product: str = "Any", limit: int = 5) -> dict:
    """Fuzzy-match mock cases against the query and product filter."""
    keywords = set(re.sub(r"[^\w\s]", "", query.lower()).split())

    scored = []
    for case in MOCK_CASES:
        if product and product != "Any" and case["product"].lower() != product.lower():
            continue
        text = f"{case['subject']} {case['root_cause']} {case['resolution']}".lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, case))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [c for _, c in scored[:limit]]

    if not results:
        return {"found": 0, "cases": [], "note": "No similar cases found. Try broader keywords."}

    return {
        "found": len(results),
        "cases": results,
        "note": f"Top {len(results)} matching cases returned."
    }


def search_documentation(query: str, doc_type: str = "Any") -> dict:
    """Fuzzy-match mock docs against the query and doc type filter."""
    keywords = set(re.sub(r"[^\w\s]", "", query.lower()).split())

    scored = []
    for doc in MOCK_DOCS:
        if doc_type and doc_type != "Any" and doc["type"] != doc_type:
            continue
        text = f"{doc['title']} {doc['summary']}".lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [d for _, d in scored[:5]]

    if not results:
        return {"found": 0, "docs": [], "note": "No matching documentation found."}

    return {"found": len(results), "docs": results}


def analyze_error_log(log_text: str) -> dict:
    """Extract key signals from a raw error log."""
    patterns = {
        "SOQL limit": r"Too many SOQL queries:?\s*(\d+)",
        "CPU limit": r"Maximum CPU time exceeded|CPU limit",
        "Heap limit": r"Heap size too large|heap",
        "DML limit": r"Too many DML (rows|statements)",
        "Null pointer": r"System\.NullPointerException",
        "Governor limit": r"System\.LimitException",
        "Apex exception": r"(System\.\w+Exception):\s*([^\n]+)",
        "Flow error": r"FLOW_ELEMENT_ERROR.*?([^\n]+)",
        "Validation error": r"FIELD_CUSTOM_VALIDATION_EXCEPTION.*?([^\n]+)",
        "Permission error": r"INSUFFICIENT_ACCESS|You do not have.*?permission",
        "Record not found": r"ENTITY_IS_DELETED|Record.*?not found",
    }

    findings = []
    for label, pattern in patterns.items():
        match = re.search(pattern, log_text, re.IGNORECASE)
        if match:
            detail = match.group(0)[:120]
            findings.append({"type": label, "detail": detail})

    line_count = len(log_text.strip().splitlines())
    has_stack_trace = "at line" in log_text.lower() or "stack trace" in log_text.lower()
    has_class_ref = bool(re.search(r"Class\.\w+\.\w+:", log_text))

    return {
        "lines_analyzed": line_count,
        "errors_found": len(findings),
        "findings": findings,
        "has_stack_trace": has_stack_trace,
        "has_class_reference": has_class_ref,
        "raw_snippet": log_text[:300] + ("..." if len(log_text) > 300 else ""),
        "note": "Replace with live log parsing service for production use."
    }


def handle_tool_call(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "search_similar_cases":
        return search_similar_cases(**tool_input)
    elif tool_name == "search_documentation":
        return search_documentation(**tool_input)
    elif tool_name == "analyze_error_log":
        return analyze_error_log(**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}
