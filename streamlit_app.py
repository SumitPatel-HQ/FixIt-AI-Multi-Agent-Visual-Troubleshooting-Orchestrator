"""
FixIt AI - Streamlit Frontend Debugger
Now handles all response scenarios including rejections and low-confidence cases.
"""

import streamlit as st
import requests
import base64
from PIL import Image, ImageDraw
import io
import json

st.set_page_config(page_title="FixIt AI Debugger", layout="wide")

st.title("🔧 FixIt AI - Backend Debugger")

# Sidebar for Config
st.sidebar.header("Configuration")
api_url = st.sidebar.text_input("Backend URL", "http://localhost:8000/api/troubleshoot")

# Status badge colors
STATUS_COLORS = {
    "success": "🟢",
    "invalid_image": "🔴",
    "low_confidence": "🟡",
    "component_not_located": "🟠",
    "needs_clarification": "🟡",
    "error": "🔴"
}

STATUS_LABELS = {
    "success": "Success",
    "invalid_image": "Invalid Image",
    "low_confidence": "Low Confidence",
    "component_not_located": "Component Not Found",
    "needs_clarification": "Needs Clarification",
    "error": "Error"
}

# Main Interface
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Input")
    uploaded_file = st.file_uploader("Upload Image of Device (or any image to test rejection)", type=["jpg", "png", "jpeg"])
    query = st.text_input("What is the issue?", "How do I fix this?")
    device_hint = st.text_input("Device Hint (Optional)", "")
    
    submit = st.button("Analyze & Troubleshoot", width='stretch')

