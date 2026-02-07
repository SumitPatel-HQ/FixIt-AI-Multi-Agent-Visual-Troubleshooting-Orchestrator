"""
FixIt AI - Streamlit Frontend
Enhanced to handle all answer_types with dynamic UI sections.
Supports multi-target localization, safety warnings, explanations, and more.
"""

import streamlit as st
import requests
import base64
from PIL import Image, ImageDraw
import io


# ==========================================
# Display Helper Functions (defined first)
# ==========================================

def show_status_badge(answer_type, status):
    """Show answer_type and status as badges."""
    status_icon = {
        "success": "🟢",
        "invalid_image": "🔴",
        "low_confidence": "🟠",
        "needs_clarification": "🟠",
        "error": "🔴",
    }.get(status, "⚪")
    st.caption(f"{status_icon} Status: **{status}** | Answer Type: `{answer_type}`")


def draw_visualizations(result, image):
    
    # Ensure image is in RGB mode
    if image.mode != "RGB":
        image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    """Draw bounding boxes and labels on image."""
    visualizations = result.get("visualizations", [])
    localization_results = result.get("localization_results")

    if visualizations:
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        colors = ["red", "blue", "green", "purple", "orange", "cyan", "magenta"]

        for i, viz in enumerate(visualizations):
            bbox = viz.get("bounding_box")
            label = viz.get("label", viz.get("target", ""))
            color = colors[i % len(colors)]

            if bbox:
                x_min = bbox.get("x_min", 0)
                y_min = bbox.get("y_min", 0)
                x_max = bbox.get("x_max", 0)
                y_max = bbox.get("y_max", 0)
                draw.rectangle([x_min, y_min, x_max, y_max], outline=color, width=3)
                if label:
                    text_bbox = draw.textbbox((x_min, y_min - 15), label)
                    draw.rectangle(text_bbox, fill=color)
                    draw.text((x_min, y_min - 15), label, fill="white")
                if viz.get("disambiguation_needed"):
                    st.warning(f"Ambiguous: {label} - {viz.get('ambiguity_note', 'Multiple matches')}")

        st.image(img_copy, width='stretch', caption="Detected Components")
    elif result.get("bounding_box"):
        bbox = result["bounding_box"]
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        draw.rectangle(
            [bbox["x_min"], bbox["y_min"], bbox["x_max"], bbox["y_max"]],
            outline="red", width=5,
        )
        st.image(img_copy, width='stretch', caption="Identified Component")
    else:
        st.image(image, width='stretch', caption="Uploaded Image")

    # Show localization status for non-found targets
    if localization_results and isinstance(localization_results, list):
        not_found = [r for r in localization_results if isinstance(r, dict) and r.get("status") != "found"]
        for r in not_found:
            target = r.get("target", "component")
            loc_status = r.get("status", "not_visible")
            if loc_status == "not_visible":
                st.info(f"**{target}**: Not visible from this angle. {r.get('suggested_action', '')}")
            elif loc_status == "not_present":
                st.warning(f"**{target}**: Not present on this device. {r.get('reasoning', '')}")
            elif loc_status == "ambiguous":
                st.warning(f"**{target}**: Ambiguous - {r.get('reasoning', 'Multiple matches found')}")


def show_rejection(result):
    """Display rejection response."""
    st.error(result.get("message", "This image is not suitable for troubleshooting."))
    if result.get("what_was_detected"):
        st.markdown(f"**What I see:** {result['what_was_detected']}")
    if result.get("suggestion"):
        st.info(f"**Suggestion:** {result['suggestion']}")
    if result.get("supported_devices"):
        st.markdown("**Supported Devices:**")
        for d in result["supported_devices"]:
            st.markdown(f"- {d}")


def show_better_input(result):
    """Display better input request."""
    st.warning(result.get("message", "I'm having trouble analyzing the image."))
    device_info = result.get("device_info", {})
    if device_info.get("device_type") and device_info["device_type"] != "Unknown":
        conf = device_info.get("confidence", 0)
        st.markdown(f"**Possible device:** {device_info['device_type']} ({conf:.0%} confidence)")
    if result.get("what_i_see"):
        st.markdown(f"**What I see:** {result['what_i_see']}")
    if result.get("reasoning"):
        st.markdown(f"**Reasoning:** {result['reasoning']}")
    if result.get("suggestions"):
        st.markdown("**Suggestions:**")
        for s in result["suggestions"]:
            st.markdown(f"- {s}")
    if result.get("clarifying_questions"):
        st.markdown("**Questions:**")
        for q in result["clarifying_questions"]:
            st.markdown(f"- {q}")


