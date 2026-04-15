import pandas as pd
import os
import sys

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
seeds_dir = os.path.join(project_root, 'transformation', 'seeds')

def load_csv_as_df(filename):
    file_path = os.path.join(seeds_dir, filename)
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    return pd.read_csv(file_path)

def generate_dropdown_options():
    print("Generating dropdown options...")
    
    # 1. Load Data
    df_spend = load_csv_as_df('ref_spend_category.csv')
    df_sources = load_csv_as_df('ref_order_sources.csv')
    df_locations = load_csv_as_df('ref_branch_locations.csv')

    # 2. Process Spend Categories
    # We just need the unique names
    spend_categories = df_spend['spend_category_name'].unique().tolist()
    spend_categories.sort()

    # 3. Process Channels (Source + Location)
    channels = []

    # 3a. Specific Sources (Non-Generic)
    # These sources don't break down by location (e.g., specific Facebook Ad Accounts if modeled that way, or Marketplaces)
    # However, based on user requirement: "Target Channel Name -> source_id + location_id"
    # Even specific sources might need a location (often 'KHO TỔNG' or similar if inventory is involved).
    # But strictly following logic: Specific Source -> Source Name
    specific_sources = df_sources[df_sources['is_generic_source'] == False]
    for _, row in specific_sources.iterrows():
        channels.append(row['name'])

    # 3b. Generic Sources (Generic = True)
    # These MUST be combined with Locations (e.g., POS -> POS 16 Truong Dinh)
    generic_sources = df_sources[df_sources['is_generic_source'] == True]
    
    # We only care about active locations (if there's a status, but file doesn't have it, assume all active)
    # We'll create combinations: "{Source Name} - {Location Name}"
    # actually, user wants "Display Name" to map to IDs.
    # The most natural display for a store is just the Store Name (e.g. "16 Trương Định") if the source is implicitly POS.
    # But since we have multiple generic sources (POS, Shopee, Lazada, Facebook, Zalo, Web)...
    # Wait, "Shopee" is marked as generic? 
    # Let's check the CSV content from memory/previous turn...
    # ref_order_sources.csv:
    # 3988158,Shopee,true,Ecom,false,Shopee
    # 3988157,Pos,true,Retail,true,Retail
    # 29: 3988153,Facebook,true,Social,false,Facebook
    
    # If I select "Facebook", do I need to pick a location?
    # Usually Marketing Spend for Facebook is for a specific "Page" or "Ad Account".
    # The current `ref_order_sources` has specific entries for Facebook too (lines 2, 3).
    
    # Let's stick to the core requirement: 
    # "Target Channel: Dropdown chọn Kênh mục tiêu."
    # "Logic để hiển thị danh sách kênh thông minh (kết hợp Source & Location)."
    
    # Strategy:
    # 1. List all Specific Sources as is.
    # 2. For Generic Sources, explode with Locations?
    #    - If Source is POS, definitely explode with Physical Locations.
    #    - If Source is Shopee/Lazada, usually we have specific shops (lines 31-47 in CSV). 
    #      Those specific shops are `is_generic_source=false`? NO.
    #      Looking at CSV lines 31+: `3988158_1,Shopee - Fine Japan Vietnam,true...` 
    #      They are MARKED AS `true` (Generic) in `is_generic_source` column?
    #      Let's re-read line 31: `3988158_1,Shopee - Fine Japan Vietnam,true,Ecom,false,Shopee,"Shopee_Fine Japan Vietnam,"`
    #      Wait, the 5th column is `is_generic_source`.
    #      Line 1 (Schema): id,name,status,channel_format,is_generic_source,platform,mapping_tag
    #      Line 31: 3988158_1 ... true (status) ... Ecom ... false (is_generic) ...
    #      Ah! So specific shops ARE `is_generic_source=false`.
    
    #      Line 24: `3988158,Shopee,true,Ecom,false,Shopee` -> This is the "Generic Shopee". It has is_generic=false? 
    #      Wait, let's trace carefully.
    #      header: id,name,status,channel_format,is_generic_source
    #      val 24: 3988158,Shopee,true,Ecom,false
    #      So "Shopee" itself is NOT generic?
    #      
    #      Let's check "Pos" (Line 25): `3988157,Pos,true,Retail,true,Retail`
    #      YES! Pos is generic.
    
    #      So logic is sound:
    #      - Take all `is_generic_source=false` rows -> usage as "Direct Channel".
    #      - Take all `is_generic_source=true` rows -> combine with Locations.
    
    for _, source_row in generic_sources.iterrows():
        source_name = source_row['name']
        for _, loc_row in df_locations.iterrows():
            loc_name = loc_row['name']
            # Combination Name
            # "POS - 16 Trương Định"
            # "WebOrder - 16 Trương Định" (This might be weird, usually Web is Warehouse specific)
            
            display_name = f"{source_name} - {loc_name}"
            channels.append(display_name)
            
            # Special Case: For POS, maybe just use Location Name? 
            # User said: "Cột Target Channel: Dropdown chọn Kênh mục tiêu... Logic hiển thị... kết hợp Source & Location"
            # And usage example: "16 Trương Định" (which implies POS).
            if source_name == "Pos":
                # Add the standalone location name as a shortcut for POS
                channels.append(loc_name)

    # Remove duplicates and sort
    channels = sorted(list(set(channels)))

    # 4. Output to CSV
    # We will create two columns: spend_category, target_channel
    # Since lengths differ, we'll make a max-length df
    max_len = max(len(spend_categories), len(channels))
    
    # Pad with empty strings
    spend_categories += [''] * (max_len - len(spend_categories))
    channels += [''] * (max_len - len(channels))
    
    df_out = pd.DataFrame({
        'spend_category_options': spend_categories,
        'target_channel_options': channels
    })
    
    output_path = os.path.join(current_dir, 'dropdown_options.csv')
    df_out.to_csv(output_path, index=False)
    print(f"Success! Dropdown options saved to: {output_path}")
    print(f"Total Spend Categories: {len([x for x in spend_categories if x])}")
    print(f"Total Target Channels: {len([x for x in channels if x])}")

if __name__ == "__main__":
    generate_dropdown_options()
