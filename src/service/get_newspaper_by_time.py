from datetime import datetime

from pymongo import MongoClient



def get_recent_newspaper(news_type, top_k = 5):
    mongo_client = \
    MongoClient("mongodb://admin:5Esbk8w8fgiAXWuM4Mpp45H2YQR0dZad2HRR5ksp@61.172.179.77:27017/?authSource=admin")[
        "newspaper_date"]
    collection = mongo_client[f"{news_type}"]
    results = collection.find({}).sort('publish_times', -1).limit(top_k)
    results = [{result["title"].replace(".txt", ""): datetime.fromtimestamp(result["publish_times"]).strftime("%Y-%m-%d")} for result in results]
    return results

def get_news_by_time(news_type, time):
    one_year_in_seconds = 365 * 24 * 60 * 60
    start_time = time - one_year_in_seconds
    end_time = time + one_year_in_seconds
    mongo_client = \
    MongoClient("mongodb://admin:5Esbk8w8fgiAXWuM4Mpp45H2YQR0dZad2HRR5ksp@61.172.179.77:27017/?authSource=admin")[
        "newspaper_date"]
    collection = mongo_client[f"{news_type}"]
    f = {
        "publish_times": {
            "$gte": start_time,  # 大于等于一年前
            "$lte": end_time  # 小于等于一年后
        }
    }
    results = collection.find(f)
    if results is None:
        return []
    else:
        results = [{result["title"].replace(".txt", ""): datetime.fromtimestamp(result["publish_times"]).strftime("%Y-%m-%d")} for result in results]
    return results

def get_news_by_time_range(news_type, start_time, end_time):
    mongo_client = \
    MongoClient("mongodb://admin:5Esbk8w8fgiAXWuM4Mpp45H2YQR0dZad2HRR5ksp@61.172.179.77:27017/?authSource=admin")[
        "newspaper_date"]
    collection = mongo_client[f"{news_type}"]
    f ={}

if __name__ == '__main__':
    res = get_recent_newspaper("activity")
    print(res)