def show_safety_warning(result):
    """Display safety warning."""
    st.error("**SAFETY WARNING** - This situation may require professional help.")
    safety = result.get("safety", {})
    if isinstance(safety, dict) and safety.get("safety_message"):
        st.error(safety["safety_message"])
    diagnosis = result.get("diagnosis")
    if isinstance(diagnosis, dict):
        if diagnosis.get("safety_warning"):
            st.warning(diagnosis["safety_warning"])
        if diagnosis.get("issue"):
            st.markdown(f"**Assessment:** {diagnosis['issue']}")
    st.markdown("---")
    st.markdown("""**Do NOT attempt DIY repair. Instead:**
1. Disconnect power if safe to do so
2. Move away from the device if there's smoke/fire
3. Contact a qualified professional or manufacturer support
4. If there's immediate danger, call emergency services""")


def show_clarification(result):
    """Display clarification request."""
    st.info(result.get("message", "I need more information to help you."))
    questions = result.get("clarifying_questions", [])
    if questions:
        st.markdown("**Please help me by answering:**")
        for q in questions:
            st.markdown(f"- {q}")


def show_identification(result):
    """Display identification results."""
    device_info = result.get("device_info", {})
    st.markdown(f"### {device_info.get('device_type', 'Unknown Device')}")
    conf = device_info.get("confidence", 0)
    badge = "🟢" if conf >= 0.6 else "🟠" if conf >= 0.3 else "🔴"
    st.markdown(f"{badge} Confidence: **{conf:.0%}**")
    if device_info.get("brand") and device_info["brand"].lower() not in ("unknown", "generic"):
        st.markdown(f"**Brand:** {device_info['brand']}")
        if device_info.get("model") and device_info["model"].lower() != "not visible":
            st.markdown(f"**Model:** {device_info['model']}")
    if device_info.get("brand_model_guidance"):
        st.info(f"**Where to find brand/model:** {device_info['brand_model_guidance']}")
    components = device_info.get("components", [])
    if components:
        st.markdown("**Detected Components:**")
        for c in components:
            st.markdown(f"- {c}")


def show_localization(result):
    """Display localization results."""
    results = result.get("localization_results", [])
    if not results:
        st.info("No components were located.")
        return
    for r in results:
        if not isinstance(r, dict):
            continue
        target = r.get("target", "component")
        loc_status = r.get("status", "not_visible")
        if loc_status == "found":
            st.success(f"**{target}**: Found!")
            if r.get("spatial_description"):
                st.markdown(f"Location: {r['spatial_description']}")
            if r.get("landmark_description"):
                st.markdown(f"Landmark: {r['landmark_description']}")
        elif loc_status == "not_visible":
            st.warning(f"**{target}**: Not visible from this angle")
            if r.get("suggested_action"):
                st.markdown(f"Try: {r['suggested_action']}")
        elif loc_status == "not_present":
            st.error(f"**{target}**: Not present on this device")
            if r.get("reasoning"):
                st.markdown(f"Reason: {r['reasoning']}")
        elif loc_status == "ambiguous":
            st.warning(f"**{target}**: Ambiguous - multiple matches")
            if r.get("reasoning"):
                st.markdown(f"Details: {r['reasoning']}")


def show_explanation(result):
    """Display explanation results."""
    explanation = result.get("explanation")
    if not explanation:
        st.info("No explanation was generated.")
        return
    if isinstance(explanation, dict):
        overview = explanation.get("overview", "")
        if overview:
            st.markdown(f"### Overview\n{overview}")
        comp_functions = explanation.get("component_functions", [])
        if comp_functions:
            st.markdown("### Component Functions")
            for cf in comp_functions:
                if isinstance(cf, dict):
                    name = cf.get("name", "")
                    purpose = cf.get("purpose", "")
                    how = cf.get("how_it_works", "")
                    st.markdown(f"**{name}**: {purpose}")
                    if how:
                        st.caption(how)
        data_flow = explanation.get("data_flow", "")
        if data_flow:
            st.markdown(f"### Data/Energy Flow\n{data_flow}")
        concepts = explanation.get("key_concepts", [])
        if concepts:
            st.markdown("### Key Concepts")
            for c in concepts:
                st.markdown(f"- {c}")
        misconceptions = explanation.get("common_misconceptions", [])
        if misconceptions:
            with st.expander("Common Misconceptions"):
                for m in misconceptions:
                    st.markdown(f"- {m}")
    elif isinstance(explanation, str):
        st.markdown(explanation)


