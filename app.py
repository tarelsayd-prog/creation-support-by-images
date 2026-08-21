import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import requests
from PIL import Image
import time

# --- Configure the Page ---
st.set_page_config(page_title="Image-to-SKU Categorizer", layout="wide")
st.title("🖼️ AI Image-to-SKU Categorizer with Custom Taxonomy")

# --- API Key Setup ---
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("Please add your GEMINI_API_KEY to the Streamlit secrets.")

# --- Helper Function to Display and Download ---
def display_and_download(results_list):
    if results_list:
        df = pd.DataFrame(results_list)
        
        expected_columns = [
            "Source", "Title_EN", "Title_AR", "Family", "Type", "Subtype", 
            "Color_Family", "Color_Name", "Brand", "Size", 
            "Description_EN", "Description_AR", 
            "Feature_Bullet_1_EN", "Feature_Bullet_1_AR", 
            "Feature_Bullet_2_EN", "Feature_Bullet_2_AR", 
            "Feature_Bullet_3_EN", "Feature_Bullet_3_AR"
        ]
        columns_to_use = [col for col in expected_columns if col in df.columns]
        df = df[columns_to_use]
        
        st.success("Processing Complete!")
        st.dataframe(df, use_container_width=True)
        
        csv_export = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="Download Data as CSV",
            data=csv_export,
            file_name='processed_skus_with_taxonomy.csv',
            mime='text/csv',
        )

# --- App UI ---
st.write("1. Upload your Taxonomy Excel sheet. \n2. Upload your images or paste URLs.")

# 1. Taxonomy Upload
st.subheader("📚 Step 1: Upload Taxonomy")
taxonomy_file = st.file_uploader("Upload 'taxonomy for gemini.xlsx'", type=['xlsx', 'xls'])

taxonomy_json_string = ""
if taxonomy_file:
    try:
        tax_df = pd.read_excel(taxonomy_file)
        
        # Ensure column names match your Excel file exactly (based on my analysis)
        fam_col, type_col, sub_col = tax_df.columns[0], tax_df.columns[1], tax_df.columns[2]
        
        # Convert to a dictionary hierarchy: Family -> Type -> [Subtypes]
        taxonomy_dict = {}
        for family, group in tax_df.groupby(fam_col):
            taxonomy_dict[str(family)] = {}
            for p_type, sub_group in group.groupby(type_col):
                subtypes = sub_group[sub_col].dropna().astype(str).unique().tolist()
                taxonomy_dict[str(family)][str(p_type)] = subtypes
                
        # Convert to a compact JSON string to feed the AI
        taxonomy_json_string = json.dumps(taxonomy_dict)
        st.success(f"Taxonomy loaded! Found {len(taxonomy_dict)} Families.")
    except Exception as e:
        st.error(f"Error reading Taxonomy file: {e}")

# 2. Image Processing (Only show if taxonomy is loaded)
if taxonomy_json_string:
    st.subheader("🖼️ Step 2: Provide Images")
    
    # Generate the dynamic prompt based on the uploaded taxonomy
    DYNAMIC_IMAGE_PROMPT = f"""
    You are an expert inventory categorizer, e-commerce copywriter, and professional English-to-Arabic translator. 
    Analyze the provided product image. First, determine an appropriate short title for this product based on the image in English, and translate it to Arabic.

    CRITICAL: You must categorize the product using ONLY the Family, Type, and Subtype from the provided JSON Taxonomy Rules below. 
    You must find the most accurate Family. Then find the most accurate Type within that Family. Then find the most accurate Subtype within that Type.
    If it absolutely does not fit anything, output "(Not Toy)" or "(Unknown)".

    Taxonomy Rules (JSON Format):
    {taxonomy_json_string}

    Return a SINGLE JSON object with EXACTLY the following keys:
    - "Title_EN": Short title of the product in English
    - "Title_AR": Short title of the product translated into Arabic
    - "Family": Must strictly match a Family key from the Taxonomy Rules.
    - "Type": Must strictly match a Type key nested under the chosen Family in the Taxonomy Rules.
    - "Subtype": Must strictly match a Subtype string nested under the chosen Type in the Taxonomy Rules.
    - "Color_Family": Broad color category (e.g., Red, Blue). If not found, output "Not Found"
    - "Color_Name": Specific color shade. If not found, output "Not Found"
    - "Brand": Brand name if clearly visible. If not found, output "Not Found"
    - "Size": Size or dimensions if clearly visible. If not found, output "Not Found"
    - "Description_EN": Powerful, catchy one-paragraph e-commerce description in English
    - "Description_AR": Natural, highly engaging Arabic translation of the description
    - "Feature_Bullet_1_EN": Key feature/benefit 1 in English
    - "Feature_Bullet_1_AR": Arabic translation of feature 1
    - "Feature_Bullet_2_EN": Key feature/benefit 2 in English
    - "Feature_Bullet_2_AR": Arabic translation of feature 2
    - "Feature_Bullet_3_EN": Key feature/benefit 3 in English
    - "Feature_Bullet_3_AR": Arabic translation of feature 3
    """

    tab1, tab2 = st.tabs(["📤 Upload Images", "🔗 Paste Image URLs"])
    model = genai.GenerativeModel('gemini-3.5-flash-lite') if api_key else None

    # --- TAB 1: Direct File Upload ---
    with tab1:
        uploaded_files = st.file_uploader("Upload product images (PNG, JPG, JPEG, WEBP)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)
        if st.button("Process Uploaded Images"):
            if not uploaded_files:
                st.warning("Please upload at least one image.")
            elif not model:
                st.error("API Key missing.")
            else:
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing image {idx + 1} of {len(uploaded_files)}: {uploaded_file.name}...")
                    try:
                        img = Image.open(uploaded_file)
                        ai_response = model.generate_content(
                            [DYNAMIC_IMAGE_PROMPT, img],
                            generation_config={"response_mime_type": "application/json"}
                        )
                        data = json.loads(ai_response.text.strip())
                        data["Source"] = uploaded_file.name
                        results.append(data)
                    except Exception as e:
                        st.error(f"Failed to process {uploaded_file.name}: {e}")
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                    if idx < len(uploaded_files) - 1:
                        time.sleep(4.1)
                status_text.text("Finished processing all uploaded images!")
                display_and_download(results)

    # --- TAB 2: Image URLs ---
    with tab2:
        url_input = st.text_area("Enter Image URLs (one per line):", height=200)
        if st.button("Process Image URLs"):
            urls = [url.strip() for url in url_input.split('\n') if url.strip()]
            if not urls:
                st.warning("Please enter at least one URL.")
            elif not model:
                st.error("API Key missing.")
            else:
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                for idx, url in enumerate(urls):
                    status_text.text(f"Processing URL {idx + 1} of {len(urls)}...")
                    try:
                        response = requests.get(url, stream=True, timeout=10)
                        response.raise_for_status()
                        img = Image.open(response.raw)
                        ai_response = model.generate_content(
                            [DYNAMIC_IMAGE_PROMPT, img],
                            generation_config={"response_mime_type": "application/json"}
                        )
                        data = json.loads(ai_response.text.strip())
                        data["Source"] = url
                        results.append(data)
                    except Exception as e:
                        st.error(f"Failed to process URL: {url}\nError: {e}")
                    progress_bar.progress((idx + 1) / len(urls))
                    if idx < len(urls) - 1:
                        time.sleep(4.1)
                status_text.text("Finished processing all URLs!")
                display_and_download(results)
