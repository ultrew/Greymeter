# app.py

import streamlit as st
from PIL import Image
import os
import json

from stego_detector import (
    calculate_hashes, get_metadata, detect_hidden_data,
    extract_text, run_file_command, run_binwalk,
    run_steghide_extract, run_binwalk_extract_and_zip,
    carve_appended_file
)

st.set_page_config(page_title="Greymeter", page_icon="🕵️", layout="wide")
st.title("🕵️ Greymeter 1.0")
st.write("Greymeter is a multi level forensic tool which uses tools like hash, file, exif tool, binwalk, steghide to uncover the secrets of your file.")

uploaded_file = st.file_uploader("Choose a file", type=["png", "jpg", "jpeg", "bmp", "pdf", "docx"])

if uploaded_file is not None:
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 2])

    with col1:
        is_image = file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        if is_image:
            st.subheader("Uploaded Image")
            st.image(uploaded_file, caption="Image to be analyzed", use_container_width=True)
        else:
            st.subheader("Uploaded File")
            st.write(f"**Filename:** {uploaded_file.name}")
        
        st.subheader("File Properties")
        hashes = calculate_hashes(file_path)
        st.write(f"**MD5:** `{hashes['md5']}`")
        st.write(f"**SHA1:** `{hashes['sha1']}`")
        st.write(f"**SHA256:** `{hashes['sha256']}`")
        
        if is_image:
            image = Image.open(uploaded_file)
            metadata = get_metadata(image)
            with st.expander("Show EXIF Metadata"):
                if metadata: st.json(metadata)
                else: st.write("No EXIF metadata found.")
    
    with col2:
        st.subheader("Analysis Results")
        
        if is_image:
            is_suspect, p_value = detect_hidden_data(image)
            extracted_text_lsb = extract_text(file_path)
            if extracted_text_lsb:
                st.text_area("Extracted LSB Message (if any)", extracted_text_lsb, height=100)
        
        with st.container(border=True):
            st.markdown("#### Forensic Carving & Extraction")
            file_output = run_file_command(file_path)
            st.code(f"File Type Information:\n{file_output}", language='bash')
            
            binwalk_summary = run_binwalk(file_path)
            st.code(f"Binwalk Analysis:\n{binwalk_summary}", language='bash')
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Attempt Binwalk Extraction (.zip)"):
                    with st.spinner("Running `binwalk -eM`..."):
                        zip_path = run_binwalk_extract_and_zip(file_path)
                        if zip_path and os.path.exists(zip_path):
                            with open(zip_path, "rb") as fp:
                                st.download_button(label="Download Binwalk Extraction.zip", data=fp, file_name="binwalk_extraction.zip", mime="application/zip")
                            os.remove(zip_path)
                        else:
                            st.info("Binwalk analysis complete. No distinct files were carved out.")
            with c2:
                if st.button("Carve Appended File (dd)"):
                    with st.spinner("Carving file based on offset..."):
                        carved_file = carve_appended_file(file_path, binwalk_summary)
                        if carved_file and os.path.exists(carved_file):
                            with open(carved_file, "rb") as fp:
                                st.download_button(label=f"Download Carved File ({os.path.basename(carved_file)})", data=fp, file_name=os.path.basename(carved_file), mime="application/octet-stream")
                            os.remove(carved_file)
                        else: st.error("Could not find an appended file to carve.")
            
            if is_image:
                steghide_summary, steghide_file_path = run_steghide_extract(file_path)
                st.code(f"Steghide Extraction Attempt:\n{steghide_summary}", language='bash')
                if steghide_file_path and os.path.exists(steghide_file_path):
                    with open(steghide_file_path, "rb") as fp:
                        st.download_button(label=f"Download Steghide Extracted File ({os.path.basename(steghide_file_path)})", data=fp, file_name=os.path.basename(steghide_file_path), mime="application/octet-stream")
                    os.remove(steghide_file_path)

    # Full report still contains all analysis data
    if os.path.exists(file_path): os.remove(file_path)