if uploaded_file and submit:
    # Prepare Request
    image = Image.open(uploaded_file)
    # Convert to Base64
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    width, height = image.size
    
    payload = {
        "image_base64": img_str,
        "query": query,
        "image_width": width,
        "image_height": height,
        "device_hint": device_hint
    }
    
    with st.spinner("Analyzing with Gemini Vision..."):
        try:
            response = requests.post(api_url, data=payload)
            
            if response.status_code == 200:
                result = response.json()
                st.session_state['result'] = result
                st.session_state['image'] = image
                
                # Show appropriate message based on status
                status = result.get("status", "unknown")
                if status == "success":
                    st.success("✅ Analysis Complete!")
                elif status == "invalid_image":
                    st.warning("⚠️ Image Not Suitable for Troubleshooting")
                elif status == "low_confidence":
                    st.warning("🤔 Need More Information")
                elif status == "component_not_located":
                    st.info("📍 Component Not Found")
                elif status == "needs_clarification":
                    st.info("❓ Clarification Needed")
                else:
                    st.info("Analysis returned")
            else:
                st.error(f"Error {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"Connection Failed: {e}")

# Display Results
if 'result' in st.session_state and 'image' in st.session_state:
    result = st.session_state['result']
    image = st.session_state['image']
    status = result.get("status", "unknown")
    
    with col1:
        st.subheader("Visualization")
        
        # Draw Bounding Box if available
        bbox = result.get("bounding_box")
        if bbox and status == "success":
            st.info(f"Target located at: {bbox}")
            img_with_box = image.copy()
            draw = ImageDraw.Draw(img_with_box)
            draw.rectangle(
                [bbox['x_min'], bbox['y_min'], bbox['x_max'], bbox['y_max']], 
                outline="red", 
                width=5
            )
            st.image(img_with_box, width='stretch', caption="Identified Component")
        else:
            st.image(image, width='stretch', caption="Uploaded Image")

    with col2:
        st.subheader("2. Analysis Results")
        
        # Status Badge
        status_icon = STATUS_COLORS.get(status, "⚪")
        status_label = STATUS_LABELS.get(status, status)
        st.markdown(f"### {status_icon} Status: {status_label}")
        
        # Handle different scenarios
        if status == "invalid_image":
            # Rejection response
            st.markdown("---")
            st.markdown("### ❌ Image Rejected")
            st.warning(result.get("message", result.get("rejection_reason", "This image is not suitable.")))
            
            if result.get("what_was_detected"):
                st.markdown(f"**What I see:** {result.get('what_was_detected')}")
            
            if result.get("suggestion"):
                st.info(f"💡 **Suggestion:** {result.get('suggestion')}")
            
            if result.get("supported_devices"):
                st.markdown("**Supported Devices:**")
                for device in result.get("supported_devices", []):
                    st.markdown(f"- {device}")
            
            st.divider()
            st.markdown("### 🔊 Message")
            st.info(result.get("audio_instructions", ""))
            
        elif status == "low_confidence":
            # Low confidence response
            st.markdown("---")
            st.markdown("### 🤔 Need More Information")
            
            device = result.get("device_identified", "Unknown")
            confidence = result.get("device_confidence", 0.0)
            st.markdown(f"**Device:** {device} ({confidence:.0%} confidence)")
            
            if result.get("what_i_see"):
                st.markdown(f"**What I see:** {result.get('what_i_see')}")
            
            if result.get("reasoning"):
                st.markdown(f"**Reasoning:** {result.get('reasoning')}")
            
            if result.get("clarifying_questions"):
                st.markdown("### ❓ Clarifying Questions")
                for q in result.get("clarifying_questions", []):
                    st.markdown(f"- {q}")
            
            if result.get("suggestions"):
                st.markdown("### 💡 Suggestions")
                for s in result.get("suggestions", []):
                    st.markdown(f"- {s}")
            
            if result.get("general_safety_tip"):
                st.warning(f"⚠️ {result.get('general_safety_tip')}")
            
            st.divider()
            st.markdown("### 🔊 Audio Script")
            st.info(result.get("audio_instructions", ""))
            
        elif status == "component_not_located":
            # Component not found response
            st.markdown("---")
            
            device = result.get("device_identified", "Unknown")
            confidence = result.get("device_confidence", 0.0)
            st.markdown(f"**Device:** {device} ({confidence:.0%} confidence)")
            st.markdown(f"**Component Searched:** {result.get('component_searched', result.get('component', 'Unknown'))}")
            
            st.warning(result.get("message", "Component not visible in image"))
            
            if result.get("typical_location"):
                st.info(f"📍 **Typical Location:** {result.get('typical_location')}")
            
            if result.get("visible_components") or result.get("visible_alternatives"):
                alternatives = result.get("visible_components") or result.get("visible_alternatives", [])
                if alternatives:
                    st.markdown("**Visible Components:**")
                    for comp in alternatives:
                        st.markdown(f"- {comp}")
            
            if result.get("suggestion"):
                st.info(f"💡 {result.get('suggestion')}")
            
            # Show steps even for component not found
            steps = result.get("troubleshooting_steps", [])
            if steps:
                st.subheader("🛠️ Suggested Actions")
                for step in steps:
                    st.markdown(f"""
                    **Step {step.get('step_number', '?')}**: {step.get('instruction', '')}  
                    *{step.get('visual_cue', '')}*
                    """)
                    
        elif status == "success" or status == "needs_clarification":
            # Success response - full results
            st.markdown("---")
            
            # Device Info
            device = result.get("device_identified", "Unknown")
            confidence = result.get("device_confidence", 0.0)
            confidence_level = result.get("confidence_level", "unknown")
            
            confidence_badge = "🟢" if confidence >= 0.6 else "🟡" if confidence >= 0.3 else "🔴"
            st.markdown(f"**Device:** {device} {confidence_badge} ({confidence:.0%} confidence)")
            
            if result.get("component"):
                st.markdown(f"**Component:** {result.get('component')}")
            if result.get("spatial_description"):
                st.markdown(f"**Location:** {result.get('spatial_description')}")
            
            if result.get("detected_components"):
                with st.expander("📦 Detected Components"):
                    for comp in result.get("detected_components", []):
                        st.markdown(f"- {comp}")
            
            st.divider()
            
            # Diagnosis
            st.markdown(f"### 🩺 Diagnosis\n{result.get('issue_diagnosis', 'N/A')}")
            
            # Warnings
            if result.get("warnings"):
                for warning in result.get("warnings"):
                    st.warning(f"⚠️ {warning}")
            
            # Steps
            st.subheader("🛠️ Repair Steps")
            steps = result.get("troubleshooting_steps", [])
            for step in steps:
                with st.container():
                    col_step, col_time = st.columns([4, 1])
                    with col_step:
                        st.markdown(f"**Step {step.get('step_number', '?')}**: {step.get('instruction', '')}")
                        if step.get('visual_cue'):
                            st.markdown(f"*Look for: {step.get('visual_cue')}*")
                        if step.get('safety_note'):
                            st.warning(f"⚠️ {step.get('safety_note')}")
                        if step.get('caveat'):
                            st.info(f"ℹ️ {step.get('caveat')}")
                    with col_time:
                        st.caption(step.get('estimated_time', ''))
            
            # When to seek help
            if result.get("when_to_seek_help"):
                st.divider()
                st.markdown(f"### 👨‍🔧 When to Seek Professional Help")
                st.info(result.get("when_to_seek_help"))
            
            st.divider()
            st.markdown("### 🔊 Audio Script")
            st.info(result.get("audio_instructions", ""))
        
        else:
            # Unknown status - show raw response
            st.warning(f"Unknown status: {status}")
            st.markdown(f"**Message:** {result.get('message', 'No message')}")
        
        # Always show raw JSON at the bottom
        with st.expander("📋 Raw JSON Response"):
            st.json(result)
