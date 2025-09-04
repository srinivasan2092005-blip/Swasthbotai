import streamlit as st
import pandas as pd
from collections import defaultdict

# Safe import for plotly
try:
    import plotly.express as px
except ModuleNotFoundError:
    st.warning("Plotly is not installed. Some graphs may not display.")
    px = None

# Safe import for speech recognition
try:
    import speech_recognition as sr
except ModuleNotFoundError:
    sr = None

# 🔹 Path to corrected Excel file
EXCEL_PATH = "dataaas/odisha_diseases_39_with_updated_treatments.xlsx"
@st.cache_data
def load_disease_data(path):
    df = pd.read_excel(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if 'name' not in df.columns:
        st.error(f"Excel must have a column called 'name'. Found: {list(df.columns)}")
        st.stop()
    df['name'] = df['name'].astype(str).str.lower()
    
    # Ensure optional columns exist
    for col in ['medicines', 'herbal_remedies', 'red_flags', 'symptoms', 'care', 'transmission', 'prevention', 'treatment', 'refs', 'about']:
        if col not in df.columns:
            df[col] = ""
    
    return df

df = load_disease_data(EXCEL_PATH)

# ------------------------ Build symptom map ------------------------
symptom_map = defaultdict(list)
all_symptoms = set()

for _, r in df.iterrows():
    raw = str(r.get("symptoms", ""))
    for s in [x.strip().lower() for x in raw.split(",") if x.strip()]:
        symptom_map[s].append(r['name'])
        all_symptoms.add(s)

all_symptoms = sorted(all_symptoms)

# ------------------------ UI ------------------------
st.title("🩺 SwasthBot – Odisha Disease Info & Herbal + Medicine Info (SIH Version)")
st.caption("⚠️ Informational only – Always consult a qualified clinician for diagnosis or treatment.")

# ------------------------ Voice Input for Disease Search ------------------------
st.markdown("### 🎤 Voice Input for Disease Search")
voice_query = ""
if sr is not None and st.button("🎙️ Speak Disease Name"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Please speak now")
        audio = r.listen(source)
    try:
        voice_query = r.recognize_google(audio)
        st.success(f"You said: {voice_query}")
    except Exception as e:
        st.error(f"Could not understand audio: {e}")

# ------------------------ Text Input for Disease Search ------------------------
query = st.text_input("🔍 Search Disease by Name:", voice_query).strip().lower()

if query:
    matches = df[df['name'].str.contains(query, case=False, na=False)]
    if not matches.empty:
        row = matches.iloc[0]

        # Heading
        st.markdown(
            f"<h2>🦠 <span style='text-decoration: underline;'>{row['name'].upper()}</span></h2>",
            unsafe_allow_html=True
        )

        # Color-coded info with emojis
        if row.get("about"):  
            st.info(f"ℹ️ **About:** {row['about']}")
        if row.get("symptoms"):  
            st.info(f"📝 **Symptoms:** {row['symptoms']}")
        if row.get("red_flags"):  
            st.error(f"🚨 **Red-flag Signs:** {row['red_flags']}")
        if row.get("care"):  
            st.warning(f"⛑ **First Aid / Immediate Care:** {row['care']}")
        if row.get("transmission"):  
            st.info(f"🔁 **Transmission:** {row['transmission']}")
        if row.get("prevention"):  
            st.info(f"🛡️ **Prevention:** {row['prevention']}")
        if row.get("treatment"):  
            st.info(f"💊 **Treatment:** {row['treatment']}")
        if row.get("medicines"):  
            st.info(f"💊 **Local Medicines:** {row['medicines']}")
        if row.get("herbal_remedies"):  
            st.success(f"🌿 **Herbal Remedies:** {row['herbal_remedies']}")
        if row.get("refs"):  
            st.caption(f"📖 **References:** {row['refs']}")
    else:
        st.warning("❌ No disease found. Please check spelling.")

# ------------------------ Symptom Checker with scoring, risk, and voice ------------------------
st.markdown("### 🧠 Symptom Checker (Awareness Only)")

# Voice input for symptoms
symptom_voice = ""
if sr is not None and st.button("🎙️ Speak Symptoms (comma separated)"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Please speak now")
        audio = r.listen(source)
    try:
        symptom_voice = r.recognize_google(audio)
        st.success(f"You said: {symptom_voice}")
    except Exception as e:
        st.error(f"Could not understand audio: {e}")

# Multiselect for symptoms (manual + voice)
symptom_input = st.multiselect(
    "Select observed symptoms:", 
    all_symptoms,
    default=[s.strip().lower() for s in symptom_voice.split(",") if s.strip()]
)

if symptom_input:
    disease_scores = {}
    risk_levels = {}
    for _, row in df.iterrows():
        disease_symptoms = str(row['symptoms']).lower().split(",")
        disease_symptoms = [s.strip() for s in disease_symptoms if s.strip()]
        red_flags = str(row.get("red_flags","")).lower().split(",")
        red_flags = [s.strip() for s in red_flags if s.strip()]

        matched = set(symptom_input) & set(disease_symptoms)
        score = len(matched)
        if score > 0:
            disease_scores[row['name']] = score

            # Determine risk
            matched_red_flags = len(set(symptom_input) & set(red_flags))
            if matched_red_flags > 0:
                risk_levels[row['name']] = "High 🔴"
            elif score / max(len(disease_symptoms),1) > 0.5:
                risk_levels[row['name']] = "Medium 🟠"
            else:
                risk_levels[row['name']] = "Low 🟢"

    if disease_scores and px is not None:
        # Sort by score descending
        sorted_diseases = sorted(disease_scores.items(), key=lambda x: x[1], reverse=True)
        st.success("⚠️ Possible conditions based on symptoms (sorted by relevance):")
        for disease, score in sorted_diseases:
            st.markdown(f"- 🦠 **{disease.title()}** – matched symptoms: {score} – Risk Level: {risk_levels[disease]}")

        # Chart visualization with risk colors
        chart_df = pd.DataFrame([
            {"Disease": d, "Matched Symptoms": s, "Risk": risk_levels[d]} 
            for d, s in sorted_diseases
        ])
        color_map = {"High 🔴": "red", "Medium 🟠": "orange", "Low 🟢": "green"}
        fig = px.bar(chart_df, x="Disease", y="Matched Symptoms", color="Risk",
                     color_discrete_map=color_map, text="Matched Symptoms")
        st.plotly_chart(fig)
    else:
        st.info("No conditions match the selected symptoms.")