def show_diagnosis(result):
    """Display diagnosis results."""
    diagnosis = result.get("diagnosis")
    if not diagnosis or not isinstance(diagnosis, dict):
        st.info("No diagnosis was generated.")
        return
    
    issue = diagnosis.get("issue", "")
    severity = diagnosis.get("severity", "medium")
    safety_warning = diagnosis.get("safety_warning")
    
    # Map severity to actual emojis (not emoji codes)
    sev_emojis = {
        "low": "🟢",
        "medium": "🟠", 
        "high": "🔴",
        "critical": "🔴"
    }
    emoji = sev_emojis.get(severity, "⚪")
    
    st.markdown(f"### Diagnosis {emoji} Severity: {severity.upper()}")
    
    if issue:
        st.markdown(issue)
    else:
        # Fallback if no issue text
        issue_diag = result.get("issue_diagnosis", "")
        if issue_diag:
            st.markdown(issue_diag)
        else:
            st.info("Diagnosis analysis is in progress...")
    
    if safety_warning:
        st.error(f"**Safety Warning:** {safety_warning}")
    
    causes = diagnosis.get("possible_causes", [])
    if causes:
        st.markdown("**Possible Causes:**")
        for c in causes:
            st.markdown(f"- {c}")
    
    indicators = diagnosis.get("indicators", [])
    if indicators:
        st.markdown("**Indicators:**")
        for ind in indicators:
            st.markdown(f"- {ind}")
    
    if diagnosis.get("professional_needed"):
        st.warning("Professional assistance recommended for this issue.")


def show_troubleshoot(result):
    """Display full troubleshooting response."""
    show_device_summary(result)

    # Localization info
    loc_results = result.get("localization_results")
    if loc_results and isinstance(loc_results, list):
        found = [r for r in loc_results if isinstance(r, dict) and r.get("status") == "found"]
        if found:
            first = found[0]
            st.markdown(f"**Component:** {first.get('target', '')}")
            if first.get("spatial_description"):
                st.markdown(f"**Location:** {first['spatial_description']}")

    # Diagnosis
    if result.get("diagnosis"):
        show_diagnosis(result)
    elif result.get("issue_diagnosis"):
        st.markdown(f"### Diagnosis\n{result['issue_diagnosis']}")

    # Warnings
    if result.get("warnings"):
        for w in result["warnings"]:
            st.warning(w)

    # Steps
    steps = result.get("troubleshooting_steps")
    if steps and isinstance(steps, list):
        st.markdown("### Repair Steps")
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_num = step.get("step", step.get("step_number", "?"))
            instruction = step.get("instruction", "")
            st.markdown(f"**Step {step_num}**: {instruction}")
            if step.get("visual_cue"):
                st.caption(f"Look for: {step['visual_cue']}")
            if step.get("safety_note"):
                st.warning(step["safety_note"])
            if step.get("estimated_time"):
                st.caption(f"Time: {step['estimated_time']}")

    # When to seek help
    if result.get("when_to_seek_help"):
        st.divider()
        st.markdown("### When to Seek Professional Help")
        st.info(result["when_to_seek_help"])


def show_mixed(result):
    """Display mixed response (multiple intents)."""
    show_device_summary(result)

    if result.get("explanation"):
        with st.expander("How It Works", expanded=True):
            show_explanation(result)
    if result.get("diagnosis"):
        with st.expander("Diagnosis", expanded=True):
            show_diagnosis(result)
    if result.get("localization_results"):
        with st.expander("Component Locations", expanded=True):
            show_localization(result)
    if result.get("troubleshooting_steps"):
        with st.expander("Repair Steps", expanded=True):
            steps = result["troubleshooting_steps"]
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_num = step.get("step", step.get("step_number", "?"))
                st.markdown(f"**Step {step_num}**: {step.get('instruction', '')}")
                if step.get("visual_cue"):
                    st.caption(f"Look for: {step['visual_cue']}")


def show_device_summary(result):
    """Show device identification summary."""
    device_info = result.get("device_info", {})
    device_type = device_info.get("device_type") or result.get("device_identified", "Unknown")
    confidence = device_info.get("confidence") or result.get("device_confidence", 0)
    badge = "🟢" if confidence >= 0.6 else "🟠" if confidence >= 0.3 else "🔴"
    st.markdown(f"**Device:** {device_type} {badge} ({confidence:.0%} confidence)")

    brand = device_info.get("brand", "")
    model = device_info.get("model", "")
    if brand and brand.lower() not in ("unknown", "generic", ""):
        brand_str = brand
        if model and model.lower() not in ("not visible", ""):
            brand_str += f" {model}"
        st.caption(f"Brand/Model: {brand_str}")

    components = device_info.get("components") or result.get("detected_components", [])
    if components:
        with st.expander("Detected Components"):
            for c in components:
                st.markdown(f"- {c}")


