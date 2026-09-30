import streamlit as st
import requests
import urllib.parse
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Parodie verkeersbord generator", layout="centered")

st.title("🚦 Parodie verkeersbord generator")
st.caption("Genereer een parodie op een verkeersbord op basis van een artikel en een onderschrift")

# Sessie-state
if "laatste_afbeelding" not in st.session_state:
    st.session_state.laatste_afbeelding = None
if "laatste_prompt" not in st.session_state:
    st.session_state.laatste_prompt = ""
if "laatste_bron" not in st.session_state:
    st.session_state.laatste_bron = ""
if "laatste_onderschrift" not in st.session_state:
    st.session_state.laatste_onderschrift = ""
if "teller" not in st.session_state:
    st.session_state.teller = 0

# Cloudflare instellingen
try:
    CF_ACCOUNT_ID = st.secrets["CLOUDFLARE_ACCOUNT_ID"]
    CF_API_TOKEN = st.secrets["CLOUDFLARE_API_TOKEN"]
    CF_BESCHIKBAAR = True
except Exception:
    CF_BESCHIKBAAR = False

# Invoervelden
artikel_tekst = st.text_area(
    "Plak hier de artikeltekst (context):",
    height=180,
    placeholder="Voer de nieuws- of artikelinhoud in...",
)

onderschrift = st.text_input(
    "Onderschrift (bepaalt het bord):",
    placeholder="bijv. 'Verboden om te tanken op maandag' of 'Pas op! Laag overvliegende drones'",
)

extra_prompt = st.text_input(
    "Extra stijl (optioneel):",
    placeholder="bijv. 'minimalistisch', 'donkere achtergrond'",
)

# Bouw de prompt — onderschrift stuurt het bord
def bouw_prompt(artikel, onderschrift, extra=""):
    prompt = (
        "You are a cartoonist for a newspaper. You draw only, you do not use text."
        "Create a parody of a recognizable traffic sign. "
        "Approach: (1) Read the text carefully. "
        "(2) Pick an existing traffic sign whose shape or pictogram fits the text. "
        "(3) Change the existing traffic sign just slightly so we understand the message, the joke. "
        "(4) Add another visual symbol that connects to the text to finalize the joke."
        "Visual style: red border of a triangular or round traffic sign, white background, "
        "black pictogram, flat vector illustration, minimal, clean. "
        "Use visual graphics only, no letters, text is forbidden. "
        f"Article (for context): {artikel[:300]}"
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
        return response.content, None
    return None, f"HTTP {response.status_code}"

# ============================================
# CLOUDFLARE WORKERS AI
# ============================================

def genereer_cloudflare(prompt):
    if not CF_BESCHIKBAAR:
        return None, "Cloudflare credentials ontbreken in secrets."
    model = "@cf/black-forest-labs/flux-1-schnell"
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{model}"
    payload = {"prompt": prompt, "steps": 4}
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
                return base64.b64decode(img_b64), None
            return None, f"Onverwachte response: {data}"
        return None, f"HTTP {response.status_code}: {response.text[:300]}"
    except Exception as e:
        return None, str(e)

# ============================================
# PILLOW — onderschrift toevoegen
# ============================================

def voeg_onderschrift_toe(afbeelding_bytes, tekst):
    """Voeg een onderschrift toe onder de afbeelding."""
    img = Image.open(BytesIO(afbeelding_bytes)).convert("RGB")
    breedte, hoogte = img.size

    marge_onder = 180
    nieuwe_hoogte = hoogte + marge_onder
    nieuwe_img = Image.new("RGB", (breedte, nieuwe_hoogte), "white")
    nieuwe_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(nieuwe_img)

    # Lettertype zoeken
    font = None
    for pad in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(pad, 40)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Tekst opsplitsen in regels (max ~30 tekens per regel)
    woorden = tekst.split()
    regels = []
    huidige = ""
    for w in woorden:
        test = (huidige + " " + w).strip()
        if len(test) <= 34:
            huidige = test
        else:
            if huidige:
                regels.append(huidige)
            huidige = w
    if huidige:
        regels.append(huidige)

    # Tekst centreren
    regel_hoogte = 50
    totaal_hoogte = regel_hoogte * len(regels)
    y = hoogte + (marge_onder - totaal_hoogte) // 2

    for regel in regels:
        bbox = draw.textbbox((0, 0), regel, font=font)
        tekst_breedte = bbox[2] - bbox[0]
        x = (breedte - tekst_breedte) // 2
        draw.text((x, y), regel, fill="black", font=font)
        y += regel_hoogte

    buffer = BytesIO()
    nieuwe_img.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()

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

if (knop_pollinations or knop_cloudflare):
    if not artikel_tekst.strip():
        st.warning("Voer eerst de artikeltekst in.")
    elif not onderschrift.strip():
        st.warning("Voer eerst een onderschrift in.")
    else:
        prompt = bouw_prompt(artikel_tekst, onderschrift, extra_prompt)

        if knop_pollinations:
            with st.spinner("Pollinations: bord genereren..."):
                img_bytes, fout = genereer_pollinations(prompt)
                bron = "Pollinations"
        else:
            with st.spinner("Cloudflare: bord genereren..."):
                img_bytes, fout = genereer_cloudflare(prompt)
                bron = "Cloudflare Workers AI"

        if img_bytes:
            with st.spinner("Onderschrift toevoegen..."):
                img_bytes = voeg_onderschrift_toe(img_bytes, onderschrift.strip())

            st.session_state.laatste_afbeelding = base64.b64encode(img_bytes).decode()
            st.session_state.laatste_prompt = prompt
            st.session_state.laatste_bron = bron
            st.session_state.laatste_onderschrift = onderschrift.strip()
            st.session_state.teller += 1
        else:
            st.error(f"Generatie mislukt ({bron}): {fout}")

# ============================================
# WEERGAVE
# ============================================

if st.session_state.laatste_afbeelding:
    st.markdown(f"**Bron:** {st.session_state.laatste_bron}")
    st.markdown(f"**Onderschrift:** *{st.session_state.laatste_onderschrift}*")
    st.image(
        f"data:image/jpeg;base64,{st.session_state.laatste_afbeelding}",
        caption="Laatste gegenereerde bord",
        use_container_width=True,
    )

    st.download_button(
        label="⬇️ Download afbeelding",
        data=base64.b64decode(st.session_state.laatste_afbeelding),
        file_name=f"verkeersbord_{st.session_state.teller}.jpg",
        mime="image/jpeg",
    )

    with st.expander("Gebruikte prompt"):
        st.write(st.session_state.laatste_prompt)
