import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import requests
from PIL import Image

# --- Configure the Page ---
st.set_page_config(page_title="Image-to-SKU Categorizer", layout="centered")
st.title("🖼️ AI Image-to-SKU Categorizer (Multilingual)")

# --- API Key Setup ---
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("Please add your GEMINI_API_KEY to the Streamlit secrets.")

# --- The Master Prompt ---
IMAGE_PROMPT = """
You are an expert inventory categorizer, e-commerce copywriter, and professional English-to-Arabic translator. 
Analyze the provided product image. First, determine an appropriate short "Title" for this product based on the image. 
Then, output EXACTLY ONE LINE of CSV data representing this product. Do NOT include a header row.

Columns order (11 columns total):
Title, Type, Subtype, Description_EN, Description_AR, Feature_Bullet_1_EN, Feature_Bullet_1_AR, Feature_Bullet_2_EN, Feature_Bullet_2_AR, Feature_Bullet_3_EN, Feature_Bullet_3_AR

Rules:
1. Strictly use only the Types and Subtypes listed below. If it is not a toy, use (Not Toy) for Type and Subtype.
2. Description_EN: Write a powerful and catchy one-paragraph product description based on what you see.
3. Description_AR: Write an accurate and highly engaging Arabic translation of the description.
4. Feature_Bullet_1_EN to Feature_Bullet_3_EN: Write three distinct, compelling key features based on the image.
5. Feature_Bullet_1_AR to Feature_Bullet_3_AR: Provide accurate Arabic translations for the three feature bullets.
6. CRITICAL: Return ONLY valid CSV data (a single comma-separated line). Enclose any text containing commas or newlines in double quotes ("") so that it does not break the CSV layout. Do NOT include markdown blocks like ```csv.

Types and Subtypes:
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
st.write("Paste your image URLs below. The AI will look at the photos, figure out what the products are, categorize them, and generate multilingual descriptions!")

url_input = st.text_area("Enter Image URLs (one per line):", height=200)

if st.button("Process Images & Generate Content"):
    urls = [url.strip() for url in url_input.split('\n') if url.strip()]
    
    if not urls:
        st.warning("Please enter at least one Image URL.")
    else:
        # Define the headers for our final output
        headers = "Title,Type,Subtype,Description_EN,Description_AR,Feature_Bullet_1_EN,Feature_Bullet_1_AR,Feature_Bullet_2_EN,Feature_Bullet_2_AR,Feature_Bullet_3_EN,Feature_Bullet_3_AR"
        all_csv_rows = [headers]
        
        # Using the model you established
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        
        # Create a visual progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(urls):
            status_text.text(f"Processing image {idx + 1} of {len(urls)}...")
            
            try:
                # 1. Download the image from the URL
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status() # Check for broken links
                img = Image.open(response.raw)
                
                # 2. Show the image and the prompt to the AI
                ai_response = model.generate_content([IMAGE_PROMPT, img])
                
                # 3. Save the single row of CSV data it generates
                row_data = ai_response.text.strip()
                all_csv_rows.append(row_data)
                
            except Exception as e:
                st.error(f"Failed to process URL: {url}\nError: {e}")
                
            # Update the progress bar
            progress_bar.progress((idx + 1) / len(urls))
            
        status_text.text("Finished processing all images!")
        
        # Combine all rows and convert into a Pandas DataFrame
        final_csv_data = "\n".join(all_csv_rows)
        
        try:
            df = pd.read_csv(io.StringIO(final_csv_data))
            
            # Display the table
            st.success("Processing Complete!")
            st.dataframe(df, use_container_width=True)
            
            # Allow user to download the table
            csv_export = df.to_csv(index=False).encode('utf-8-sig') 
            st.download_button(
                label="Download Data as CSV",
                data=csv_export,
                file_name='image_processed_skus.csv',
                mime='text/csv',
            )
        except Exception as e:
            st.error(f"Error parsing final data. AI might have formatted it wrong: {e}")