def show_audio(result):
    """Show audio instructions section."""
    audio = result.get("audio_instructions", "")
    if audio:
        st.markdown("### Audio Script")
        st.info(audio)


def show_grounding(result):
    """Show web grounding info with source links."""
    st.markdown("**Web Search Sources**")
    st.caption("Gemini's native Google Search grounding was used to enhance this response.")

    sources = result.get("grounding_sources", [])
    if sources:
        for src in sources:
            if isinstance(src, dict):
                url = src.get("url", "")
                title = src.get("title", url)
                if url:
                    st.markdown(f"- [{title}]({url})")
                elif title:
                    st.caption(f"- {title}")
            elif isinstance(src, str):
                st.caption(f"- {src}")

    summary = result.get("grounding_sources_summary")
    if summary and not sources:
        st.caption(f"Sources: {summary}")

    disclaimer = result.get("grounding_disclaimer")
    if disclaimer:
        st.caption(f"_{disclaimer}_")


# ==========================================
# Answer type display config
# ==========================================

ANSWER_TYPE_TITLES = {
    "locate_only": "Component Location",
    "identify_only": "Detected Components",
    "explain_only": "How It Works",
    "troubleshoot_steps": "Troubleshooting Steps",
    "diagnose_only": "Diagnosis",
    "mixed": "Analysis Results",
    "ask_clarifying_questions": "I need more information",
    "reject_invalid_image": "Image Not Suitable",
    "ask_for_better_input": "Better Image Needed",
    "safety_warning_only": "Safety Alert",
}

# ==========================================
# Main App Layout
# ==========================================

st.set_page_config(page_title="FixIt AI", layout="wide")
st.title("FixIt AI - Device Troubleshooter")

# Sidebar
st.sidebar.header("Configuration")
api_url = st.sidebar.text_input("Backend URL", "http://localhost:8000/api/troubleshoot")

# Main Interface
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Input")
    uploaded_file = st.file_uploader(
        "Upload Image of Device (or any image to test rejection)",
        type=["jpg", "png", "jpeg"],
    )
    query = st.text_input("What is the issue?", "How do I fix this?")
    device_hint = st.text_input("Device Hint (Optional)", "")
    submit = st.button("Analyze & Troubleshoot", use_container_width=True)

if uploaded_file and submit:
    image = Image.open(uploaded_file)
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    width, height = image.size

    payload = {
        "image_base64": img_str,
        "query": query,
        "image_width": width,
        "image_height": height,
        "device_hint": device_hint,
    }

    with st.spinner("Analyzing with Gemini Vision..."):
        try:
            response = requests.post(api_url, data=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                st.session_state["result"] = result
                st.session_state["image"] = image
            else:
                st.error(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            st.error(f"Connection Failed: {e}")

# Display Results
if "result" in st.session_state and "image" in st.session_state:
    result = st.session_state["result"]
    image = st.session_state["image"]
    answer_type = result.get("answer_type", "troubleshoot_steps")
    status = result.get("status", "success")
    section_title = result.get("section_title", ANSWER_TYPE_TITLES.get(answer_type, "Analysis Results"))

    with col1:
        st.subheader("Visualization")
        draw_visualizations(result, image)

    with col2:
        st.subheader(f"2. {section_title}")
        show_status_badge(answer_type, status)
        st.divider()

        # Route to appropriate display
        if answer_type == "reject_invalid_image":
            show_rejection(result)
        elif answer_type == "ask_for_better_input":
            show_better_input(result)
        elif answer_type == "safety_warning_only":
            show_safety_warning(result)
        elif answer_type == "ask_clarifying_questions":
            show_clarification(result)
        elif answer_type == "identify_only":
            show_identification(result)
        elif answer_type == "locate_only":
            show_localization(result)
        elif answer_type == "explain_only":
            show_explanation(result)
        elif answer_type == "diagnose_only":
            show_diagnosis(result)
        elif answer_type == "troubleshoot_steps":
            show_troubleshoot(result)
        elif answer_type == "mixed":
            show_mixed(result)
        else:
            show_troubleshoot(result)

        # Audio (always shown)
        st.divider()
        show_audio(result)

        # Web Grounding badge
        if result.get("web_grounding_used"):
            st.divider()
            show_grounding(result)

        # Raw JSON
        with st.expander("Raw JSON Response"):
            st.json(result)
