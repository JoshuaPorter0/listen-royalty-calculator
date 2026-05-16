import streamlit as st
import requests
import datetime
import time

# Set up clean page styling
st.set_page_config(page_title="ListenBrainz Royalty Calc", page_icon="🎵", layout="centered")

st.title("🎵 ListenBrainz Royalty Calculator")
st.write("See how much you would owe your favorite artists based on a custom per-stream rate.")

# User inputs
username = st.text_input("Enter ListenBrainz Username:", value="")
rate = st.slider("Per-stream rate (in USD):", min_value=0.001, max_value=0.02, value=0.004, step=0.001, format="$%.3f")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
with col2:
    end_date = st.date_input("End Date", datetime.date.today())

# Convert dates to Unix timestamps for the API
start_ts = int(time.mktime(start_date.timetuple()))
end_ts = int(time.mktime((end_date + datetime.timedelta(days=1)).timetuple()))

if st.button("Calculate Royalties", type="primary"):
    if not username:
        st.error("Please enter a username!")
    else:
        with st.spinner("Fetching data from ListenBrainz API..."):
            all_listens = []
            max_ts = end_ts
            url = f"https://api.listenbrainz.org/1/user/{username}/listens"
            error_flag = False
            
            # API Loop: ListenBrainz returns records backwards in batches of 100
            while max_ts > start_ts:
                params = {"count": 100, "max_ts": max_ts}
                response = requests.get(url, params=params)
                
                if response.status_code != 200:
                    st.error("Failed to fetch data. Check if the username is spelled correctly.")
                    error_flag = True
                    break
                
                data = response.json()
                listens = data.get("payload", {}).get("listens", [])
                
                if not listens:
                    break
                
                # Filter listens to match our start date boundary
                valid_listens = [l for l in listens if l['listened_at'] >= start_ts]
                all_listens.extend(valid_listens)
                
                # Break early if we've crossed into history past our start date
                if len(valid_listens) < len(listens):
                    break
                
                # Set the pointer to the oldest track in this batch to look further back
                max_ts = listens[-1]['listened_at']
                time.sleep(0.1) # Courteous delay to avoid hitting API rate limits
            
            if not error_flag:
                total_streams = len(all_listens)
                total_owed = total_streams * rate
                
                st.markdown("---")
                
                # Main Dashboard Metrics
                c1, c2 = st.columns(2)
                c1.metric(label="Total Streams Tracked", value=f"{total_streams:,}")
                c2.metric(label="Total Royalties Owed", value=f"${total_owed:,.2f}")
                
                # Breakdown by Artist
                if total_streams > 0:
                    artists = {}
                    for listen in all_listens:
                        metadata = listen.get("track_metadata", {})
                        artist_name = metadata.get("artist_name", "Unknown Artist")
                        artists[artist_name] = artists.get(artist_name, 0) + 1
                    
                    # Sort all artists by stream count descending
                    sorted_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)
                    
                    st.write("### 🧾 Itemized Artist Invoice")
                    st.write("Click any column header to sort. Use the search icon to find specific artists.")
                    
                    # Construct data for the clean table layout
                    invoice_rows = []
                    for artist, count in sorted_artists:
                        artist_owed = count * rate
                        invoice_rows.append({
                            "Artist Name": artist,
                            "Total Streams": count,
                            "Royalties Owed": f"${artist_owed:,.3f}"
                        })
                    
                    # Render the interactive spreadsheet
                    st.dataframe(invoice_rows, use_container_width=True)
                    
                else:
                    st.info("No streams found for this user in the specified date range.")
