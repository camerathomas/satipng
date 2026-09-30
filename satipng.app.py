import streamlit as st
import requests
import urllib.parse
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Parodie verkeersbord generator", layout="centered")

st.title("🚦 Parodie verkeersbord generator")
st.caption("Genereer een parodie op een verkeersbord op basis van een artikel")

# Sessie-state
if "laatste_afbeelding" not in st.session_state:
    st.session_state.laatste_afbeelding = None
if "laatste_prompt" not in st.session_state:
    st.session_state.laatste_prompt = ""
if "laatste_bron" not in st.session_state:
    st.session_state.laatste_bron = ""
if "teller" not in st.session_state:
    st.session_state.teller = 0

# Cloudflare instellingen
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

# Bouw de prompt
def bouw_prompt(artikel, extra=""):
    prompt = (
        "Ontwerp een satirisch verkeersbord dat het artikel samenvat. "
        "Het bord is een parodie op een bestaand Nederlands verkeersbord. "
        "KIES EEN VORM: "
        "- Driehoek met rode rand = gevaar. "
        "- Rond met rode rand = verbod. "
        "- Rond met blauwe achtergrond = gebod. "
        "- Rechthoek = informatie. "
        "- Achthoek = stop. "
        "- Richtingaanwijzer = richting of keuze. "
        "REGELS: "
        "- Gebruik de vorm die past bij de kern van het artikel. "
        "- Gebruik GEEN tekst op het bord, behalve als het bord 'STOP' is. "
        "- Het bord werkt met een SYMBOOL, niet met woorden. "
        "- Het symbool is eenvoudig en herkenbaar. "
        "- Denk aan: pijlen, kruisen, uitroeptekens, voetgangers, dieren, voertuigen, handen, ogen, monden. "
        "- Het symbool mag absurd of satirisch zijn, maar moet in één oogopslag te begrijpen zijn. "
        "- Het geheel is grappig, niet beledigend. "
        "- Geen politieke partijen, geen personen bij naam. "
        "- Gebruik alleen eenvoudige SVG-vormen (cirkels, driehoeken, rechthoeken, lijnen, paden). "
        "- Geen externe fonts, geen externe afbeeldingen. "
        f"Artikel: {artikel[:500]}"
    )
    if extra.strip():
        prompt += f" Extra stijl: {extra}"
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
# PILLOW — onderschrift
# ============================================

def voeg_onderschrift_toe(afbeelding_bytes, tekst):
    img = Image.open(BytesIO(afbeelding_bytes)).convert("RGB")
    breedte, hoogte = img.size

    marge = 130
    nieuwe_img = Image.new("RGB", (breedte, hoogte + marge), "white")
    nieuwe_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(nieuwe_img)

    font = None
    for pad in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(pad, 48)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), tekst, font=font)
    tekst_breedte = bbox[2] - bbox[0]
    tekst_hoogte = bbox[3] - bbox[1]

    x = (breedte - tekst_breedte) // 2
    y = hoogte + (marge - tekst_hoogte) // 2

    draw.text((x, y), tekst, fill="black", font=font)

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

if (knop_pollinations or knop_cloudflare) and artikel_tekst.strip():
    prompt = bouw_prompt(artikel_tekst)

    if knop_pollinations:
        with st.spinner("Pollinations: bord genereren..."):
            img_bytes, fout = genereer_pollinations(prompt)
            bron = "Pollinations"
    else:
        with st.spinner("Cloudflare: bord genereren..."):
            img_bytes, fout = genereer_cloudflare(prompt)
            bron = "Cloudflare Workers AI"

    if img_bytes:
        st.session_state.laatste_afbeelding = base64.b64encode(img_bytes).decode()
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
        file_name=f"verkeersbord_{st.session_state.teller}.jpg",
        mime="image/jpeg",
    )

    with st.expander("Gebruikte prompt"):
        st.write(st.session_state.laatste_prompt)
