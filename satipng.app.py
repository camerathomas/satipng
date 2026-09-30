import streamlit as st
import requests
import urllib.parse
import base64
from io import BytesIO
import time

# Pagina configuratie
st.set_page_config(page_title="Satirische verkeersbord generator", layout="wide")

st.title("🎨 Satirische verkeersbord generator")
st.caption("Gebaseerd op Pollinations gratis afbeeldingsgeneratie · Flux model")

# Invoergebied
artikel_tekst = st.text_area(
    "Plak hier de artikeltekst:",
    height=200,
    placeholder="Voer de nieuws- of artikelinhoud in die je wilt omzetten in een satirisch verkeersbord..."
)

# Aantal afbeeldingen
aantal = st.slider("Aantal afbeeldingen om te genereren", min_value=1, max_value=10, value=3)

# Generatieknop
if st.button("🚦 Genereer satirische verkeersborden", type="primary"):
    if not artikel_tekst.strip():
        st.warning("Voer eerst de artikeltekst in.")
    else:
        # Simpele prompt constructie: gebruik artikel als basis voor verkeersbord beschrijving
        # In de praktijk kun je hier een LLM aanroepen om het artikel samen te vatten en om te zetten in een visuele prompt
        basis_prompt = (
            f"A satirical traffic warning sign, clean vector illustration style, "
            f"centered composition, simple background. "
            f"Theme: {artikel_tekst[:200]}"
        )
        
        st.info(f"Prompt: {basis_prompt[:150]}...")
        
        voortgang = st.progress(0)
        resultaten = []
        
        for i in range(aantal):
            with st.spinner(f"Afbeelding {i+1}/{aantal} genereren..."):
                try:
                    # Pollinations API aanroep
                    encoded_prompt = urllib.parse.quote(basis_prompt)
                    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                    params = {
                        "width": 768,
                        "height": 768,
                        "model": "flux",
                        "nologo": "true",
                        "seed": i,  # Verschillende seed voor variatie
                    }
                    
                    response = requests.get(url, params=params, timeout=60)
                    
                    if response.status_code == 200:
                        # Converteer naar base64 voor directe weergave
                        img_base64 = base64.b64encode(response.content).decode()
                        resultaten.append(img_base64)
                    else:
                        st.warning(f"Afbeelding {i+1} mislukt: HTTP {response.status_code}")
                        
                except Exception as e:
                    st.warning(f"Afbeelding {i+1} fout: {e}")
                
                voortgang.progress((i + 1) / aantal)
                
                # Rate limit: 1 verzoek per 15 seconden
                if i < aantal - 1:
                    time.sleep(15)
        
        # Toon resultaten
        if resultaten:
            st.success(f"{len(resultaten)} afbeeldingen gegenereerd!")
            
            # Toon in grid (2 kolommen)
            cols = st.columns(2)
            for idx, img_b64 in enumerate(resultaten):
                with cols[idx % 2]:
                    st.image(f"data:image/jpeg;base64,{img_b64}", 
                            caption=f"Afbeelding {idx+1}",
                            use_container_width=True)
        else:
            st.error("Geen afbeeldingen gegenereerd. Probeer het later opnieuw.")
