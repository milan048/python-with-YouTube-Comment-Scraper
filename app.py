import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from textblob import TextBlob
from googleapiclient.discovery import build
import isodate

# ======================
# YouTube API Setup
# ======================
API_KEY = "AIzaSyCGUxhvjFogC5qImxqpVlXuNzM01BUjS4Q"  # 🔑 Replace with your API key
youtube = build("youtube", "v3", developerKey=API_KEY)

# ======================
# Helper Functions
# ======================
def get_channel_stats(channel_id):
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()
    if response["items"]:
        data = response["items"][0]
        return {
            "Channel Name": data["snippet"]["title"],
            "Subscribers": data["statistics"]["subscriberCount"],
            "Views": data["statistics"]["viewCount"],
            "Total Videos": data["statistics"]["videoCount"],
            "Uploads Playlist": data["contentDetails"]["relatedPlaylists"]["uploads"]
        }
    return None

def get_video_details(playlist_id, max_results=20):
    videos = []
    request = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=playlist_id,
        maxResults=max_results
    )
    response = request.execute()

    video_ids = [item["contentDetails"]["videoId"] for item in response["items"]]

    video_request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    )
    video_response = video_request.execute()

    for item in video_response["items"]:
        videos.append({
            "Video Title": item["snippet"]["title"],
            "Video ID": item["id"],
            "Views": int(item["statistics"].get("viewCount", 0)),
            "Likes": int(item["statistics"].get("likeCount", 0)),
            "Comments": int(item["statistics"].get("commentCount", 0)),
            "Duration": isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds()
        })
    return pd.DataFrame(videos)

def get_comments(video_id, max_comments=50):
    comments = []
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_comments,
        textFormat="plainText"
    )
    response = request.execute()
    for item in response.get("items", []):
        comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        comments.append(comment)
    return comments

def analyze_sentiment(comment):
    analysis = TextBlob(comment)
    polarity = analysis.sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"

# ======================
# Streamlit UI
# ======================
st.set_page_config(page_title="YouTube Analytics Dashboard", layout="wide")
st.title("📊 YouTube Analytics & Sentiment Analysis")

# Step 1: Enter Channel ID
channel_id = st.text_input("Enter YouTube Channel ID:")

if channel_id:
    channel_stats = get_channel_stats(channel_id)
    if channel_stats:
        st.subheader("📌 Channel Information")
        st.write(channel_stats)

        # Step 2: Fetch Videos
        st.subheader("🎬 Latest Videos")
        video_df = get_video_details(channel_stats["Uploads Playlist"])
        st.dataframe(video_df)

        # Step 3: Graphs
        st.subheader("📈 Video Statistics")
        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots()
            ax.bar(video_df["Video Title"], video_df["Views"])
            plt.xticks(rotation=90)
            st.pyplot(fig)

        with col2:
            fig, ax = plt.subplots()
            ax.bar(video_df["Video Title"], video_df["Likes"], color="green")
            plt.xticks(rotation=90)
            st.pyplot(fig)

        # Step 4: Comment Sentiment
        st.subheader("💬 Comment Sentiment Analysis")
        video_choice = st.selectbox("Choose a video to analyze comments", video_df["Video Title"])
        selected_video_id = video_df.loc[video_df["Video Title"] == video_choice, "Video ID"].values[0]

        comments = get_comments(selected_video_id)
        sentiment_results = [analyze_sentiment(c) for c in comments]

        df_sentiment = pd.DataFrame({"Comment": comments, "Sentiment": sentiment_results})
        st.dataframe(df_sentiment)

        # Sentiment Count Plot
        fig, ax = plt.subplots()
        df_sentiment["Sentiment"].value_counts().plot(kind="bar", ax=ax, color=["green", "red", "gray"])
        st.pyplot(fig)

        # Step 5: Word Cloud
        st.subheader("☁ Word Cloud of Comments")
        all_comments = " ".join(comments)
        if all_comments.strip():
            wordcloud = WordCloud(width=800, height=400, background_color="white").generate(all_comments)
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)

        # Step 6: Export
        st.subheader("⬇ Export Data")
        st.download_button("Download Video Data as CSV", video_df.to_csv(index=False), "videos.csv", "text/csv")
        st.download_button("Download Sentiment Data as CSV", df_sentiment.to_csv(index=False), "sentiments.csv", "text/csv")

    else:
        st.error("Channel not found! Please check the Channel ID.")