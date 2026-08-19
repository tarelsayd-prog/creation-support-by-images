import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from PIL import Image
import time

# --- Configure the Page ---
st.set_page_config(page_title="Image-to-SKU Categorizer", layout="centered")
st.title("🖼️ AI Image-to-SKU Categorizer (Direct Upload)")

# --- API Key Setup ---
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("Please add your GEMINI_API_KEY to the Streamlit secrets.")

# --- The Master Prompt ---
IMAGE_PROMPT = """
You are an expert inventory categorizer, e-commerce copywriter, and professional English-to-Arabic translator. 
Analyze the provided product image. First, determine an appropriate short title for this product based on the image in English, and translate it to Arabic.

Return a SINGLE JSON object with EXACTLY the following keys:
- "Title_EN": Short title of the product in English
- "Title_AR": Short title of the product translated into Arabic
- "Type": Must be strictly selected from the allowed Types below (or "(Not Toy)")
- "Subtype": Must be strictly selected from the allowed Subtypes below (or "(Not Toy)")
- "Color_Family": Broad color category (e.g., Red, Blue, Neutral, Multi, etc.). If not applicable or not found, output "Not Found"
- "Color_Name": Specific color shade (e.g., Navy Blue, Crimson, Pastel Pink). If not found, output "Not Found"
- "Brand": Brand name if clearly visible on the product or packaging. If not found, output "Not Found"
- "Size": Size or dimensions if clearly visible (e.g., Large, 50cm, 12 inch). If not found, output "Not Found"
- "Description_EN": Powerful, catchy one-paragraph e-commerce description in English
- "Description_AR": Natural, highly engaging Arabic translation of the description
- "Feature_Bullet_1_EN": Key feature/benefit 1 in English
- "Feature_Bullet_1_AR": Arabic translation of feature 1
- "Feature_Bullet_2_EN": Key feature/benefit 2 in English
- "Feature_Bullet_2_AR": Arabic translation of feature 2
- "Feature_Bullet_3_EN": Key feature/benefit 3 in English
- "Feature_Bullet_3_AR": Arabic translation of feature 3

Rules for Types & Subtypes:
- Pretend Play: Beauty Playsets, Tools, Magnet & Felt Playboards, Shops & Accessories, Money & Banking, Doctor Playsets, Household Toys, Kitchen & Food
- Sports & Outdoor Play: Inflatable Pool Ride On, Pool Toys and Games, Trampolines, Playhouses, Baby Floats & Float Suits, Sand & Water Tables, Sports, Balls, Pools, Gym Sets & Swings, Blasters & Foam Play, Beanbags & Foot Bags, Play Tents & Tunnels, Boats, Kites & Wind Spinners, Beach Toys, Bubbles, Pool Covers & Accessories, Kickball & Playground Balls, Swim Ring, Rafts, Yo-yos, Lawn Games, Fitness Equipment, Water Slides, Ball Pits and Accessories, Play Sets & Playground Equipment, Inflatable Bouncers, Water Blasters & Soakers
- Hobbies: Models & Model Kits, RC Helicopters, RC Motorcycles, RC Cars & Trucks, RC Ships & Submarines, Slot Cars Race Tracks & Accessories, Hobby RC Vehicles & Parts, Stamp Collecting, RC Trains, RC Quadcopters, Scaled Model Vehicles, RC Vehicles & Parts, Trains & Accessories, Radio Control, RC Animals & Robots, Model Building Kits & Tools, Hobby Building Tools & Hardware, Coin Collecting, RC Airplanes
- Figures & Statues: Accessories, Statues & Bobbleheads, Action Figures, Playsets, Animal Figures
- Toy Play Vehicles: Vehicle Playsets, Trains & Railway Sets, RC Vehicles & Batteries, Play Vehicles, Die-cast Vehicles, Race Tracks
- Puzzles: Brain Teasers, Jigsaw Puzzles, Floor Puzzles, Pegged Puzzles, 3D Puzzles
- Arts & Crafts: Printing & Stamping, Craft Kits, Easels, Drawing & Painting Supplies, Beads, Stickers, Blackboards & Whiteboards, Clay & Dough
- Learning & Education: Early Development Toys, Mathematics & Counting, Solar, Flash Cards, Reading & Writing, Geography, Basic & Life Skills Toys, Musical Instruments, Science, Electronics
- Tricycles, Scooters & Wagons: Skates, Skateboards, Kids Bikes, Kids Helmets, Ride-on Toys, Kids Kick Scooter, Kids Scooter Parts & Accessories, Kids Protective Gear, Electric Ride ons, Tricycles, Kids Hoverboard, Kids Drift Scooter, Bike Accessories
- Baby & Toddler Toys: Activity Centers, Music & Sound, Stacking & Nesting Toys, Shape Sorters, Hammering & Pounding Toys, Baby Gyms & Playmats, Push & Pull Toys, Bath Toys, Indoor Climbers & Play Structures, Blocks, Crib Toys & Attachments, Rocking & Spring Ride-ons, Car Seat & Stroller Toys, Rattles, Stuffed Animals & Toys
- Party Supplies: Party Packs, Candles, Party Tableware, Cake Supplies, Party Games & Crafts, Balloons, Pinatas, Tablecovers & Centerpieces, Holi Colour, Party Hats, Banners Streamers & Confetti, Noisemakers, Invitations & Cards, Party Favors
- Stuffed Animals & Plush: Plush Backpacks & Purses, Teddy Bears, Plush Pillows, Plush Puppets, Puppets, Animals & Figures
- Dressing Up & Costumes: Costumes, Costume Accessories
- Dolls & Accessories: Playsets & Figures, Dollhouses, Soft Dolls, Doll Accessories, Baby Dolls, Dollhouse Accessories, Fashion Dolls
- Building Toys: Building Sets, Stacking Blocks
- Novelty Toys: Squishy toys, Slime & Putty Toys, Nesting Dolls, Miniatures, Finger Boards & Finger Bikes, Viewfinders, Prisms & Kaleidoscopes, Wind-Up Toys, Gag Toys & Practical Jokes, Fidget Spinners, Pop Bubble Fidget, Magic Kits & Accessories, Money Banks, Light-Up Toys, Magnets & Magnetic Toys, Temporary Tattoos, Shaped Rubber Wristbands, Toy Balls
- Games: Handheld Games, Standard Playing Card Decks, Dice & Gaming Dice, Board Games, Game Accessories, Card Games, Trading Cards, Battling Tops
- Electronics For Kids: Plug & Play Video Games, Music Players & Karaoke, Electronic Pets, Rc Figures & Robots, Electronic Toys, Cameras & Camcorders
"""

