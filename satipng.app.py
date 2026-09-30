import streamlit as st
import requests
import urllib.parse
import base64

st.set_page_config(page_title="Satirische verkeersbord generator", layout="centered")

st.title("🎨 Satirische verkeersbord generator")
st.caption("Genereer satirische verkeersborden op basis van een artikel")

# Sessie-state
if "laatste_afbeelding" not in st.session_state:
    st.session_state.laatste_afbeelding = None
if "laatste_prompt" not in st.session_state:
    st.session_state.laatste_prompt = ""
if "laatste_bron" not in st.session_state:
    st.session_state.laatste_bron = ""
if "teller" not in st.session_state:
    st.session_state.teller = 0

# Cloudflare instellingen (via Streamlit secrets)
try:
    CF_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]
    CF_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]
    CF_BESCHIKBAAR = True
except Exception:
    CF_BESCHIKBAAR = False

# Invoerveld
artikel_tekst = st.text_area(
    "Plak hier de artikeltekst:",
    height=200,
    placeholder="Voer de nieuws- of artikelinhoud in...",
)

# Optioneel: eigen stijl toevoegen
extra_prompt = st.text_input(
    "Extra stijl (optioneel):",
    placeholder="bijv. 'minimalistisch', 'donkere achtergrond', 'handgetekend'",
)

# Bouw de prompt
def bouw_prompt(artikel, extra=""):
    prompt = (
        "You are a satirical cartoonist for a newspaper. "
        "Create one image based on the article text below. "
        "Your trademark: you take a recognizable traffic sign and tilt its meaning "
        "with one simple graphic twist, so the sign tells a hilarious or painful "
        "truth about the article. "
        "Approach: (1) Read the article and determine the core in one sentence. "
        "(2) Find an existing traffic sign whose shape, pictogram, or meaning comes "
        "close to that core. (3) Replace or distort one element of that sign so the "
        "satire becomes visible. (4) Add a caption in the style of a traffic sign: "
        "'Forbidden to ...', 'Stop for the ...', 'Warning! Low-flying ...'. "
        "Visual style: use the red border of triangular or round traffic signs as a "
        "recognizable element. Simple, graphic, vector-like. White background, black "
        "and red lines. One clear pictogram, no cluttered details. The caption is "
        "placed below or inside the sign, in short, readable text. "
        f"Article: {artikel[:500]}"
    )
    if extra.strip():
        prompt += f" Extra style: {extra}"
    return prompt

# ============================================
# POLLINATIONS
# ============================================

def genereer_pollinations(prompt):
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}"
    params = {
        "width": 768,
        "height": 768,
        "model": "flux",
        "nologo": "true",
        "seed": st.session_state.teller,
    }
    response = requests.get(url, params=params, timeout=60)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode(), None
    return None, f"HTTP {response.status_code}"

# ============================================
# CLOUDFLARE WORKERS AI
# ============================================

def genereer_cloudflare(prompt):
    if not CF_BESCHIKBAAR:
        return None, "Cloudflare credentials ontbreken in secrets."
    model = "@cf/black-forest-labs/flux-1-schnell"
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{model}"
    payload = {
        "prompt": prompt,
        "steps": 4,
    }
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        if response.status_code == 200:
            data = response.json()
            img_b64 = data.get("result", {}).get("image")
            if img_b64:
                return img_b64, None
            return None, f"Onverwachte response: {data}"
        return None, f"HTTP {response.status_code}: {response.text[:300]}"
    except Exception as e:
        return None, str(e)

# ============================================
# KNOPPEN
# ============================================

col1, col2 = st.columns(2)

with col1:
    knop_pollinations = st.button("🚦 Genereer met Pollinations", type="primary", use_container_width=True)

with col2:
    knop_cloudflare = st.button("☁️ Genereer met Cloudflare", type="secondary", use_container_width=True)

# ============================================
# GENERATIE
# ============================================

if (knop_pollinations or knop_cloudflare) and artikel_tekst.strip():
    prompt = bouw_prompt(artikel_tekst, extra_prompt)

    if knop_pollinations:
        with st.spinner("Pollinations: afbeelding genereren..."):
            img_b64, fout = genereer_pollinations(prompt)
            bron = "Pollinations"
    else:
        with st.spinner("Cloudflare: afbeelding genereren..."):
            img_b64, fout = genereer_cloudflare(prompt)
            bron = "Cloudflare Workers AI"

    if img_b64:
        st.session_state.laatste_afbeelding = img_b64
        st.session_state.laatste_prompt = prompt
        st.session_state.laatste_bron = bron
        st.session_state.teller += 1
    else:
        st.error(f"Generatie mislukt ({bron}): {fout}")

elif (knop_pollinations or knop_cloudflare) and not artikel_tekst.strip():
    st.warning("Voer eerst de artikeltekst in.")

# ============================================
# WEERGAVE
# ============================================

if st.session_state.laatste_afbeelding:
    st.markdown(f"**Bron:** {st.session_state.laatste_bron}")
    st.image(
        f"data:image/jpeg;base64,{st.session_state.laatste_afbeelding}",
        caption="Laatste gegenereerde bord",
        use_container_width=True,
    )

    st.download_button(
        label="⬇️ Download afbeelding",
        data=base64.b64decode(st.session_state.laatste_afbeelding),
        file_name=f"verkeersbord_{st.session_state.laatste_bron.lower().replace(' ', '_')}_{st.session_state.teller}.jpg",
        mime="image/jpeg",
    )

    with st.expander("Gebruikte prompt"):
        st.write(st.session_state.laatste_prompt)
