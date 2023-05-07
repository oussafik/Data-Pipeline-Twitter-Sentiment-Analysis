import tweepy
import time
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from scipy.special import softmax
from kafka import KafkaProducer
import json
import time

# Credentials
api_key = "2cpcfEOVjxZnVh4de3gqhNE4d"
api_secret = "Fsma5JVCMZCpOCxGeRomwMi8DS4ZC5zKBWGD8ppKWVKDjJ49yj"
bearer_token = "AAAAAAAAAAAAAAAAAAAAAOCgmAEAAAAAGS3EYrbGYhhsmoOEDUPCe8t7cc0%3DMOxhTd4keIGhUnVNwegmsmzAmBcv13MiWwEYxZoZo9QgmBc6vk"
access_token = "1548626209491374080-mp4DCN2E430ZoSaMLoXlL7n1cv5NgX"
access_token_secret = "h1s86z4bVkJIPRMlIQjwY20xkNaaIS8LLfHdSHMLu36uh"

# Creating Tweepy API object
auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
api = tweepy.API(auth)

# load model and tokenizer
roberta = "cardiffnlp/twitter-roberta-base-sentiment"

model = AutoModelForSequenceClassification.from_pretrained(roberta)
tokenizer = AutoTokenizer.from_pretrained(roberta)

labels = ['Negative', 'Neutral', 'Positive']

def json_serializer(data):
    return json.dumps(data).encode("utf-8")

producer = KafkaProducer(bootstrap_servers=['192.168.1.87:9092'],value_serializer=json_serializer)

# Bot searches for tweets containing certain keywords
class MyStream(tweepy.StreamingClient):

    # This function gets called when the stream is working
    def on_connect(self):
        print("Connected")

    # This function gets called when a tweet passes the stream
    def on_tweet(self, tweet):
        if tweet.referenced_tweets is None:
            # Extracting tweet information
            text = tweet.text
            user_id = tweet.author_id
            retweet_count = tweet.public_metrics['retweet_count']
            created_at = tweet.created_at
            favorite_count = tweet.public_metrics['like_count']
            reply_count = tweet.public_metrics['reply_count']

            # sentiment analysis
            encoded_tweet = tokenizer(tweet.text, return_tensors='pt')
            output = model(**encoded_tweet)

            scores = output[0][0].detach().numpy()
            scores = softmax(scores)
            ind = scores.argmax()
            result = labels[ind]
            # Printing tweet information
            print(f"Text: {text}\nUser ID: {user_id}\nRetweets: {retweet_count}\nFavorites: {favorite_count}\nReply: {reply_count}\nCreated at: {created_at}\nSentiment: {result}\n")

            message = {"User ID":user_id,"Text":text,"Created At":created_at.strftime("%Y-%m-%d %H:%M:%S"),"Retweets":retweet_count,"Favorites":favorite_count,"Reply":reply_count,"Sentiment":result}
            producer.send("tweets", message)
            # Delay between tweets
            time.sleep(0.5)

# Creating Stream object
stream = MyStream(bearer_token=bearer_token)

# Adding terms to search rules
for term in ["iphone", "apple", "samsung", "redmi", "applewatch"]:
    stream.add_rules(tweepy.StreamRule(term))

# Starting stream
stream.filter(tweet_fields=["referenced_tweets", "author_id","created_at", "public_metrics","id"])