# --- App UI ---
st.write("Drag and drop your product images below. The AI will analyze them, categorize the products, and generate bilingual descriptions!")

# Use Streamlit's file uploader instead of text area
uploaded_files = st.file_uploader("Upload product images (PNG, JPG, JPEG, WEBP)", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)

if st.button("Process Images & Generate Content"):
    if not uploaded_files:
        st.warning("Please upload at least one image.")
    else:
        results = []
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing image {idx + 1} of {len(uploaded_files)}: {uploaded_file.name}...")
            
            try:
                # 1. Open the uploaded image file directly
                img = Image.open(uploaded_file)
                
                # 2. Call Gemini with JSON response mode
                ai_response = model.generate_content(
                    [IMAGE_PROMPT, img],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # 3. Parse JSON safely and add the filename as a column for reference
                data = json.loads(ai_response.text.strip())
                data["File_Name"] = uploaded_file.name # Keeps track of which image is which
                results.append(data)
                
            except Exception as e:
                st.error(f"Failed to process image: {uploaded_file.name}\nError: {e}")
                
            # Update the progress bar
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
            # 4. SAFETY PAUSE: Wait ~4 seconds to avoid hitting the 15/minute Free Tier limit
            if idx < len(uploaded_files) - 1:
                time.sleep(4.1)
            
        status_text.text("Finished processing all images!")
        
        if results:
            # Build DataFrame directly from clean JSON dicts
            df = pd.DataFrame(results)
            
            # Ensure columns are arranged logically, adding the File_Name at the very beginning
            expected_columns = [
                "File_Name", "Title_EN", "Title_AR", "Type", "Subtype", "Color_Family", "Color_Name", 
                "Brand", "Size", "Description_EN", "Description_AR", 
                "Feature_Bullet_1_EN", "Feature_Bullet_1_AR", 
                "Feature_Bullet_2_EN", "Feature_Bullet_2_AR", 
                "Feature_Bullet_3_EN", "Feature_Bullet_3_AR"
            ]
            columns_to_use = [col for col in expected_columns if col in df.columns]
            df = df[columns_to_use]
            
            # Display the table
            st.success("Processing Complete!")
            st.dataframe(df, use_container_width=True)
            
            # Allow user to download CSV formatted with utf-8-sig for proper Arabic text in Excel
            csv_export = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="Download Data as CSV",
                data=csv_export,
                file_name='uploaded_images_processed_skus.csv',
                mime='text/csv',
            )
