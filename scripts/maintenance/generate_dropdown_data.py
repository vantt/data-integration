import pandas as pd
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEEDS_DIR = os.path.join(BASE_DIR, 'transformation', 'seeds')
OUTPUT_DIR = os.path.join(BASE_DIR, 'scripts', 'maintenance', 'output')

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_csv(filename):
    return pd.read_csv(os.path.join(SEEDS_DIR, filename))

def generate_spend_items():
    print("Generating Spend Items Dropdown...")
    df = load_csv('ref_marketing_spend_map.csv')
    
    # We want: Display Name -> Spend Code
    # The file has: spend_code, display_name, ...
    
    output = df[['display_name', 'spend_code']].copy()
    output.columns = ['Display Name', 'Spend Code']
    
    output_path = os.path.join(OUTPUT_DIR, 'spend_items_dropdown.csv')
    output.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")
    print(output.head())

def generate_channels():
    print("\nGenerating Channels Dropdown...")
    sources = load_csv('ref_order_sources.csv')
    locations = load_csv('ref_branch_locations.csv')
    
    channels = []
    
    # Logic matching dim_channels.sql
    
    # 1. Specific Channels (Non-Generic)
    specific = sources[sources['is_generic_source'] == False]
    for _, row in specific.iterrows():
        channels.append({
            'Display Name': row['name'],
            'Channel Ref': f"{row['id']}|", # source_id|location_id (empty)
            'Type': 'Specific'
        })
        
    # 2. Generic Channels (POS -> Locations)
    generic = sources[sources['is_generic_source'] == True]
    
    # We cross join generic sources with locations
    # Usually only POS (Retail) needs location expansion? 
    # dim_channels.sql cross joins ALL generic sources with ALL branch_locations.
    # Let's inspect generic sources.
    
    for _, source_row in generic.iterrows():
        # For 'Pos' (id 3988157), we definitely need locations.
        # For 'Shopee' (id 3988158), it says 'is_generic_source' = True in the CSV I saw?
        # Let's check the CSV content from previous turns.
        # Line 24: 3988158,Shopee,true,Ecom,false,Shopee,
        # Line 25: 3988157,Pos,true,Retail,true,Retail,
        # Wait, check 'is_generic_source' column index.
        # Header: id,name,status,channel_format,is_generic_source,platform,mapping_tag
        # Shopee (3988158): is_generic_source is 'true'? 
        # Line 24 in view_file output: `3988158,Shopee,true,Ecom,false,Shopee,`
        # status=true, channel_format=Marketplace, is_generic_source=false ??
        # Ah, comma counting.
        # id=3988158, name=Shopee, status=true, channel_format=Marketplace, is_generic_source=false
        # id=3988157, name=Pos, status=true, channel_format=Retail, is_generic_source=true
        
        # Accessing by column name is safer with pandas.
        pass

    # Re-implementing logic using pandas to be sure
    
    # Filter Generic: is_generic_source == True
    generic_sources = sources[sources['is_generic_source'] == True]
    
    for _, source_row in generic_sources.iterrows():
        for _, loc_row in locations.iterrows():
             # Logic from dim_channels: l.name is channel_name
             # But wait, if Source is "Pos" and Location is "16 Truong Dinh", Channel Name is "16 Truong Dinh"?
             # Yes, dim_channels sql: "l.name as channel_name" for generic.
             
             channels.append({
                'Display Name': loc_row['name'],
                'Channel Ref': f"{source_row['id']}|{loc_row['id']}",
                'Type': f"Generic ({source_row['name']})"
             })

    # Convert to DataFrame
    df_channels = pd.DataFrame(channels)
    
    output_path = os.path.join(OUTPUT_DIR, 'channels_dropdown.csv')
    df_channels.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")
    print(df_channels.head())
    print(f"Total Channels: {len(df_channels)}")

if __name__ == "__main__":
    generate_spend_items()
    generate_channels()
