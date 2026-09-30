import streamlit as st
import requests
import urllib.parse
import base64

st.set_page_config(page_title="Satirische verkeersbord generator", layout="centered")

st.title("🎨 Satirische verkeersbord generator")
st.caption("Gebaseerd op Pollinations gratis afbeeldingsgeneratie · Flux model")

# Sessie-state
if "laatste_afbeelding" not in st.session_state:
    st.session_state.laatste_afbeelding = None
if "laatste_prompt" not in st.session_state:
    st.session_state.laatste_prompt = ""
if "teller" not in st.session_state:
    st.session_state.teller = 0

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

# Genereer-knop
if st.button("🚦 Genereer verkeersbord", type="primary"):
    if not artikel_tekst.strip():
        st.warning("Voer eerst de artikeltekst in.")
    else:
        basis_prompt = (
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
            f"Article: {artikel_tekst[:500]}"
        )
        if extra_prompt.strip():
            basis_prompt += f" Extra style: {extra_prompt}"

        with st.spinner("Afbeelding genereren..."):
            try:
                encoded_prompt = urllib.parse.quote(basis_prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                params = {
                    "width": 768,
                    "height": 768,
                    "model": "flux",
                    "nologo": "true",
                    "seed": st.session_state.teller,
                }

                response = requests.get(url, params=params, timeout=60)

                if response.status_code == 200:
                    img_base64 = base64.b64encode(response.content).decode()
                    st.session_state.laatste_afbeelding = img_base64
                    st.session_state.laatste_prompt = basis_prompt
                    st.session_state.teller += 1
                else:
                    st.error(f"Generatie mislukt: HTTP {response.status_code}")

            except Exception as e:
                st.error(f"Fout: {e}")

# Toon de laatste afbeelding
if st.session_state.laatste_afbeelding:
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
